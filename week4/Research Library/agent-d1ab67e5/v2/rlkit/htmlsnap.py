"""Retained source-HTML snapshot parsing for citation capture (offline).

Cases ship source HTML snapshots (publisher page / preprint page saved by the
organizer).  parse_snapshot extracts the CURRENT paper's citation fields from
<meta name="citation_*"> / DC.* / og:* tags plus the <title>, with per-field
provenance (which tag filled which field) — and explicitly refuses to harvest
the page's reference list or "related articles" links as if they were the
current paper (the classic failure mode this challenge calls out).

Also validates structural anchors: locate_anchor(snapshot, kind, target)
checks whether a section id / figure number / text fingerprint exists in the
retained HTML, returning the surrounding line number so a locator can be
re-verified by a third party.  Live browsing is out of scope: this module
only reads files the case provided, and says so in every record.
"""
from __future__ import annotations

import hashlib
import html.parser
import json
import os
import re
import sys

META_MAP = {
    "citation_title": "title", "dc.title": "title", "og:title": "title",
    "citation_author": "authors", "dc.creator": "authors",
    "citation_journal_title": "venue", "citation_conference_title": "venue",
    "prism.publicationname": "venue",
    "citation_doi": "doi", "dc.identifier": "doi", "prism.doi": "doi",
    "citation_publication_date": "date", "citation_online_date": "date",
    "prism.publicationdate": "date", "dc.date": "date",
    "citation_volume": "volume", "prism.volume": "volume",
    "citation_issue": "issue", "prism.number": "issue",
    "citation_firstpage": "firstpage", "prism.startingpage": "firstpage",
    "citation_lastpage": "lastpage", "prism.endingpage": "lastpage",
    "citation_pdf_url": "pdf_url", "citation_issn": "issn",
    "citation_language": "language", "dc.language": "language",
}


class _MetaParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.metas = []          # (name, content) in document order
        self._in_title = False
        self.title = ""
        self.ids = []            # element id attributes (section/figure anchors)
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            name = (a.get("name") or a.get("property") or "").strip().lower()
            if name and a.get("content") is not None:
                self.metas.append((name, a["content"].strip()))
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if data.strip():
            self.text_parts.append(data.strip())


def parse_snapshot(path: str) -> dict:
    raw = open(path, "rb").read()
    html_text = raw.decode("utf-8", errors="replace")
    p = _MetaParser()
    p.feed(html_text)
    rec, prov = {}, {}
    for name, content in p.metas:
        field = META_MAP.get(name)
        if not field or not content:
            continue
        if field == "authors":
            rec.setdefault("authors", []).append(content)
            prov.setdefault("authors", name)
        elif field not in rec:
            if field == "doi" and not re.search(r"10\.\d{4,9}/", content):
                continue  # dc.identifier often is not a DOI — skip non-DOI values
            rec[field] = content
            prov[field] = name
    if "title" not in rec and p.title.strip():
        rec["title"] = re.sub(r"\s+", " ", p.title).strip()
        prov["title"] = "<title>"
    if rec.get("date") and not rec.get("year"):
        m = re.search(r"(19|20)\d{2}", rec["date"])
        if m:
            rec["year"] = m.group(0)
            prov["year"] = prov.get("date", "date")
    sha = hashlib.sha256(raw).hexdigest()
    warnings = []
    if not rec.get("title"):
        warnings.append("no_title_in_snapshot: 快照缺少可用标题，需人工核对")
    if not rec.get("doi"):
        warnings.append("no_doi_in_snapshot")
    n_reflist = len(re.findall(r'class="[^"]*(ref|reference|citation-list)[^"]*"', html_text, re.I))
    if n_reflist:
        warnings.append(f"reference_list_present({n_reflist}): 页面含参考文献列表，"
                        "仅取自 <meta> 标签，未把文献列表条目当作当前论文")
    return {"snapshot": os.path.abspath(path), "sha256": sha, "bytes": len(raw),
            "record": rec, "provenance": prov, "anchor_ids": p.ids[:200],
            "warnings": warnings,
            "scope_note": "offline parse of case-provided snapshot; no live network access"}


def locate_anchor(path: str, target: str) -> dict:
    """Re-verifiable locator: find a section id, figure number or text
    fingerprint in the retained HTML and return its line number + context."""
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    t = target.strip()
    for i, line in enumerate(lines, start=1):
        if f'id="{t}"' in line or f"id='{t}'" in line:
            return {"target": target, "found": True, "kind": "element_id",
                    "line": i, "context": line.strip()[:200]}
    plain = re.sub(r"<[^>]+>", " ", "\n".join(lines))
    plain = re.sub(r"\s+", " ", plain)
    if t and t in plain:
        for i, line in enumerate(lines, start=1):
            if t[:40] in re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", line)):
                return {"target": target, "found": True, "kind": "text_fingerprint",
                        "line": i, "context": re.sub(r"<[^>]+>", " ", line).strip()[:200]}
        return {"target": target, "found": True, "kind": "text_fingerprint",
                "line": None, "context": t[:120]}
    return {"target": target, "found": False, "kind": "missing",
            "reason": "anchor not present in retained snapshot"}


def _demo() -> int:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="htmlsnap-demo-")
    snap = os.path.join(tmp, "paper.html")
    open(snap, "w", encoding="utf-8").write("""<html><head>
<title>Deep Learning for Proteins | Nature</title>
<meta name="citation_title" content="Deep Learning for Proteins">
<meta name="citation_author" content="Smith, John">
<meta name="citation_author" content="Doe, Jane">
<meta name="citation_doi" content="10.1000/xyz.1">
<meta name="citation_journal_title" content="Nature">
<meta name="citation_publication_date" content="2021/03/01">
<meta name="dc.identifier" content="https://publisher.example/article/view/123">
</head><body>
<section id="sec2"><h2>Methods</h2><p>We screened 500 genes.</p></section>
<figure id="fig3"><figcaption>Figure 3. Accuracy curve</figcaption></figure>
<div class="reference-list"><span>Somebody else (1998) unrelated cited work</span></div>
</body></html>""")
    r = parse_snapshot(snap)
    rec = r["record"]
    assert rec["title"] == "Deep Learning for Proteins"
    assert rec["authors"] == ["Smith, John", "Doe, Jane"]
    assert rec["doi"] == "10.1000/xyz.1" and rec["year"] == "2021"
    assert r["provenance"]["doi"] == "citation_doi"
    assert not any("Somebody else" in str(v) for v in rec.values()), "ref-list leaked into record"
    assert any("reference_list_present" in w for w in r["warnings"])
    a1 = locate_anchor(snap, "sec2")
    assert a1["found"] and a1["kind"] == "element_id" and a1["line"]
    a2 = locate_anchor(snap, "Accuracy curve")
    assert a2["found"] and a2["kind"] == "text_fingerprint"
    a3 = locate_anchor(snap, "nonexistent-section-99")
    assert not a3["found"]
    print(json.dumps({"demo": "htmlsnap.parse+anchors", "fields": sorted(rec),
                      "warnings": r["warnings"], "anchors_ok": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "parse":
        print(json.dumps(parse_snapshot(sys.argv[2]), ensure_ascii=False, indent=1))
    elif cmd == "anchor":
        print(json.dumps(locate_anchor(sys.argv[2], sys.argv[3]), ensure_ascii=False, indent=1))
    else:
        print("usage: htmlsnap.py parse <snapshot.html> | anchor <snapshot.html> <target>")
        sys.exit(2)
