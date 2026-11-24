"""Web-article main-text extraction & fetch audit (offline rules, no network).

输入：案例提供的 HTML 快照（不联网抓取——联网与浏览器操作由 Agent 按
任务说明完成；本模块只处理落盘的 HTML/文本并保留来源轨迹）。

职责：
  - 正文识别：从导航/广告/参考文献/相关推荐中切出正文段落，保留章节
    标题与顺序；拒绝把摘要页/目录页当正文（启发式：正文密度）
  - 抓取清单：来源 URL、抓取时间、段落锚点（seg_id→原文顺序）落盘，
    译文可逐段回溯
  - 正文完整度信号：参考文献混入检测、半页/截断信号，异常如实上报
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from html.parser import HTMLParser

DROP_TAGS = {"script", "style", "noscript", "nav", "footer", "header", "form", "aside"}
DROP_CLASS = re.compile(r"nav|menu|sidebar|advert|related|recommend|ref-list|"
                        r"reference|citation|breadcrumb|cookie|footer|header", re.I)


class _BlockParser(HTMLParser):
    KEEP = ("p", "h1", "h2", "h3", "h4", "figcaption", "li")

    def __init__(self):
        super().__init__()
        self.blocks = []  # (tag, class, text)
        self._stack = []  # [(tag, dropped_by_this_tag)]
        self._cur = None
        self._drop = 0

    def handle_starttag(self, tag, attrs):
        cls = " ".join(v for k, v in attrs if k == "class")
        aid = dict(attrs).get("id", "")
        drop = bool(tag in DROP_TAGS or DROP_CLASS.search(cls) or DROP_CLASS.search(aid))
        self._stack.append((tag, drop))
        if drop:
            self._drop += 1
        if tag in self.KEEP and self._drop == 0:
            self._cur = [tag, cls, []]

    def handle_endtag(self, tag):
        if self._cur and self._cur[0] == tag:
            text = html.unescape("".join(self._cur[2]))
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                self.blocks.append({"tag": self._cur[0], "class": self._cur[1], "text": text})
            self._cur = None
        # pop the nearest matching open tag (and any unclosed tags above it)
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                self._drop -= sum(1 for _, d in self._stack[i:] if d)
                del self._stack[i:]
                break
        if self._drop < 0:
            self._drop = 0

    def handle_data(self, data):
        if self._cur is not None and self._drop == 0:
            self._cur[2].append(data)


def extract_main_text(html_text: str, source_url: str = "",
                      fetched_at: str = "") -> dict:
    """切出正文候选段。heuristics:
      - 去掉 nav/广告/参考文献等容器
      - 保留 h1-h4 标题、p、figcaption 顺序
      - 参考文献段（数字开头密集 DOI/期刊模式）剔除
    """
    parser = _BlockParser()
    parser.feed(html_text or "")
    ref_pat = re.compile(r"^\[\d+\]|^\d+\.\s+\S.*(doi|vol\.|pp\.|期刊|et al\.)", re.I)
    segs, dropped_ref = [], 0
    for b in parser.blocks:
        if b["tag"] == "li" and ref_pat.search(b["text"]):
            dropped_ref += 1
            continue
        if ref_pat.search(b["text"]) and len(b["text"]) > 200:
            dropped_ref += 1
            continue
        segs.append(b)
    para_lens = [len(s["text"]) for s in segs if s["tag"] == "p"]
    n_para = len(para_lens)
    signals = []
    if n_para == 0:
        signals.append("no paragraph found — 可能抓到摘要页/目录页/付费墙页")
    if n_para and sum(1 for l in para_lens if l > 200) < max(1, n_para // 4):
        signals.append("正文密度低：长段落过少，疑似导航页或截断")
    body_segs = [{"seg_id": f"seg{i + 1}", "order": i + 1, "tag": s["tag"],
                  "loc": f"seg.{i + 1}", "text": s["text"]}
                 for i, s in enumerate(segs)]
    return {"source_url": source_url, "fetched_at": fetched_at,
            "html_sha256": hashlib.sha256((html_text or "").encode()).hexdigest()[:16],
            "segments": body_segs, "n_segments": len(body_segs),
            "dropped_reference_items": dropped_ref, "signals": signals,
            "ok": not signals,
            "rule": "正文 = 去掉导航/广告/参考文献后的标题+段落序列；"
                    "摘要页/目录页/截断必须报信号，不得当正文交付"}


def fetch_manifest(pages: list[dict]) -> dict:
    """pages: [{url, fetched_at, html_sha256, n_segments, signals}]
    抓取轨迹清单：每次抓取的来源、时间、版本（哈希）与信号，供回溯。"""
    return {"pages": pages, "n_pages": len(pages),
            "rule": "来源 URL + 抓取时间 + 内容哈希 = 页面版本；"
                    "HTTP 快照与实时页面是不同版本，分开登记"}


def _demo() -> int:
    sample = """<html><body>
    <nav class="main-nav">Home | Issues | Login</nav>
    <div class="advert">Subscribe now!</div>
    <article>
    <h1>Synthetic Demo Paper on Alloy Strength</h1>
    <p>We report a synthetic alloy with yield strength 520 MPa measured at 25 C. This paragraph is deliberately long enough to look like a real body paragraph for the density heuristic used in this demo, and it keeps going with more synthetic discussion of microstructure and processing so that the length threshold is clearly exceeded.</p>
    <h2>Methods</h2>
    <p>Samples were cast and annealed at 900 C for 2 h before mechanical testing, following a standard synthetic procedure described purely for demonstration purposes in this offline demo dataset; additional sentences describe synthetic polishing, etching and tensile protocols so that this paragraph also passes the density threshold comfortably.</p>
    </article>
    <ul><li>[1] Smith et al., doi:10.1000/x, vol. 3, pp. 1-9</li></ul>
    <div class="related-articles">You may also like...</div>
    </body></html>"""
    rep = extract_main_text(sample, source_url="https://example.org/demo-paper",
                            fetched_at="2026-11-24T00:00:00Z")
    assert rep["ok"], rep["signals"]
    texts = [s["text"] for s in rep["segments"]]
    assert any("yield strength 520 MPa" in t for t in texts)
    assert not any("Subscribe" in t or "You may also like" in t for t in texts)
    assert rep["dropped_reference_items"] == 1
    nav_only = "<html><body><nav class='nav'>a|b|c</nav><p>Sign in to read.</p></body></html>"
    rep2 = extract_main_text(nav_only)
    assert not rep2["ok"] and rep2["signals"]
    man = fetch_manifest([{"url": rep["source_url"], "fetched_at": rep["fetched_at"],
                           "html_sha256": rep["html_sha256"],
                           "n_segments": rep["n_segments"], "signals": []}])
    assert man["n_pages"] == 1
    print(json.dumps({"demo": "webtext", "segments": rep["n_segments"],
                      "refs_dropped": rep["dropped_reference_items"],
                      "navpage_signal": rep2["signals"][0][:40]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "extract":
        html_text = open(sys.argv[2], encoding="utf-8", errors="replace").read()
        url = sys.argv[4] if len(sys.argv) > 4 else ""
        rep = extract_main_text(html_text, source_url=url)
        json.dump(rep, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"segments={rep['n_segments']} signals={rep['signals']} -> {sys.argv[3]}")
        sys.exit(0 if rep["ok"] else 1)
    elif cmd == "manifest":
        pages = json.load(open(sys.argv[2], encoding="utf-8"))
        rep = fetch_manifest(pages.get("pages", pages))
        json.dump(rep, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"pages={rep['n_pages']} -> {sys.argv[3]}")
    else:
        print("usage: webtext.py [extract|manifest] ...")
        sys.exit(2)
