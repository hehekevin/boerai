"""Cross-section consistency observations.

Detects candidate inconsistencies a reviewer should look at:
  1. same quantity mentioned with different numeric values across sections
     (e.g. n = 42 in Methods vs n = 40 in Results);
  2. numbers inside the abstract that never appear in the body
     (candidate abstract/body mismatch — needs agent confirmation);
  3. structural completeness: expected sections present/absent.
All outputs are observations with both locations quoted side by side; the
engine never declares a contradiction on its own (units and context differ —
only the agent can judge).
"""
from __future__ import annotations

import json
import re
import sys

from . import locate

NUM = re.compile(r"\d+(?:\.\d+)?")
KEYN = re.compile(r"\b(n\s*=\s*(\d+)|(\d+)\s*(participants|patients|subjects|samples|名|例)|"
                  r"(\d+(?:\.\d+)?)\s*%)", re.I)
EXPECTED_SECTIONS = ["abstract|摘要", "introduction|引言|前言",
                     "methods?|materials|方法|材料", "results?|结果", "discussion|讨论"]


def _keyvals(text: str) -> list[dict]:
    out = []
    for u in locate.split_units(text):
        for m in KEYN.finditer(u["text"]):
            kind = ("percent" if m.group(5) else
                    "n" if m.group(2) else "count")
            val = m.group(2) or m.group(3) or m.group(5)
            out.append({"kind": kind, "value": val, "locator": u["locator"],
                        "section": u["section"], "context": u["text"][:200]})
    return out


def observe(text: str) -> dict:
    kvs = _keyvals(text)
    groups: dict = {}
    for kv in kvs:
        groups.setdefault(kv["kind"], {}).setdefault(kv["value"], []).append(kv)
    by_kind: dict = {}
    for kv in kvs:
        by_kind.setdefault(kv["kind"], set()).add(kv["value"])
    conflicts = []
    for kind, vals in by_kind.items():
        if kind in ("n",) and len(vals) > 1:
            seen = {v: [x for x in kvs if x["kind"] == kind and x["value"] == v]
                    for v in sorted(vals)}
            conflicts.append({"kind": kind, "values": sorted(vals),
                              "occurrences": {v: [{"locator": o["locator"],
                                                   "context": o["context"]}
                                                  for o in occ] for v, occ in seen.items()},
                              "note": "observation: multiple distinct values for the same "
                                      "quantity kind; may be legitimate (subgroups, exclusions) "
                                      "— agent must check context before any finding"})
    # abstract numbers not present in body
    units = locate.split_units(text)
    abstract_txt = " ".join(u["text"] for u in units
                            if re.match(r"(?i)abstract|摘要", u["section"]))
    body_txt = " ".join(u["text"] for u in units
                        if not re.match(r"(?i)abstract|摘要", u["section"]))
    missing = []
    if abstract_txt and body_txt:
        body_nums = set(NUM.findall(body_txt))
        for u in units:
            if not re.match(r"(?i)abstract|摘要", u["section"]):
                continue
            for v in NUM.findall(u["text"]):
                if v not in body_nums and float(v) != 0:
                    missing.append({"value": v, "locator": u["locator"],
                                    "context": u["text"][:200]})
    sections_present = [s for u in units for s in [u["section"]]]
    sec_blob = " ".join(sections_present).lower()
    structure = {pat.split("|")[0]: bool(re.search(pat, sec_blob, re.I))
                 for pat in EXPECTED_SECTIONS}
    return {"quantity_conflicts": conflicts,
            "abstract_numbers_not_in_body": missing[:20],
            "structure": structure,
            "note": "observations only; both locations are quoted so a reviewer can verify"}


def _demo() -> int:
    text = ("# Abstract\n\nWe studied 42 adults; recall improved by 18.5%.\n\n"
            "# Introduction\n\nMemory research matters.\n\n"
            "# Methods\n\nWe recruited n = 42 adults.\n\n"
            "# Results\n\nAfter exclusions, n = 40 remained. Recall improved by 18.5%.\n\n"
            "# Discussion\n\nWe discuss implications.")
    rep = observe(text)
    assert rep["quantity_conflicts"], "n=42 vs n=40 must surface as an observation"
    occ = rep["quantity_conflicts"][0]["occurrences"]
    assert "42" in occ and "40" in occ
    assert all(rep["structure"].values()), rep["structure"]
    # abstract-only number: change body so 18.5 appears -> not missing; '42' appears too
    assert rep["abstract_numbers_not_in_body"] == []
    text2 = text.replace("Recall improved by 18.5%.\n\n# Discussion",
                         "Recall improved.\n\n# Discussion")
    rep2 = observe(text2)
    assert any(m["value"] == "18.5" for m in rep2["abstract_numbers_not_in_body"])
    print(json.dumps({"demo": "consistency.observe",
                      "conflicts": len(rep["quantity_conflicts"]),
                      "abstract_gap_detected": bool(rep2["abstract_numbers_not_in_body"]),
                      "structure": rep["structure"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m arkit.consistency <text_file> [out.json]
    rep = observe(open(sys.argv[1], encoding="utf-8").read())
    if len(sys.argv) > 2:
        json.dump(rep, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"quantity_conflicts": len(rep["quantity_conflicts"]),
                      "abstract_gaps": len(rep["abstract_numbers_not_in_body"]),
                      "structure": rep["structure"]}, ensure_ascii=False))
