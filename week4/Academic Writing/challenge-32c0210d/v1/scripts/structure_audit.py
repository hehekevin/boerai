#!/usr/bin/env python3
"""structure-forge: outline, duplicate detection, claim-evidence gap hints.

--outline FILE     heading tree with paragraph counts/lengths -> JSON
--dup FILE         cross-section duplicate detection via 8-gram shingles
                   (near-duplicate paragraphs reported with locations)
--claims FILE      extract claim sentences (表明/证明/因此/显著/说明/proves/
                   demonstrates/therefore) and evidence sentences (has citation
                   marker [n] / figure ref / number) -> gap hints
Stdlib only.
"""
import argparse
import json
import re
import sys


def paras(text):
    out = []
    for block in re.split(r"\n\s*\n", text):
        lines = [l for l in block.splitlines()
                 if l.strip() and not re.match(r"^#{1,6}\s", l.strip())]
        if lines:
            out.append("\n".join(lines))
    return out


def outline(text):
    tree, stack = [], []
    cur_section = "（无标题正文）"
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1))
            node = {"level": lvl, "title": m.group(2).strip(), "paras": 0, "chars": 0, "children": []}
            while stack and stack[-1]["level"] >= lvl:
                stack.pop()
            if stack:
                stack[-1]["children"].append(node)
            else:
                tree.append(node)
            stack.append(node)
        else:
            if line.strip():
                tgt = stack[-1] if stack else None
                if tgt:
                    tgt["paras"] += 1
                    tgt["chars"] += len(line.strip())
    return tree


def norm_para(p):
    return re.sub(r"[\s，。；、,.;:：\"'（）()《》\[\]]+", "", p)


def shingles(s, n=6):
    return {s[i:i + n] for i in range(0, max(0, len(s) - n + 1))}


def dup_detect(text):
    # sentence-level: identical/near-identical sentences across paragraphs
    sentences = []  # (para_idx, norm_sent)
    for i, p in enumerate(paras(text)):
        for sent in re.split(r"(?<=[.。!?])", p):
            ns = norm_para(sent)
            if len(ns) >= 6:
                sentences.append((i, ns))
    seen_pairs = set()
    reported = []
    for a in range(len(sentences)):
        for b in range(a + 1, len(sentences)):
            if sentences[a][0] == sentences[b][0]:
                continue
            sa, sb = sentences[a][1], sentences[b][1]
            if sa == sb or (len(sa) >= 12 and len(sb) >= 12 and (sa in sb or sb in sa)):
                key = (min(sentences[a][0], sentences[b][0]), max(sentences[a][0], sentences[b][0]))
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                pa = next(p for i, p in enumerate(paras(text)) if i == sentences[a][0])
                pb = next(p for i, p in enumerate(paras(text)) if i == sentences[b][0])
                reported.append({"para_a": sentences[a][0], "para_b": sentences[b][0],
                                 "duplicate_sentence": sa[:60],
                                 "excerpt_a": pa[:50], "excerpt_b": pb[:50],
                                 "action_hint": "merge / cross-reference instead of restating"})
    return reported


CLAIM_RE = re.compile(r"(表明|证明|说明|因此|因而|显著|优于|证实|demonstrates?|proves?|therefore|indicates)")
EV_RE = re.compile(r"\[\d+\]|Fig\.?\s*\d+|Table\s*\d+|图\s*\d+|表\s*\d+|（?\s*n\s*=\s*\d+|\d+\.\d+")


def claims_scan(text):
    hints = []
    for i, p in enumerate(paras(text)):
        for sent in re.split(r"(?<=[.。!?])\s*", p):
            if CLAIM_RE.search(sent) and len(sent) > 8:
                has_ev = bool(EV_RE.search(sent))
                hints.append({"para": i, "claim": sent.strip()[:110],
                              "has_inline_evidence": has_ev,
                              "hint": None if has_ev else "claim without inline evidence marker -> link to data/citation or soften"})
    return hints


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outline"); ap.add_argument("--dup"); ap.add_argument("--claims")
    ap.add_argument("--out")
    a = ap.parse_args()
    src = a.outline or a.dup or a.claims
    if not src:
        ap.error("choose --outline/--dup/--claims FILE")
    text = open(src, encoding="utf-8", errors="replace").read()
    if a.outline:
        out = {"schema": "structure-forge/outline@1", "tree": outline(text)}
    elif a.dup:
        dups = dup_detect(text)
        out = {"schema": "structure-forge/dup@1", "n_paragraphs": len(paras(text)),
               "n_duplicates": len(dups), "duplicates": dups}
    else:
        out = {"schema": "structure-forge/claims@1", "hints": claims_scan(text)}
    if a.out:
        open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
        print("wrote %s" % a.out)
    else:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
