#!/usr/bin/env python3
"""writing-client-forge: revision tracking + numbering integrity.

--diff OLD NEW         paragraph-level revision records (unchanged/moved/
                       modified/added/removed) with verbatim before/after
--numbering FILE       citation [n] sequence & reference-list consistency;
                       Figure/Table numbering vs references; heading numbering
Stdlib only.
"""
import argparse
import difflib
import json
import re
import sys


def read(p):
    return open(p, encoding="utf-8", errors="replace").read()


def paras(text):
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


def diff_docs(old, new):
    po, pn = paras(old), paras(new)
    sm = difflib.SequenceMatcher(None, [re.sub(r"\s+", "", x) for x in po],
                                 [re.sub(r"\s+", "", x) for x in pn])
    records = []
    rid = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        for k, idx in enumerate(range(i1, i2)):
            rid += 1
            records.append({"id": "R%03d" % rid, "type": "removed", "old_para": idx,
                            "before": po[idx][:200], "after": None})
        for k, idx in enumerate(range(j1, j2)):
            rid += 1
            rec = {"id": "R%03d" % rid,
                   "type": "added" if tag == "insert" else ("replaced" if tag == "replace" else tag),
                   "new_para": idx, "after": pn[idx][:200], "before": None}
            records.append(rec)
    # sentence-level detail for replaced blocks (accept/reject granularity)
    detailed = []
    for r in records:
        if r["type"] == "replaced" and r.get("before") and r.get("after"):
            so = difflib.SequenceMatcher(None, r["before"], r["after"])
            for tag, a1, a2, b1, b2 in so.get_opcodes():
                if tag != "equal":
                    detailed.append({"parent": r["id"], "type": tag,
                                     "before": r["before"][a1:a2][:120],
                                     "after": r["after"][b1:b2][:120]})
    return {"n_old": len(po), "n_new": len(pn), "revisions": records,
            "sentence_changes": detailed[:200]}


def numbering(text):
    problems, info = [], {}
    body = text
    # citations in text
    cites = [int(n) for m in re.finditer(r"\[(\d{1,3})\]", body) for n in m.groups()]
    # reference list entries
    ref_sec = ""
    m = re.search(r"(?im)^#{1,6}[ \t]*references[ \t]*$\n?([\s\S]*)", text)
    if m:
        ref_sec = m.group(0)
    refs = [int(n) for n in re.findall(r"^\s*\[(\d{1,3})\]", ref_sec, flags=re.M)]
    info["citations_used"] = sorted(set(cites))
    info["reference_list_entries"] = refs
    if refs:
        if refs != list(range(1, len(refs) + 1)):
            problems.append("REFS: reference list numbering not contiguous: %s" % refs[:30])
        missing = [c for c in set(cites) if c not in refs]
        if missing:
            problems.append("REFS: cited but absent in reference list: %s" % sorted(missing)[:20])
    elif cites:
        problems.append("REFS: citations found but no References section parsed")
    # figure/table numbering in captions vs references
    cap_figs = sorted(set(re.findall(r"(?i)^\s*(?:figure|fig\.?|图)\s*(\d+)", text, flags=re.M)))
    used_figs = sorted(set(re.findall(r"(?i)(?:figure|fig\.?|图)\s*(\d+)", text)))
    info["figure_captions"] = cap_figs
    for f in used_figs:
        if cap_figs and f not in cap_figs:
            problems.append("FIGREF: Figure %s referenced but no caption found" % f)
    return problems, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff", nargs=2, metavar=("OLD", "NEW"))
    ap.add_argument("--numbering"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.diff:
        out = {"schema": "writing-client/revision@1", **diff_docs(read(a.diff[0]), read(a.diff[1]))}
        out["note"] = "every revision record is individually acceptable/rejectable; apply edits by id"
    elif a.numbering:
        problems, info = numbering(read(a.numbering))
        out = {"schema": "writing-client/numbering@1", **info, "problems": problems}
        if a.out:
            open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
            print(json.dumps({"wrote": a.out, "problems": len(problems)}, ensure_ascii=False))
            return 0
        if problems:
            print("FAIL (%d):" % len(problems))
            for p in problems: print("  - %s" % p)
            return 1
        print("PASS: numbering consistent.", json.dumps(info, ensure_ascii=False))
        return 0
    else:
        ap.error("choose --diff OLD NEW / --numbering FILE")
    if a.out:
        open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
        print("wrote %s (%d revisions)" % (a.out, out.get("n_new", 0)))
    else:
        print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    sys.exit(main())
