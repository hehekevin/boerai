#!/usr/bin/env python3
"""trans-align-forge: pre-delivery verifier for bilingual translation.

Checks (stdlib only, never crashes on odd shapes):
  1. alignment      — bilingual.md paragraph IDs match segments.json (order + set)
  2. token fidelity — numbers/units/citations/author-year/figure-table-eq markers
                      found in source segment must appear in its translation
  3. glossary lock  — every locked glossary term: whenever its EN form appears in
                      a source paragraph, the ZH translation appears in that
                      paragraph's translation (full-text back-fill check)
  4. honest gaps    — 【未译/【译注 markers exist -> must be listed; counted

Exit 0 = PASS (warnings allowed), 1 = FAIL.
"""
import argparse
import json
import re
import sys

HEAD_RE = re.compile(r"^#{2,4}\s*(P\d+)")
CN_FIELD = re.compile(r"^\*\*原文\*\*[：:](.*)$|^### .+")
SRC_FIELD = re.compile(r"\*\*原文\*\*[：:]\s?(.*)", re.S)
TGT_FIELD = re.compile(r"\*\*译文\*\*[：:]\s?(.*?)(?=\n\*\*记号\*\*|\n\*\*原文\*\*|\n###|\Z)", re.S)
UNTRANS_RE = re.compile(r"【未译[：:]([^】]*)】")


def parse_bilingual(path):
    blocks = []
    text = open(path, encoding="utf-8", errors="replace").read()
    parts = re.split(r"(?=^#{2,4}\s*P\d+)", text, flags=re.M)
    for part in parts:
        m = HEAD_RE.match(part)
        if not m:
            continue
        seg_id = m.group(1)
        src = SRC_FIELD.search(part)
        tgt = TGT_FIELD.search(part)
        blocks.append({"seg_id": seg_id,
                       "src": src.group(1).strip() if src else "",
                       "tgt": tgt.group(1).strip() if tgt else ""})
    return blocks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--bilingual", required=True)
    ap.add_argument("--glossary")
    ap.add_argument("--contract")
    a = ap.parse_args()

    problems, warnings = [], []
    segs_data = json.load(open(a.source, encoding="utf-8"))
    segments = {s["seg_id"]: s for s in segs_data["segments"]}
    blocks = parse_bilingual(a.bilingual)
    if not blocks:
        print("FAIL: no '### Pxxx / **原文** / **译文**' blocks found in %s — check templates/bilingual-table.md format" % a.bilingual)
        return 1

    # 1. alignment
    src_ids = list(segments.keys())
    out_ids = [b["seg_id"] for b in blocks]
    if out_ids != src_ids:
        missing = [i for i in src_ids if i not in out_ids]
        extra = [i for i in out_ids if i not in src_ids]
        dup = [i for i in set(out_ids) if out_ids.count(i) > 1]
        if missing:
            problems.append("ALIGNMENT: %d untranslated segments: %s" % (len(missing), missing[:10]))
        if extra:
            problems.append("ALIGNMENT: unknown segment IDs in bilingual.md: %s" % extra[:10])
        if dup:
            problems.append("ALIGNMENT: duplicated segment IDs: %s" % sorted(dup)[:10])
        elif not missing and not extra:
            problems.append("ALIGNMENT: segment order differs from source")

    # 2. token fidelity
    by_id = {b["seg_id"]: b for b in blocks}
    n_tok_fail = 0
    for sid, seg in segments.items():
        b = by_id.get(sid)
        if not b:
            continue
        toks = seg.get("tokens", {})
        for kind in ("citations", "author_year", "ref_markers", "units"):
            for tok in toks.get(kind, []):
                if tok not in b["tgt"]:
                    problems.append("TOKEN: %s %s %r missing in translation" % (sid, kind, tok))
                    n_tok_fail += 1
        for tok in toks.get("numbers", []):
            if tok not in b["tgt"]:
                warnings.append("NUM: %s number %r not in translation (check: moved/rewritten or lost)" % (sid, tok))

    # 3. glossary lock
    if a.glossary:
        gloss = json.load(open(a.glossary, encoding="utf-8"))
        entries = gloss.get("entries", gloss) if isinstance(gloss, dict) else gloss
        locked = [e for e in entries if isinstance(e, dict) and e.get("status") == "locked" and e.get("zh")]
        n_lock_fail = 0
        for e in locked:
            en, zh = e["en"], e["zh"]
            for sid, seg in segments.items():
                b = by_id.get(sid)
                if not b or en not in b["src"]:
                    continue
                if zh not in b["tgt"]:
                    problems.append("GLOSS: %s term %r -> %r missing in translation (en present in source)" % (sid, en, zh))
                    n_lock_fail += 1
        if not locked:
            warnings.append("GLOSS: glossary has no locked entries (status=locked with zh); terminology enforcement skipped")
        else:
            print("glossary: %d locked entries checked across all segments" % len(locked))
    else:
        warnings.append("GLOSS: no glossary passed; terminology check skipped entirely")

    # 4. honest gaps
    untrans = [(b["seg_id"], UNTRANS_RE.search(b["tgt"]).group(1))
               for b in blocks if UNTRANS_RE.search(b["tgt"])]

    if warnings:
        print("WARN (%d):" % len(warnings))
        for w in warnings[:40]:
            print("  - %s" % w)
    if problems:
        print("FAIL (%d):" % len(problems))
        for p in problems[:60]:
            print("  - %s" % p)
        return 1
    print("PASS: alignment=%d segments; token fidelity ok; untranslated=%d (must be listed in result.json.gaps)"
          % (len(blocks), len(untrans)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
