"""Text anchoring for audit evidence.

Every finding must point at a verifiable place. This module splits a source
text into located units (section §, paragraph index, sentence index, table
anchors) and verifies that a quoted string really occurs in the source.
Locators are plain strings: "§Results ¶3 s2", "p.4 ¶1", "Table 2".
"""
from __future__ import annotations

import difflib
import json
import re
import sys

SECTION_RE = re.compile(
    r"^\s*(#{1,4}\s+|)(abstract|summary|introduction|background|methods?|materials|"
    r"results?|discussion|conclusion|references?|acknowledg|appendix|"
    r"摘要|引言|前言|背景|方法|材料|结果|讨论|结论|参考文献|致谢|附录)\b", re.I | re.M)
TABLE_RE = re.compile(r"\b(table|tab\.|表)\s*(\d+[a-z]?)", re.I)
SENT_SPLIT = re.compile(r"(?<=[.!?。！？；;])\s+")


def norm_text(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "")).strip()


def split_units(text: str) -> list[dict]:
    """Split into located units: paragraphs and sentences with § context."""
    units = []
    section = "(front)"
    para_i = 0
    for raw in re.split(r"\n\s*\n", text or ""):
        para = norm_text(raw)
        if not para:
            continue
        m = re.match(r"^\s*#{1,4}\s*(.+)$", para)
        head = SECTION_RE.match(para)
        if (m and len(para) < 120) or (head and len(para) < 120):
            section = (m.group(1) if m else para)[:60].strip("# ")
            continue
        para_i += 1
        sents = SENT_SPLIT.split(para)
        for si, s in enumerate(sents, 1):
            s = s.strip()
            if not s:
                continue
            tabs = [f"Table {n}" for _, n in TABLE_RE.findall(s)]
            units.append({"section": section, "para": para_i, "sent": si,
                          "locator": f"§{section} ¶{para_i} s{si}",
                          "text": s, "tables": tabs})
    return units


def verify_quote(text: str, quote: str, threshold: float = 0.92) -> dict:
    """Is quote present in source text? Exact first, then best fuzzy window."""
    src, q = norm_text(text), norm_text(quote)
    if not q:
        return {"verified": False, "method": "empty_quote", "score": 0.0}
    idx = src.find(q)
    if idx >= 0:
        return {"verified": True, "method": "exact", "score": 1.0, "char_offset": idx}
    # fuzzy: slide over sentence-sized windows
    best, best_u = 0.0, None
    for u in split_units(text):
        r = difflib.SequenceMatcher(None, u["text"].lower(), q.lower()).ratio()
        if r > best:
            best, best_u = r, u
    if best >= threshold:
        return {"verified": True, "method": "fuzzy", "score": round(best, 3),
                "nearest_locator": best_u["locator"], "nearest_text": best_u["text"][:160]}
    return {"verified": False, "method": "fuzzy_below_threshold", "score": round(best, 3),
            "nearest_locator": best_u["locator"] if best_u else "",
            "nearest_text": (best_u["text"][:160] if best_u else "")}


def parse_locator(loc: str) -> bool:
    """A locator must reference section/paragraph/page/table/line — not be free text."""
    return bool(re.search(r"(§|¶|p\.\s*\d|page\s*\d|table\s*\d|表\s*\d|fig|l\.\s*\d|line\s*\d|s\d+)",
                          loc or "", re.I))


def find_mentions(text: str, pattern: str, flags: int = re.I) -> list[dict]:
    """All regex matches with locators (observation helper for other modules)."""
    units = split_units(text)
    out = []
    rx = re.compile(pattern, flags)
    for u in units:
        for m in rx.finditer(u["text"]):
            out.append({"locator": u["locator"], "section": u["section"],
                        "match": m.group(0), "context": u["text"][:200]})
    return out


def _demo() -> int:
    text = ("# Introduction\n\nWe study sleep and memory. Prior work is mixed.\n\n"
            "# Methods\n\nWe recruited n = 42 adults. Table 1 lists demographics.\n\n"
            "# Results\n\nRecall improved by 18.5% (p = 0.032). See Table 2.")
    units = split_units(text)
    assert any(u["section"].lower().startswith("methods") for u in units), units
    v1 = verify_quote(text, "Recall improved by 18.5% (p = 0.032).")
    assert v1["verified"] and v1["method"] == "exact"
    v2 = verify_quote(text, "Recall improved by 18.5 % (p = 0.032)")
    assert v2["verified"] and v2["method"] == "fuzzy" and v2["score"] >= 0.92, v2
    v3 = verify_quote(text, "The placebo group showed no change whatsoever in any task.")
    assert not v3["verified"], v3
    assert parse_locator("§Results ¶3 s1") and parse_locator("p.4 ¶2") and parse_locator("Table 2")
    assert not parse_locator("somewhere in the paper")
    hits = find_mentions(text, r"n\s*=\s*\d+")
    assert hits and hits[0]["match"] == "n = 42"
    print(json.dumps({"demo": "locate", "units": len(units), "exact": v1["verified"],
                      "fuzzy": v2["score"], "fake_rejected": not v3["verified"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m arkit.locate <text_file> <quote> -> verification JSON
    text = open(sys.argv[1], encoding="utf-8").read()
    quote = sys.argv[2] if len(sys.argv) > 2 else ""
    if quote:
        print(json.dumps(verify_quote(text, quote), ensure_ascii=False, indent=1))
    else:
        for u in split_units(text):
            print(u["locator"], "|", u["text"][:80])
