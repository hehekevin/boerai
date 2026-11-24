#!/usr/bin/env python3
"""trans-align-forge: deterministic candidate-term extraction for the glossary.

Heuristics (stdlib only): capitalized multi-word noun phrases (2-4 words),
ALL-CAPS acronyms (2-8 chars, may contain digits), hyphenated compounds seen
>=2 times, quoted/parenthesized definition patterns, domain suffix words.
Output: glossary_draft.json with candidate terms + frequency + first location;
the agent then fills translations once and locks the table.
"""
import argparse
import json
import re
import sys
from collections import Counter

STOP = {"the", "a", "an", "of", "in", "on", "for", "and", "or", "to", "with",
        "by", "from", "at", "as", "is", "are", "was", "were", "be", "been",
        "we", "our", "this", "that", "these", "those", "it", "its", "not",
        "no", "than", "then", "when", "which", "where", "how", "can", "may",
        "figure", "table", "equation", "section", "results", "discussion",
        "conclusion", "introduction", "abstract", "references", "acknowledg"}
WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-]*")


def candidates(segments):
    phrases, acronyms, hyphens, ngrams = Counter(), Counter(), Counter(), Counter()
    first_loc = {}
    for seg in segments:
        text = seg["text"]
        # multi-word capitalized phrase (allow internal stopwords like "of")
        for m in re.finditer(
                r"\b([A-Z][a-z]+(?:[\s\-](?:of|in|and|for)?[\s\-])?[A-Z][a-z]+"
                r"(?:[\s\-][A-Z][a-z]+){0,2})\b", text):
            t = m.group(0)
            phrases[t] += 1
            first_loc.setdefault(t, seg["seg_id"])
        # acronyms
        for m in re.finditer(r"\b([A-Z]{2,8}(?:\d|[a-z])?)\b", text):
            t = m.group(1)
            if t.lower() not in STOP:
                acronyms[t] += 1
                first_loc.setdefault(t, seg["seg_id"])
        # hyphenated compounds
        for m in re.finditer(r"\b([a-z]{2,}(?:-[a-z]{2,})+)\b", text):
            t = m.group(1)
            hyphens[t] += 1
            first_loc.setdefault(t, seg["seg_id"])
        # repeated n-grams (2-3 words, any case) — catches lowercase domain terms
        words = WORD_RE.findall(text)
        for n in (3, 2):
            for i in range(len(words) - n + 1):
                gram = [w.lower() for w in words[i:i + n]]
                if any(w in STOP or len(w) < 3 for w in gram):
                    continue
                t = " ".join(words[i:i + n])
                ngrams[t] += 1
                first_loc.setdefault(t, seg["seg_id"])
    out = []
    seen = set()
    for t, c in phrases.most_common(80):
        out.append({"en": t, "zh": "", "kind": "phrase", "freq": c,
                    "first": first_loc[t], "status": "candidate"})
        seen.add(t.lower())
    for t, c in acronyms.most_common(40):
        if t not in seen:
            out.append({"en": t, "zh": "", "kind": "acronym", "freq": c,
                        "first": first_loc[t], "status": "candidate"})
            seen.add(t.lower())
    for t, c in ngrams.most_common(60):
        if c >= 2 and t.lower() not in seen and not any(t.lower() in s for s in seen):
            out.append({"en": t, "zh": "", "kind": "ngram", "freq": c,
                        "first": first_loc[t], "status": "candidate"})
            seen.add(t.lower())
    for t, c in hyphens.most_common(40):
        if c >= 2 and t.lower() not in seen:
            out.append({"en": t, "zh": "", "kind": "compound", "freq": c,
                        "first": first_loc[t], "status": "candidate"})
            seen.add(t.lower())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--segments", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    data = json.load(open(a.segments, encoding="utf-8"))
    segs = data["segments"] if isinstance(data, dict) else data
    cands = candidates(segs)
    json.dump({"schema": "trans-align-forge/glossary-draft@1", "note":
               "fill zh for each entry, drop false positives, set status=locked; "
               "keep en field EXACTLY as in source", "n_candidates": len(cands),
               "entries": cands},
              open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("candidates=%d -> %s" % (len(cands), a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
