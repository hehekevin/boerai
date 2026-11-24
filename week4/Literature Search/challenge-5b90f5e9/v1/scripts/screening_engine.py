#!/usr/bin/env python3
"""systematic-screening-forge: PRISMA-style screening & audit engine.

Deterministic subcommands (0 model requests):
  --protocol QUESTION     build screening protocol skeleton (PICO elements + criteria table)
  --screen REF CRITERIA   screen records against criteria table with reason codes
  --dedup-multi FILES...  multi-source dedup keeping merge rationale per pair
  --audit STAGES_JSON     closed-loop count audit across pipeline stages
Stdlib only.
"""
import argparse
import json
import re
import sys
import os
import unicodedata


def norm_title(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"[^\w\s]", "", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def load_records(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    recs = []
    try:
        obj = json.loads(text)
        recs = obj if isinstance(obj, list) else obj.get("items", [])
    except json.JSONDecodeError:
        for line in text.splitlines():
            if line.strip() and not line.startswith("#"):
                parts = line.split("\t")
                recs.append({"title": parts[0], "abstract": parts[1] if len(parts) > 1 else "", "doi": parts[2] if len(parts) > 2 else "", "year": parts[3] if len(parts) > 3 else "", "source": parts[4] if len(parts) > 4 else ""})
    out = []
    for i, r in enumerate(recs):
        if not isinstance(r, dict):
            r = {"title": str(r)}
        out.append({"idx": i, "title": r.get("title", ""), "abstract": r.get("abstract") or r.get("summary") or "", "doi": (r.get("doi") or "").strip(), "year": str(r.get("year") or ""), "source": r.get("source") or ""})
    return out


def cmd_protocol(question):
    """PICO decomposition + criteria table skeleton."""
    pico = {
        "schema": "screening/protocol@1",
        "question": question,
        "PICO": {
            "P_population": "从研究问题中提取研究对象（人群/材料/系统）",
            "I_intervention": "提取干预/处理/方法",
            "C_comparison": "提取对照/基线（若无对照写 N/A 并说明）",
            "O_outcome": "提取结局指标与测量方式",
        },
        "inclusion_criteria": [
            {"code": "I1", "criterion": "研究主题与 PICO 全要素相关", "evidence_required": "标题或摘要命中全部 PICO 要素或其同义词"},
            {"code": "I2", "criterion": "研究类型符合综述范围", "evidence_required": "摘要中出现研究设计词（RCT/队列/案例等）"},
        ],
        "exclusion_criteria": [
            {"code": "E1", "criterion": "非研究性文献（评论/新闻/社论）", "evidence_required": "摘要无方法与结果部分"},
            {"code": "E2", "criterion": "语言不在限定范围", "evidence_required": "标题与摘要均非限定语种"},
            {"code": "E3", "criterion": "研究对象部分重叠（同一队列多次报道）", "evidence_required": "与已纳入记录人群/样本描述重叠"},
        ],
        "search_protocol_template": {
            "databases": ["PubMed", "Web of Science", "Scopus"],
            "fields": "title/abstract",
            "date_range": "如有限制写明起止，否则 N/A",
            "language_limit": "写明限定语种，不限则 N/A",
            "search_date": "执行检索的日期（必填）",
        },
        "notes": "本骨架由脚本生成；要素词需由 Agent 从研究问题语义补充，补充词记录在 expansions 字段",
    }
    print(json.dumps(pico, ensure_ascii=False, indent=1))
    return 0


REASON_PATTERNS = [
    ("E1", re.compile(r"(?i)editorial|commentary|news|opinion|社论|评论|评述(?!性研究)"), "非研究性文献"),
    ("I2", re.compile(r"(?i)randomi[sz]ed|RCT|cohort|case[- ]control|meta[- ]analysis|systematic review|队列|随机对照|荟萃|系统综述|survey|experiment|benchmark|dataset"), "研究类型命中"),
    ("E2", re.compile(r"(?i)(^|[^a-z])(non[- ]?english|仅中文|仅日文)"), "语言限定不符"),
]


def cmd_screen(ref_path, criteria_path):
    recs = load_records(ref_path)
    try:
        criteria = json.load(open(criteria_path, encoding="utf-8"))
    except Exception:
        criteria = {}
    inc = [c.get("criterion", "") for c in criteria.get("inclusion_criteria", [])] or ["与主题相关且为研究性文献"]
    exc = criteria.get("exclusion_criteria", [])

    screened = []
    for r in recs:
        text = norm_title(r["title"]) + " " + norm_title(r["abstract"])
        reason_code, reason, evidence = "pending", "", ""
        # exclusion first (E codes win)
        for code, pat, label in REASON_PATTERNS:
            if code.startswith("E"):
                m = pat.search(r["title"] + " " + r["abstract"])
                if m:
                    reason_code, reason, evidence = code, label, m.group(0)[:80]
                    break
        if reason_code == "pending":
            for code, pat, label in REASON_PATTERNS:
                if code.startswith("I"):
                    m = pat.search(r["title"] + " " + r["abstract"])
                    if m:
                        reason_code, reason, evidence = code, label, m.group(0)[:80]
                        break
        if reason_code == "pending":
            reason_code, reason = "pending_review", "规则未命中，需人工/模型复核"
        decision = "include" if reason_code.startswith("I") else ("exclude" if reason_code.startswith("E") else "pending")
        screened.append({"idx": r["idx"], "title": r["title"][:80], "decision": decision,
                         "reason_code": reason_code, "reason": reason, "evidence": evidence,
                         "source": r["source"], "year": r["year"]})

    counts = {"include": 0, "exclude": 0, "pending": 0}
    for s in screened:
        counts[s["decision"]] += 1
    out = {"schema": "screening/screen@1", "n_input": len(recs), "counts": counts,
           "criteria_applied": {"inclusion": inc, "exclusion_codes": [e.get("code") for e in exc]},
           "records": screened}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def cmd_dedup_multi(files):
    """Multi-source dedup: keep merge rationale for each duplicate pair."""
    all_recs = []
    for fi, path in enumerate(files):
        for r in load_records(path):
            r["src_file"] = os.path.basename(path)
            r["src_idx"] = fi
            all_recs.append(r)
    kept, dupes = [], []
    seen = {}
    for r in all_recs:
        k = ("doi:" + r["doi"]) if r["doi"] else ("title:" + norm_title(r["title"]))
        if k in seen:
            prev = seen[k]
            match_type = "doi_exact" if r["doi"] else "title_normalized"
            dupes.append({"kept_idx": prev["idx"], "dup_idx": r["idx"],
                          "kept_title": prev["title"][:60], "dup_title": r["title"][:60],
                          "match_type": match_type,
                          "merge_rationale": "同标识符合并；字段冲突保留信息更全者（摘要长度/年份优先）",
                          "sources": sorted({prev.get("src_file", ""), r.get("src_file", "")})})
        else:
            seen[k] = r
            kept.append(r)
    print(json.dumps({"schema": "screening/dedup-multi@1", "n_input": len(all_recs), "n_unique": len(kept),
                      "n_duplicates": len(dupes), "duplicate_pairs": dupes[:40]}, ensure_ascii=False, indent=1))
    return 0


def cmd_audit(stages_path):
    """Closed-loop count audit: every stage's input = previous output; losses explained."""
    stages = json.load(open(stages_path, encoding="utf-8"))
    if isinstance(stages, dict):
        stages = stages.get("stages", [])
    problems, chain = [], []
    prev_out = None
    for i, s in enumerate(stages):
        name = s.get("stage", f"stage{i}")
        n_in, n_out = s.get("n_in"), s.get("n_out")
        excluded = s.get("n_excluded", 0)
        if prev_out is not None and n_in != prev_out:
            problems.append(f"STAGE {name}: n_in={n_in} != previous n_out={prev_out}（计数不闭合）")
        if n_in is not None and n_out is not None and n_in - n_out != excluded:
            problems.append(f"STAGE {name}: n_in-n_out={n_in - n_out} != n_excluded={excluded}（排除数对不上）")
        if not s.get("criteria_ref"):
            problems.append(f"STAGE {name}: 缺少 criteria_ref（判定依据未引用标准编号）")
        chain.append({"stage": name, "n_in": n_in, "n_out": n_out, "n_excluded": excluded})
        prev_out = n_out
    ok = not problems
    print(json.dumps({"schema": "screening/audit@1", "closed_loop": ok, "chain": chain,
                      "problems": problems}, ensure_ascii=False, indent=1))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol")
    ap.add_argument("--screen", nargs=2, metavar=("RECORDS", "CRITERIA_JSON"))
    ap.add_argument("--dedup-multi", nargs="+", metavar="FILE")
    ap.add_argument("--audit")
    a = ap.parse_args()
    if a.protocol:
        return cmd_protocol(a.protocol)
    if a.screen:
        return cmd_screen(a.screen[0], a.screen[1])
    if a.dedup_multi:
        return cmd_dedup_multi(a.dedup_multi)
    if a.audit:
        return cmd_audit(a.audit)
    ap.error("choose --protocol / --screen / --dedup-multi / --audit")


if __name__ == "__main__":
    sys.exit(main())
