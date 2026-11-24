#!/usr/bin/env python3
"""increment-tracker-forge: watermark-based incremental literature tracking.

Deterministic subcommands (0 model requests):
  --baseline BASE.json CURRENT.json   diff baseline vs current snapshot -> new/removed/updated
  --window FROM TO TZ                 fixed time-window record + boundary check rules
  --dedupkeys CURRENT.json            stable dedup keys (doi / arxiv / title-norm) per record
  --retrylog EVENTS.json              idempotent retry report (which events can rerun safely)
Stdlib only.
"""
import argparse
import json
import re
import sys
import unicodedata


def norm_title(s):
    s = unicodedata.normalize("NFKC", s or "")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", s.lower())).strip()


def rec_key(r):
    for k in ("doi", "arxiv_id"):
        if r.get(k):
            return f"{k}:{r[k]}"
    return "title:" + norm_title(r.get("title", ""))


def load(path):
    data = json.load(open(path, encoding="utf-8"))
    return data if isinstance(data, list) else data.get("records", data.get("items", []))


def cmd_baseline(base_path, cur_path):
    base = {rec_key(r): r for r in load(base_path)}
    cur = load(cur_path)
    new, updated, removed = [], [], []
    cur_keys = set()
    for r in cur:
        k = rec_key(r)
        cur_keys.add(k)
        if k not in base:
            new.append({"key": k, "title": (r.get("title") or "")[:80], "date": r.get("date", ""), "status": "new"})
        else:
            b = base[k]
            changes = {f: (b.get(f), r.get(f)) for f in ("title", "status", "version") if b.get(f) != r.get(f)}
            if changes:
                updated.append({"key": k, "title": (r.get("title") or "")[:80], "changes": {f: {"old": str(o)[:60], "new": str(n)[:60]} for f, (o, n) in changes.items()}, "status": "updated"})
    for k, b in base.items():
        if k not in cur_keys:
            removed.append({"key": k, "title": (b.get("title") or "")[:80], "status": "removed", "note": "消失/撤稿——需人工核实原因"})
    print(json.dumps({"schema": "tracker/increment@1", "watermark": {"n_baseline": len(base), "n_current": len(cur)},
                      "n_new": len(new), "n_updated": len(updated), "n_removed": len(removed),
                      "new": new[:30], "updated": updated[:20], "removed": removed[:10],
                      "next_watermark_note": "本次 current 快照即下次的 baseline（冻结版本）"}, ensure_ascii=False, indent=1))
    return 0


def cmd_window(frm, to, tz):
    rules = {
        "schema": "tracker/window@1",
        "window": {"from": frm, "to": to, "timezone": tz or "UTC"},
        "boundary_rules": [
            "窗口左闭右开：date >= from AND date < to——跨窗边界不重复覆盖",
            "时区固定：所有日期转换为同一时区后比较；来源时区不同时记录转换",
            "补抓：窗口结束后发现的窗口内记录 → 追加到窗口结果并标记 backfill=true，不重建整窗",
            "回溯：只对明确指定的历史窗口执行，不与当前窗口混合",
        ],
        "drift_check": "窗口起止写入每次运行的版本记录；与上次窗口比对，重叠=重复覆盖风险，间隙=漏检风险",
    }
    print(json.dumps(rules, ensure_ascii=False, indent=1))
    return 0


def cmd_dedupkeys(cur_path):
    recs = load(cur_path)
    keys = []
    collisions = {}
    for r in recs:
        k = rec_key(r)
        keys.append({"idx": recs.index(r), "key": k, "title": (r.get("title") or "")[:60], "doi": r.get("doi", ""), "arxiv_id": r.get("arxiv_id", "")})
        collisions.setdefault(k, 0)
        collisions[k] += 1
    dup_keys = {k: n for k, n in collisions.items() if n > 1}
    print(json.dumps({"schema": "tracker/dedupkeys@1", "n_records": len(recs),
                      "key_strategy": "doi > arxiv_id > title_normalized（NFKC→去标点→压空白→小写）",
                      "collisions": [{"key": k, "count": n} for k, n in list(dup_keys.items())[:20]],
                      "n_collisions": len(dup_keys)}, ensure_ascii=False, indent=1))
    return 0


def cmd_retrylog(events_path):
    events = json.load(open(events_path, encoding="utf-8"))
    if isinstance(events, dict):
        events = events.get("events", [])
    out = []
    for e in events:
        etype = e.get("type", "")
        idempotent = etype in ("fetch", "query", "dedup_pass")
        out.append({"event_id": e.get("event_id", ""), "type": etype, "status": e.get("status", ""),
                    "error": (e.get("error") or "")[:80],
                    "retry_safe": idempotent and e.get("status") == "failed",
                    "idempotency_basis": "fetch/query/dedup 幂等（重跑产生相同键集，推送层按 dedup 键抑制二次）" if idempotent else "push/notify 非幂等——重试需人工确认"})
    print(json.dumps({"schema": "tracker/retry@1", "n_events": len(out),
                      "retryable": sum(1 for o in out if o['retry_safe']),
                      "non_retryable": sum(1 for o in out if not o['retry_safe']),
                      "events": out[:30], "note": "重跑幂等，不产生二次推送"}, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", nargs=2, metavar=("BASE", "CURRENT"))
    ap.add_argument("--window", nargs=3, metavar=("FROM", "TO", "TZ"))
    ap.add_argument("--dedupkeys")
    ap.add_argument("--retrylog")
    a = ap.parse_args()
    if a.baseline:
        return cmd_baseline(a.baseline[0], a.baseline[1])
    if a.window:
        return cmd_window(a.window[0], a.window[1], a.window[2])
    if a.dedupkeys:
        return cmd_dedupkeys(a.dedupkeys)
    if a.retrylog:
        return cmd_retrylog(a.retrylog)
    ap.error("choose --baseline / --window / --dedupkeys / --retrylog")


if __name__ == "__main__":
    sys.exit(main())
