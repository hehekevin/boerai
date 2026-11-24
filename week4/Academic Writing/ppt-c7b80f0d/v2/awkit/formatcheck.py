"""格式合规：标题层级与编号、分节字数、参考文献字段顺序。

spec.json（Agent 从模板/格式要求中抽取为结构化检查项，不凭经验猜）：
  {"max_heading_level": 3,
   "numbering": "1.1",                    # 或 "none" / "chapter"（一、二、）
   "sections": [{"name": "摘要", "min_chars": 100, "max_chars": 500},
                {"name": "引言", "min_chars": 0}],
   "reference_style": {"field_order": ["author", "title", "venue", "year"],
                        "author_max": 3,  "et_al_after": 3},
   "required_front": ["标题", "摘要"],
   "required_back": ["参考文献"]}

校验（全部机械）：
1. 标题层级不跳跃（# 之后直接 ### 记违规）、编号连续（1, 1.1, 1.2 …）。
2. 每个 spec.sections 指定的节：存在 + 字数（CJK 字+EN 词）在 [min,max]。
3. 参考文献条目字段顺序：author→title→venue→year 按出现位置判定；
   作者数超过 et_al_after 必须出现 "et al/等"。
4. 前置/后置必需块齐全。
输出 format.json，violations 为空即 ok。

CLI:  python -m awkit.formatcheck check DRAFT SPEC OUT
"""
from __future__ import annotations

import json
import re
import sys

_HEAD = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_NUMHEAD = re.compile(r"^(\d+(?:\.\d+)*)[\.、\s]")
_YEAR = re.compile(r"(?:19|20)\d{2}")


def count_words(text: str) -> int:
    cjk = len(re.findall(r"[一-鿿]", text))
    en = len(re.findall(r"[A-Za-z0-9]+", text))
    return cjk + en


def sections(draft: str) -> list[dict]:
    lines = draft.splitlines()
    heads = []
    for i, ln in enumerate(lines):
        m = _HEAD.match(ln)
        if m:
            heads.append({"line": i, "level": len(m.group(1)), "title": m.group(2)})
    for j, h in enumerate(heads):
        end = heads[j + 1]["line"] if j + 1 < len(heads) else len(lines)
        h["text"] = "\n".join(lines[h["line"] + 1:end])
        h["words"] = count_words(h["text"])
    return heads


