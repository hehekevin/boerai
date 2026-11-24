"""双语一致性：术语表机械套用、EN/ZH 段对齐、漏译检测。

terms.json:    [{"en": "hit rate", "zh": "命中率", "banned_zh": ["打中率"]}, ...]
segments.json: [{"id": "g001", "en": "The hit rate was 4.2%.",
                 "zh": "命中率为 4.2%。"}, ...]
                （单边任务可只给 en 或只给 zh，配对的才做对齐检查）

引擎校验：
1. 对齐段数：en 非空的段数与 zh 非空的段数一致（count_mismatch 违规）。
2. 术语机械套用：EN 段含 term.en（不区分大小写）时，配对 ZH 段必须含
   term.zh，且不得含 banned_zh 中的写法；ZH 段出现 banned_zh 即违规。
3. 漏译检测：ZH 段中 CJK 字符占比 < 阈值（默认 0.3）且含 ≥6 个拉丁字母词
   → 疑似未翻译；ZH 段整句与 EN 段字符级相同 → 未翻译。
4. 数字对齐：配对段的数字集合应一致（单位换算须走 awkit.claims 的
   computed 登记，不在此处豁免）。
输出 bilingual.json + 术语不一致/漏译/数字漂移清单。

CLI:  python -m awkit.bilingual check TERMS SEGMENTS OUT
"""
from __future__ import annotations

import json
import re
import sys

_CJK = re.compile(r"[一-鿿]")
_LATIN_WORD = re.compile(r"[A-Za-z]{2,}")
_NUM = re.compile(r"\d+(?:\.\d+)?")


def cjk_ratio(s: str) -> float:
    chars = [c for c in s if not c.isspace()]
    if not chars:
        return 0.0
    return sum(1 for c in chars if _CJK.match(c)) / len(chars)


def check(terms: list[dict], segments: list[dict], cjk_min: float = 0.3) -> dict:
    violations, term_hits = [], 0
    en_n = sum(1 for s in segments if s.get("en"))
    zh_n = sum(1 for s in segments if s.get("zh"))
    if en_n != zh_n:
        violations.append({"type": "segment_count_mismatch", "en_segments": en_n,
                           "zh_segments": zh_n,
                           "note": "EN/ZH 段数不一致，存在漏段"})
    for s in segments:
        en, zh, sid = s.get("en", "") or "", s.get("zh", "") or "", s.get("id", "?")
        if en and zh:
            if en.strip() == zh.strip():
                violations.append({"type": "untranslated_identical", "id": sid,
                                   "text": zh[:120]})
            elif cjk_ratio(zh) < cjk_min and len(_LATIN_WORD.findall(zh)) >= 6:
                violations.append({"type": "untranslated_suspect", "id": sid,
                                   "cjk_ratio": round(cjk_ratio(zh), 3), "text": zh[:120]})
            en_nums = sorted(_NUM.findall(en))
            zh_nums = sorted(_NUM.findall(zh))
            if en_nums != zh_nums:
                violations.append({"type": "number_drift", "id": sid,
                                   "en_numbers": en_nums, "zh_numbers": zh_nums,
                                   "note": "配对段数字集合不一致；单位换算须登记 computed"})
            low_en = en.lower()
            for t in terms:
                if t.get("en", "").lower() in low_en:
                    if t.get("zh", "") and t["zh"] not in zh:
                        violations.append({"type": "term_not_applied", "id": sid,
                                           "term_en": t["en"], "expected_zh": t["zh"]})
                    else:
                        term_hits += 1
        for t in terms:
            for bad in t.get("banned_zh", []):
                if bad and bad in zh:
                    violations.append({"type": "banned_term_used", "id": sid,
                                       "banned": bad, "expected_zh": t.get("zh", "")})
    # 术语表内部冲突：两个条目 en 相同 zh 不同 / zh 相同 en 不同
    seen_en, seen_zh = {}, {}
    for t in terms:
        if t.get("en", "").lower() in seen_en and seen_en[t["en"].lower()] != t.get("zh"):
            violations.append({"type": "term_table_conflict", "en": t["en"],
                               "zh_a": seen_en[t["en"].lower()], "zh_b": t.get("zh")})
        seen_en[t.get("en", "").lower()] = t.get("zh")
        if t.get("zh") and t["zh"] in seen_zh and seen_zh[t["zh"]] != t.get("en"):
            violations.append({"type": "term_table_conflict", "zh": t["zh"],
                               "en_a": seen_zh[t["zh"]], "en_b": t.get("en")})
        if t.get("zh"):
            seen_zh[t["zh"]] = t.get("en")
    return {"ok": not violations, "segments": len(segments),
            "term_applications": term_hits, "violations": violations}


def _demo() -> int:
    terms = [{"en": "hit rate", "zh": "命中率", "banned_zh": ["打中率"]},
             {"en": "donor", "zh": "供体"}]
    segs = [{"id": "g001", "en": "The hit rate was 4.2%.", "zh": "命中率为 4.2%。"},
            {"id": "g002", "en": "We used cells from 3 donors.", "zh": "我们使用了来自 3 名供体的细胞。"},
            {"id": "g003", "en": "The assay used 96 well plates.",
             "zh": "The assay used 96 well plates for readout."},
            {"id": "g004", "en": "Follow up lasted 12 months.", "zh": "随访持续 13 个月。"}]
    rep = check(terms, segs)
    kinds = {v["type"] for v in rep["violations"]}
    assert not rep["ok"]
    assert "untranslated_suspect" in kinds or "untranslated_identical" in kinds, kinds
    assert "number_drift" in kinds, kinds
    assert rep["term_applications"] >= 2
    bad_term = check(terms, [{"id": "g1", "en": "The hit rate was 4.2%.",
                              "zh": "打中率为 4.2%。"}])
    assert any(v["type"] == "banned_term_used" for v in bad_term["violations"])
    miss = check(terms, segs + [{"id": "g005", "en": "Extra paragraph.", "zh": ""}])
    assert any(v["type"] == "segment_count_mismatch" for v in miss["violations"])
    good = check(terms, segs[:2])
    assert good["ok"], good["violations"]
    return 0


def main(argv: list[str]) -> int:
    if "--demo" in argv:
        return _demo()
    if argv and argv[0] == "check":
        terms = json.load(open(argv[1], encoding="utf-8"))
        segs = json.load(open(argv[2], encoding="utf-8"))
        rep = check(terms, segs)
        json.dump(rep, open(argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"bilingual: ok={rep['ok']} segments={rep['segments']} "
              f"violations={len(rep['violations'])} -> {argv[3]}")
        return 0 if rep["ok"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
