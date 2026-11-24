#!/usr/bin/env python3
"""reader-workflow-forge: single-surface reading client workflow with verifiable anchors.

Deterministic subcommands (0 model requests):
  --sessionlog EVENTS_JSON   workflow completeness audit (open->locate->select->ask->save->review in ONE surface)
  --anchor ANSWER_JSON       anchor verification: answer tied to current page/selected text w/ backlink
  --persistence SESSION_JSON saved-state audit (annotations/QA/positions exportable)
  --repro SESSION_JSON       reproducibility audit (operation path + anchors + raw outputs)
Stdlib only.
"""
import argparse, json, re, sys

FLOW = ["open", "locate", "select", "ask", "save", "review"]

def cmd_sessionlog(path):
    events = json.load(open(path, encoding="utf-8"))
    if isinstance(events, dict):
        events = events.get("events", [])
    types = [e.get("type", "") for e in events]
    done = [f for f in FLOW if any(f in t for t in types)]
    missing = [f for f in FLOW if f not in done]
    multi_surface = any(re.search(r"(?i)(switch|external|另一个工具|切换)", str(e.get("note", ""))) for e in events)
    print(json.dumps({"schema": "reader/session@1", "flow_steps_done": done, "missing_steps": missing,
                      "single_surface": not multi_surface,
                      "verdict": "complete" if not missing else f"incomplete: 缺 {missing}",
                      "note": "同一界面完成全流程，不靠用户跨工具搬运"}, ensure_ascii=False, indent=1))
    return 0 if not missing else 1

def cmd_anchor(path):
    ans = json.load(open(path, encoding="utf-8"))
    if isinstance(ans, dict):
        ans = ans.get("answers", [ans])
    out = []
    for a in ans:
        has_ctx = bool(a.get("selected_text") and a.get("page_context"))
        backlink = bool(a.get("anchor") and (a.get("anchor").get("page") is not None or a.get("anchor").get("paragraph")))
        quote_in_ctx = norm(a.get("quote", "")).lower() in norm(a.get("page_context", "")).lower() if a.get("quote") else None
        out.append({"qid": a.get("qid", ""), "based_on_selection": has_ctx,
                    "backlink_present": backlink, "quote_matches_context": quote_in_ctx,
                    "verdict": "anchored" if has_ctx and backlink else "unanchored——需补锚点",
                    "note": "答案基于当前页面与选中文本；一键回到页码/段落/片段"})
    print(json.dumps({"schema": "reader/anchor@1", "answers": out[:30]}, ensure_ascii=False, indent=1))
    return 0

def norm(s):
    return re.sub(r"\s+", " ", s or "").strip().lower()

def cmd_persistence(path):
    s = json.load(open(path, encoding="utf-8"))
    saved = s.get("saved", {}) if isinstance(s, dict) else {}
    checks = [
        {"item": "annotations", "saved": bool(saved.get("annotations")),
         "export_format": saved.get("export_format", "未声明——须可保存/回看/导出")},
        {"item": "qa_results", "saved": bool(saved.get("qa_results"))},
        {"item": "reading_positions", "saved": bool(saved.get("reading_positions"))},
    ]
    ok = all(c["saved"] for c in checks)
    print(json.dumps({"schema": "reader/persist@1", "checks": checks,
                      "verdict": "PASS" if ok else "部分未持久化",
                      "note": "随对话消失=失败；须保存/回看/导出"}, ensure_ascii=False, indent=1))
    return 0

def cmd_repro(path):
    s = json.load(open(path, encoding="utf-8"))
    if isinstance(s, dict):
        s = s.get("session", s)
    ops = s.get("operations", [])
    raw_outputs = s.get("raw_outputs", [])
    anchors = s.get("anchors", [])
    checks = [
        {"check": "operation_path_recorded", "pass": bool(ops), "detail": f"{len(ops)} 步操作记录"},
        {"check": "raw_outputs_recorded", "pass": bool(raw_outputs), "detail": f"{len(raw_outputs)} 次原始输出"},
        {"check": "anchors_recorded", "pass": bool(anchors), "detail": f"{len(anchors)} 个原文锚点"},
    ]
    ok = all(c["pass"] for c in checks)
    print(json.dumps({"schema": "reader/repro@1", "checks": checks, "verdict": "PASS" if ok else "FAIL",
                      "note": "他人可复核复现：操作路径+原文锚点+原始输出"}, ensure_ascii=False, indent=1))
    return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessionlog")
    ap.add_argument("--anchor")
    ap.add_argument("--persistence")
    ap.add_argument("--repro")
    a = ap.parse_args()
    if a.sessionlog: return cmd_sessionlog(a.sessionlog)
    if a.anchor: return cmd_anchor(a.anchor)
    if a.persistence: return cmd_persistence(a.persistence)
    if a.repro: return cmd_repro(a.repro)
    ap.error("choose --sessionlog / --anchor / --persistence / --repro")

if __name__ == "__main__":
    sys.exit(main())
