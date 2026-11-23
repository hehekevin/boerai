#!/usr/bin/env python3
"""review-forge: reviewer comment ledger + reply coverage + anchor location.

--split FILE      parse reviewer-comments.md into numbered comments with
                  sub-requirements (a/b/c, 1/2, "and", "also") -> ledger JSON
--check LEDGER REPLIES.md   every comment & sub-item answered? unanswered list
--locate REPLIES.md MANUSCRYPT.md  quoted/claimed edit anchors exist in the
                  manuscript? (quoted fragments >=8 chars searched verbatim;
                  "已在第X节/Section X" refs checked against headings)
Stdlib only.
"""
import argparse
import json
import re
import sys


def split_comments(text):
    comments = []
    cur = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^(?:R(?:eviewer)?\s*)?(\d+)[\.、\)\:：]\s*(.*)$|^意见\s*(\d+)\s*[:：]?\s*(.*)$", line)
        if m:
            num = m.group(1) or m.group(3)
            body = (m.group(2) or m.group(4) or "").strip()
            cur = {"no": num, "body": body, "subs": [], "source_line": line[:120]}
            comments.append(cur)
            continue
        if cur is None:
            continue
        # sub-requirement markers
        if re.match(r"^(?:\(?[a-e]\)|[1-5]\)|（[a-e]）|（[1-5]）|[-*•])\s+", line) or \
           re.search(r"\b(?:also|additionally|and|此外|同时|并且|另外)\b", line[:12], re.I):
            cur["subs"].append(line[:200])
        else:
            cur["body"] = (cur["body"] + " " + line)[:800]
    # implicit subs: sentences inside body containing multiple demands
    for c in comments:
        if not c["subs"]:
            parts = re.split(r"(?<=。)|(?<=；)", c["body"])
            if len(parts) >= 2:
                c["subs"] = [p.strip()[:200] for p in parts if p.strip()][1:]
    return comments


def check_coverage(ledger, replies_text):
    problems, covered = [], 0
    for c in ledger["comments"]:
        no = c["no"]
        pat = re.compile(r"(?:^|[^\d])%s(?![\d])" % re.escape(str(no)))
        hit = pat.search(replies_text)
        if not hit:
            problems.append("COMMENT %s: no reply found (must answer every comment)" % no)
            continue
        covered += 1
        for i, sub in enumerate(c.get("subs", []), 1):
            # sliding 2-gram overlap between sub text and nearby reply lines
            sub_norm = re.sub(r"[\s，。；、,.;:：]", "", sub)
            grams = {sub_norm[j:j+2] for j in range(len(sub_norm)-1)}
            window = replies_text[max(0, hit.start()):hit.start() + 2000]
            ok = sum(1 for g in grams if g in window) / max(1, len(grams))
            if ok < 0.2:
                problems.append("COMMENT %s sub-%d possibly unanswered (overlap %.0f%%): %s" % (no, i, ok*100, sub[:60]))
    return problems, covered


def locate_anchors(replies_text, manuscript_text):
    problems, checked = [], 0
    ms_norm = re.sub(r"\s+", "", manuscript_text)
    # quoted fragments
    for m in re.finditer(r"[“「\"']([^\"'”」]{8,120})[”」\"']", replies_text):
        frag = re.sub(r"\s+", "", m.group(1))
        checked += 1
        if frag not in ms_norm:
            problems.append("ANCHOR: quoted fragment not found in manuscript: %s" % m.group(1)[:60])
    # section refs
    heads = re.findall(r"^#{1,6}\s*(.+)$", manuscript_text, flags=re.M)
    for m in re.finditer(r"(?:第([一二三四五六七八九十\d]+)节|Section\s*(\d+)|(\d+)\.(\d+(?:\.\d+)*)\s*节)", replies_text):
        checked += 1
        ref = (m.group(2) or m.group(4) or "")
        if ref and not any(ref in h for h in heads):
            problems.append("SECTION: referenced section %r not in manuscript headings" % ref)
    return problems, checked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split"); ap.add_argument("--ledger"); ap.add_argument("--replies")
    ap.add_argument("--check", nargs=2, metavar=("LEDGER","REPLIES"))
    ap.add_argument("--locate", nargs=2, metavar=("REPLIES","MANUSCRIPT"))
    ap.add_argument("--manuscript"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.split:
        text = open(a.split, encoding="utf-8", errors="replace").read()
        comments = split_comments(text)
        out = {"schema": "review-forge/ledger@1", "n_comments": len(comments), "comments": comments}
        tgt = a.out or "/app/work/ledger.json"
        open(tgt, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
        print("comments=%d subs=%d -> %s" % (len(comments), sum(len(c["subs"]) for c in comments), tgt))
        return 0
    if a.check:
        ledger = json.load(open(a.check[0], encoding="utf-8"))
        replies = open(a.check[1], encoding="utf-8", errors="replace").read()
        problems, covered = check_coverage(ledger, replies)
        if problems:
            print("FAIL (%d):" % len(problems))
            for p in problems[:30]: print("  - %s" % p)
            return 1
        print("PASS: all %d comments covered (subs keyword-checked)." % covered)
        return 0
    if a.locate:
        replies = open(a.locate[0], encoding="utf-8", errors="replace").read()
        ms = open(a.locate[1], encoding="utf-8", errors="replace").read()
        problems, checked = locate_anchors(replies, ms)
        if problems:
            print("FAIL (%d):" % len(problems))
            for p in problems[:30]: print("  - %s" % p)
            return 1
        print("PASS: %d anchors (quotes/section refs) located in manuscript." % checked)
        return 0
    ap.error("choose --split / --check / --locate")


if __name__ == "__main__":
    sys.exit(main())
