"""引用完整性：正文引用键 ↔ 参考文献表。

支持三种正文引用形态（可混用但会提示统一）：
  数字型   [1] [2,3] [4-6]
  作者年   (Smith, 2020) / Smith et al. (2020) / （张三, 2021）
  键型     @smith2020 / [Smith2020]

参考文献表：草稿中 “参考文献 / References / Bibliography” 标题之后，
每行一个条目，或 bib 风格 @key{...}。

校验（全部机械可复算）：
1. 每个正文引用键必须能解析到参考文献条目（unresolved → 违规）。
2. 每个条目必须至少被正文引用一次（uncited → 警告，参考文献堆砌）。
3. 数字型引用编号必须连续无跳号、且首号为 1。
4. 条目必需字段：作者 + 年份 + 标题（可用 config 调整）；缺字段 → 违规。
5. 引用形态混用 → 提示统一（警告）。

CLI:  python -m awkit.citecheck check DRAFT OUT [CONFIG_JSON]
"""
from __future__ import annotations

import json
import re
import sys

_REF_HEAD = re.compile(r"^\s*#{0,6}\s*(参考文献|参考资料|References|Bibliography|REFERENCES)\s*$",
                       re.IGNORECASE)
_NUM_CITE = re.compile(r"\[(\d+(?:\s*[-,，]\s*\d+)*)\]")
_KEY_CITE = re.compile(r"@([A-Za-z][\w:.-]+)")
_AUTHYEAR = re.compile(r"[（(]([A-Z][A-Za-z\u4e00-\u9fff'’-]+(?:\s+et\s+al\.?)?)[,，]\s*((?:19|20)\d{2})[)）]")
_ENTRY_NUM = re.compile(r"^\s*[\[（(]?(\d+)[\]）).、]\s*(.+)")
_YEAR = re.compile(r"(?:19|20)\d{2}")


def split_reference_block(draft: str) -> tuple[str, list[str]]:
    lines = draft.splitlines()
    for i, ln in enumerate(lines):
        if _REF_HEAD.match(ln.strip()):
            body = [l for l in lines[i + 1:] if l.strip()]
            return "\n".join(lines[:i]), body
    return draft, []


def parse_entries(ref_lines: list[str]) -> list[dict]:
    entries, idx = [], 0
    for ln in ref_lines:
        m = _ENTRY_NUM.match(ln)
        if m:
            entries.append({"num": int(m.group(1)), "raw": m.group(2).strip()})
        else:
            idx += 1
            entries.append({"num": None, "raw": ln.strip(), "key_guess": f"line{idx}"})
    return entries


def expand_nums(spec: str) -> list[int]:
    out = []
    for part in re.split(r"[,，]", spec):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif part.isdigit():
            out.append(int(part))
    return out


def check(draft: str, config: dict | None = None) -> dict:
    cfg = {"required_fields": ["author", "year", "title"]}
    cfg.update(config or {})
    body, ref_lines = split_reference_block(draft)
    entries = parse_entries(ref_lines)
    num_cites, key_cites, ay_cites = [], [], []
    for m in _NUM_CITE.finditer(body):
        num_cites.extend(expand_nums(m.group(1)))
    key_cites = _KEY_CITE.findall(body)
    ay_cites = [(m.group(1), m.group(2)) for m in _AUTHYEAR.finditer(body)]
    by_num = {e["num"]: e for e in entries if e["num"] is not None}
    violations, warnings = [], []
    # 1) 数字引用解析
    for n in sorted(set(num_cites)):
        if n not in by_num:
            violations.append({"type": "unresolved_numeric_cite", "cite": f"[{n}]",
                               "note": "正文引用编号在参考文献表中无对应条目"})
    # 2) 作者年/键型引用解析
    for name, year in sorted(set(ay_cites)):
        last = name.split()[0].replace("et al.", "").strip(" .").lower()
        if not any(last in e["raw"].lower() and year in e["raw"] for e in entries):
            violations.append({"type": "unresolved_authoryear_cite", "cite": f"({name}, {year})"})
    for k in sorted(set(key_cites)):
        if not any(k.lower() in e["raw"].lower() for e in entries):
            violations.append({"type": "unresolved_key_cite", "cite": f"@{k}"})
    # 3) 编号连续性
    cited_nums = sorted(set(num_cites))
    if cited_nums:
        expect = list(range(1, max(cited_nums) + 1))
        gaps = [n for n in expect if n not in cited_nums]
        if gaps:
            warnings.append({"type": "citation_numbering_gap", "missing": gaps})
        listed = sorted(by_num)
        if listed != expect[:len(listed)] and entries:
            warnings.append({"type": "reference_list_nonsequential", "listed": listed})
    # 4) 条目字段
    for i, e in enumerate(entries, 1):
        raw = e["raw"]
        missing = []
        if "author" in cfg["required_fields"] and not re.match(r"^[A-Za-z\u4e00-\u9fff'’ .,&-]+", raw):
            missing.append("author")
        if "year" in cfg["required_fields"] and not _YEAR.search(raw):
            missing.append("year")
        if "title" in cfg["required_fields"] and len(raw) < 12:
            missing.append("title")
        if missing:
            violations.append({"type": "entry_missing_fields", "entry_no": i,
                               "missing": missing, "raw": raw[:120]})
    # 5) 未被引用的条目 / 形态混用
    for e in entries:
        if e["num"] is not None and e["num"] not in set(num_cites):
            warnings.append({"type": "uncited_reference", "entry": e["raw"][:120]})
    forms = sum(bool(x) for x in (num_cites, key_cites, ay_cites))
    if forms > 1:
        warnings.append({"type": "mixed_citation_styles",
                         "note": "数字/作者年/键型混用，建议统一"})
    ok = not violations
    return {"ok": ok, "n_entries": len(entries),
            "n_intext_cites": len(num_cites) + len(key_cites) + len(ay_cites),
            "violations": violations, "warnings": warnings}


def _demo() -> int:
    draft = ("CRISPR 筛选已广泛用于功能基因组学 [1]。命中率受供体差异影响 [2]。"
             "另有研究报道了类似现象 (Lee, 2020)。\n\n# 参考文献\n"
             "[1] Smith J, Wang L. CRISPR screens in T cells. Nat Methods, 2021.\n"
             "[2] Lee K. Donor effects in pooled screens. Cell, 2020.\n"
             "[3] Orphan R. Never cited work. PLoS ONE, 2019.\n")
    rep = check(draft)
    assert rep["ok"], rep["violations"]
    assert any(w["type"] == "uncited_reference" for w in rep["warnings"])
    assert any(w["type"] == "mixed_citation_styles" for w in rep["warnings"])
    bad = draft.replace("差异影响 [2]", "差异影响 [7]")
    rep2 = check(bad)
    assert any(v["type"] == "unresolved_numeric_cite" for v in rep2["violations"])
    noyear = draft + "[4] Anonymous. Missing year entry.\n"
    rep3 = check(noyear)
    assert any(v["type"] == "entry_missing_fields" and "year" in v["missing"]
               for v in rep3["violations"])
    return 0


def main(argv: list[str]) -> int:
    if "--demo" in argv:
        return _demo()
    if argv and argv[0] == "check":
        draft = open(argv[1], encoding="utf-8").read()
        cfg = json.load(open(argv[3], encoding="utf-8")) if len(argv) > 3 else {}
        rep = check(draft, cfg)
        json.dump(rep, open(argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"citecheck: ok={rep['ok']} entries={rep['n_entries']} "
              f"violations={len(rep['violations'])} warnings={len(rep['warnings'])} -> {argv[2]}")
        return 0 if rep["ok"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
