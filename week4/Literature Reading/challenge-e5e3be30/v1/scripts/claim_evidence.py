#!/usr/bin/env python3
"""evidence-writing-forge: claim extraction + reference integrity.

--claims FILE      split manuscript into claim units (sentences with
                   assertion markers or bare facts), each tagged with markers
--checkref FILE    citation markers [n] vs reference list: existence,
                   continuity, order-of-first-appearance
Stdlib only.
"""
import argparse
import json
import re
import sys

ASSERT_RE = re.compile(r"(表明|证明|显示|说明|揭示|证实|提出|发现|表明|影响|提高|降低|增加|减少|优于|显著|demonstrates?|shows?|indicates?|improves?|reduces?|increases?|outperforms?)")


def paras(text):
    return [p for p in re.split(r"\n\s*\n", text) if p.strip() and not p.strip().startswith("#")]


def claims(text):
    units = []
    cid = 0
    for pi, p in enumerate(paras(text)):
        for sent in re.split(r"(?<=[.。!?])\s+|(?<=[。；])", p):
            s = sent.strip()
            if len(s) < 12:
                continue
            is_assert = bool(ASSERT_RE.search(s))
            has_cite = bool(re.search(r"\[\d+\]|\(\w+ et al\.?,? \d{4}\)", s))
            if is_assert or has_cite:
                cid += 1
                units.append({"id": "C%03d" % cid, "para": pi, "text": s[:200],
                              "is_assertion": is_assert, "has_citation": has_cite,
                              "citations": re.findall(r"\[(\d+)\]", s),
                              "hedges": re.findall(r"(可能|推测|约|大约|may|might|approximately|suggest)", s, re.I)})
    return units


def checkref(text):
    problems, info = [], {}
    cites = [int(n) for n in re.findall(r"\[(\d{1,3})\]", text)]
    m = re.search(r"(?im)^#{0,6}\s*references\s*$([\s\S]*)", text)
    refs = [int(n) for n in re.findall(r"^\s*\[(\d{1,3})\]", m.group(1), flags=re.M)] if m else []
    info["citations_used"] = sorted(set(cites))
    info["ref_entries"] = refs
    if cites and not refs:
        problems.append("citations present but References section missing/unparsable")
    for c in sorted(set(cites)):
        if refs and c not in refs:
            problems.append("citation [%d] not in reference list" % c)
    if refs and refs != sorted(set(refs)):
        problems.append("reference list has duplicate/unordered entries: %s" % refs)
    if refs and refs != list(range(1, len(refs) + 1)):
        problems.append("reference list numbering not contiguous from 1: %s" % refs)
    # first-appearance order check (numbered style)
    if refs:
        first_order = []
        for n in cites:
            if n not in first_order:
                first_order.append(n)
        expected = list(range(1, len(set(cites)) + 1))
        if first_order != expected:
            warnings_only = True
            info["first_appearance_order"] = first_order
            info["order_note"] = "citation first-appearance order differs from numeric order (IEEE style) — verify style requirement"
    return problems, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims"); ap.add_argument("--checkref"); ap.add_argument("--out")
    a = ap.parse_args()
    src = a.claims or a.checkref
    if not src:
        ap.error("choose --claims FILE / --checkref FILE")
    text = open(src, encoding="utf-8", errors="replace").read()
    if a.claims:
        units = claims(text)
        out = {"schema": "evidence-writing/claims@1", "n_claim_units": len(units), "units": units}
    else:
        problems, info = checkref(text)
        out = {"schema": "evidence-writing/refcheck@1", **info, "problems": problems}
    if a.out:
        open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
        print("wrote %s" % a.out)
        if a.checkref and out.get("problems"):
            return 1
    else:
        print(json.dumps(out, ensure_ascii=False, indent=1)[:5000])
        if a.checkref and out.get("problems"):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