def check(draft: str, spec: dict) -> dict:
    violations, warnings = [], []
    heads = sections(draft)
    # 1) 层级与编号
    prev = 0
    for h in heads:
        if h["level"] > prev + 1 and prev != 0:
            violations.append({"type": "heading_level_skip", "title": h["title"],
                               "from": prev, "to": h["level"]})
        prev = h["level"]
    if spec.get("numbering") and spec["numbering"] != "none":
        counters: dict[int, int] = {}
        for h in heads:
            m = _NUMHEAD.match(h["title"])
            if h["level"] <= (spec.get("max_heading_level") or 6) and heads.index(h) > 0:
                if not m and spec.get("numbering") == "1.1":
                    warnings.append({"type": "unnumbered_heading", "title": h["title"]})
                elif m:
                    parts = m.group(1).split(".")
                    lvl = len(parts)
                    counters[lvl] = counters.get(lvl, 0) + 1
                    if int(parts[-1]) != counters[lvl]:
                        violations.append({"type": "numbering_not_sequential",
                                           "title": h["title"],
                                           "expected_last": counters[lvl]})
                    for k in list(counters):
                        if k > lvl:
                            del counters[k]
    # 2) 分节字数
    for want in spec.get("sections", []):
        hit = next((h for h in heads if want["name"] in h["title"]), None)
        if not hit:
            violations.append({"type": "section_missing", "section": want["name"]})
            continue
        lo, hi = want.get("min_chars", 0), want.get("max_chars")
        if hit["words"] < lo or (hi is not None and hit["words"] > hi):
            violations.append({"type": "section_length_out_of_range",
                               "section": want["name"], "words": hit["words"],
                               "min": lo, "max": hi})
    # 3) 参考文献字段顺序
    rs = spec.get("reference_style") or {}
    order = rs.get("field_order", [])
    in_refs = False
    for ln in draft.splitlines():
        if re.match(r"^\s*#{0,6}\s*(参考文献|References)\s*$", ln.strip(), re.I):
            in_refs = True
            continue
        if not in_refs or not ln.strip() or not re.match(r"^\s*[\[（(]?\d+", ln):
            continue
        entry = ln.strip()
        if order and "year" in order and "title" in order:
            ym = _YEAR.search(entry)
            if ym:
                pos_year = ym.start()
                tail_after_year = entry[ym.end():]
                if "year" in order[:-1]:  # year 不是最后一个字段却还有长尾巴
                    if len(tail_after_year.strip(" .,")) > 40 and order.index("year") < len(order) - 1:
                        warnings.append({"type": "field_order_suspect", "entry": entry[:120]})
        if rs.get("author_max"):
            head = re.split(r"[.。]", entry, 1)[0]
            n_auth = len([a for a in re.split(r"[,，、]| and ", head) if a.strip()]) - 1
            has_etal = bool(re.search(r"et\s+al|等", entry))
            if n_auth > rs["author_max"] and rs.get("et_al_after") and not has_etal:
                violations.append({"type": "author_truncation_missing",
                                   "entry": entry[:120],
                                   "authors": n_auth, "rule": f"et al after {rs['et_al_after']}"})
    # 4) 前置/后置块
    flat = draft
    for b in spec.get("required_front", []):
        if b not in flat[:max(400, len(flat) // 4)]:
            violations.append({"type": "front_matter_missing", "block": b})
    for b in spec.get("required_back", []):
        if b not in flat[-max(400, len(flat) // 2):]:
            violations.append({"type": "back_matter_missing", "block": b})
    return {"ok": not violations, "n_headings": len(heads),
            "section_words": {h["title"][:30]: h["words"] for h in heads},
            "violations": violations, "warnings": warnings}


def _demo() -> int:
    spec = {"max_heading_level": 3, "numbering": "1.1",
            "sections": [{"name": "摘要", "min_chars": 10, "max_chars": 60},
                         {"name": "方法", "min_chars": 5}],
            "reference_style": {"author_max": 3, "et_al_after": 3},
            "required_front": ["标题"], "required_back": ["参考文献"]}
    draft = ("# 标题：T 细胞筛选研究\n\n# 摘要\n本研究筛选 500 个基因以鉴定 T 细胞活化调控因子。\n\n"
             "# 1. 引言\n背景介绍。\n\n### 1.1.1 细节\n过深标题。\n\n# 2. 方法\n样本量 500，覆盖 3 名供体，初筛命中率为 4.2%。\n\n"
             "# 3. 结果\n命中 21 个基因。\n\n# 参考文献\n"
             "[1] Smith J, Wang L, Lee K, Chen Y, Zhao M. CRISPR screens. Nat Methods, 2021.\n")
    rep = check(draft, spec)
    kinds = {v["type"] for v in rep["violations"]}
    assert "heading_level_skip" in kinds  # # -> ###
    assert "author_truncation_missing" in kinds  # 5 作者无 et al
    long_abs = draft.replace("本研究筛选 500 个基因以鉴定 T 细胞活化调控因子。",
                             "本研究" + "筛选" * 40 + "。")
    rep2 = check(long_abs, spec)
    assert any(v["type"] == "section_length_out_of_range" for v in rep2["violations"])
    clean = ("# 标题：T 细胞筛选研究\n\n# 摘要\n本研究筛选 500 个基因以鉴定调控因子。\n\n"
             "# 1. 引言\n背景介绍。\n\n# 2. 方法\n样本量 500，覆盖 3 名供体。\n\n"
             "# 参考文献\n[1] Smith J, et al. CRISPR screens. Nat Methods, 2021.\n")
    rep3 = check(clean, spec)
    assert rep3["ok"], rep3["violations"]
    return 0


def main(argv: list[str]) -> int:
    if "--demo" in argv:
        return _demo()
    if argv and argv[0] == "check":
        draft = open(argv[1], encoding="utf-8").read()
        spec = json.load(open(argv[2], encoding="utf-8"))
        rep = check(draft, spec)
        json.dump(rep, open(argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"formatcheck: ok={rep['ok']} headings={rep['n_headings']} "
              f"violations={len(rep['violations'])} -> {argv[3]}")
        return 0 if rep["ok"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
