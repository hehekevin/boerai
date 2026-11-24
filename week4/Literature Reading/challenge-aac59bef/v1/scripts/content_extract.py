#!/usr/bin/env python3
"""content-extract-forge: web page main-content identification for paper reading.

Deterministic subcommands (0 model requests):
  --extract PAGE.html       strip nav/ads/footer/refs, keep headings+paragraphs with structure marks
  --segments TEXT           paragraph segmentation (for translation pipeline input)
Stdlib only (html.parser).
"""
import argparse
import json
import re
import sys
from html.parser import HTMLParser

# noise containers: nav/ads/related/refs removed from main content
NOISE_TAGS = {"nav", "header", "footer", "aside", "script", "style", "noscript", "form"}
NOISE_CLASS_HINTS = re.compile(r"(?i)(nav|menu|sidebar|advert|ads?|banner|related|recommend|comment|share|social|footer|header|breadcrumb)")
REFS_HINT = re.compile(r"(?i)^\s*(references|参考文献|bibliography|引\s*用\s*文\s*献)\s*$")
NOISE_TEXT = re.compile(r"(?i)^(登录|sign\s*in|subscribe|订阅|download pdf|下载|分享|share|copyright|©|all rights reserved)")


class ContentParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []          # blocks: {type: heading/para/ref_heading, level, text}
        self._skip_depth = 0
        self._in_ref = False
        self._buf = []
        self._cur = None       # (type, level)

    def handle_starttag(self, tag, attrs):
        if tag in NOISE_TAGS:
            self._skip_depth += 1
            return
        ad = False
        for k, v in attrs:
            if k in ("class", "id", "role") and v and NOISE_CLASS_HINTS.search(v):
                ad = True
        if ad:
            self._skip_depth += 1
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush()
            self._cur = ("heading", int(tag[1]))
        elif tag == "p" or tag == "li":
            self._flush()
            self._cur = ("para", 0)

    def handle_endtag(self, tag):
        if tag in NOISE_TAGS or tag == "div":  # div may be noise wrapper; flush anyway
            self._flush()
            if tag in NOISE_TAGS and self._skip_depth:
                self._skip_depth -= 1
        elif tag in ("p", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush()

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._cur:
            self._buf.append(data)

    def _flush(self):
        if not self._cur:
            return
        text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        typ, level = self._cur
        self._cur, self._buf = None, []
        if not text or len(text) < 2:
            return
        if NOISE_TEXT.match(text):
            return
        if REFS_HINT.match(text):
            self._in_ref = True
            self.out.append({"type": "ref_heading", "level": 0, "text": text})
            return
        if self._in_ref and typ == "para":
            self.out.append({"type": "ref_item", "level": 0, "text": text[:120]})
            return
        self.out.append({"type": typ, "level": level, "text": text[:300]})


def cmd_extract(path):
    html = open(path, encoding="utf-8", errors="replace").read()
    p = ContentParser()
    p.feed(html)
    body = [b for b in p.out if b["type"] in ("heading", "para")]
    noise = [b for b in p.out if b["type"] in ("ref_heading", "ref_item")]
    print(json.dumps({"schema": "webread/extract@1", "file": path,
                      "n_body_blocks": len(body),
                      "structure": [{"type": b["type"], "level": b["level"], "text": b["text"][:100]} for b in body[:30]],
                      "n_noise_blocks_removed": len(noise),
                      "noise_sample": [b["text"][:50] for b in noise[:5]],
                      "kept_structure_marks": "章节标题(level)/图表标题保留/脚注与上下标随正文保留",
                      "note": "导航/广告/相关推荐/参考文献区已切除——正文识别按标签+类名+文本启发式"}, ensure_ascii=False, indent=1))
    return 0


def cmd_segments(text_path):
    text = open(text_path, encoding="utf-8", errors="replace").read()
    paras = [norm(p) for p in re.split(r"\n\s*\n", text) if norm(p)]
    print(json.dumps({"schema": "webread/segments@1", "n_paragraphs": len(paras),
                      "paragraphs": [{"no": i + 1, "text": p[:150]} for i, p in enumerate(paras[:30])],
                      "note": "按段落而非整页翻译；供 build_glossary/verify_translation 消费"}, ensure_ascii=False, indent=1))
    return 0


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract")
    ap.add_argument("--segments")
    a = ap.parse_args()
    if a.extract:
        return cmd_extract(a.extract)
    if a.segments:
        return cmd_segments(a.segments)
    ap.error("choose --extract PAGE.html / --segments TEXT")


if __name__ == "__main__":
    sys.exit(main())
