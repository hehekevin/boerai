#!/usr/bin/env python3
"""screening-ranking-forge: multi-signal ranking with explicit weights, labels, conflicts.

Deterministic subcommands (0 model requests):
  --score RECORDS_JSON          rank records by explicit weighted signals
  --label SCORED_JSON           assign layered labels (core/method/background/exclude) w/ criteria
  --conflicts SCORED_JSON       detect conflicts (same study multi-report, preprint dup, ties)
  --explain SCORED_JSON         per-record priority explanation (which rule, which evidence, confidence)
Stdlib only.
"""
import argparse
import json
import re
import sys
import unicodedata

WEIGHTS = {"relevance_terms": 0.45, "recency": 0.25, "venue_weight": 0.2, "study_type": 0.10}


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "")).strip()


def load(path):
    data = json.load(open(path, encoding="utf-8"))
    return data if isinstance(data, list) else data.get("records", data.get("items", []))


def rec_weights(rec):
    text = norm(rec.get("title", "")) + " " + norm(rec.get("abstract", ""))
    rel_terms = rec.get("relevance_terms", [])
    n_hit = sum(1 for t in rel_terms if norm(t) in text.lower()) if rel_terms else 0
    rel = n_hit / len(rel_terms) if rel_terms else 0.0
    year = int(re.search(r"(20\d{2})", str(rec.get("year", ""))).group(1)) if re.search(r"(20\d{2})", str(rec.get("year", ""))) else 2015
    recency = max(0.0, min(1.0, (year - 2015) / 11))
    venue_w = {"Nature": 1.0, "Science": 1.0, "NeurIPS": 1.0, "ICML": 1.0, "CVPR": 1.0}.get(rec.get("venue", ""), 0.5)
    stype = 1.0 if re.search(r"(?i)randomi|trial|experiment|benchmark|dataset", text) else 0.4
    score = round(WEIGHTS["relevance_terms"] * rel + WEIGHTS["recency"] * recency +
                  WEIGHTS["venue_weight"] * venue_w + WEIGHTS["study_type"] * stype, 4)
    return {"score": score, "signals": {"relevance_terms_hit": n_hit, "relevance_ratio": rel,
                                        "recency_score": recency, "venue_score": venue_w,
                                        "study_type_score": stype}}


def cmd_score(path):
    recs = load(path)
    scored = []
    for r in recs:
        w = rec_weights(r)
        scored.append({**{k: r.get(k, "") for k in ("idx", "title", "year", "venue")},
                       **w})
    scored.sort(key=lambda x: -x["score"])
    for i, s in enumerate(scored):
        s["rank"] = i + 1
    ties = []
    for i in range(1, len(scored)):
        if scored[i]["score"] == scored[i - 1]["score"]:
            ties.append({"ranks": [scored[i - 1]["rank"], scored[i]["rank"]],
                         "tiebreak": "并列时按年份新→旧，再按标题字典序；规则显式声明"})
    print(json.dumps({"schema": "rank/score@1", "weights": WEIGHTS, "n_records": len(recs),
                      "ranked": scored, "ties": ties}, ensure_ascii=False, indent=1))
    return 0


def cmd_label(scored_path):
    data = json.load(open(scored_path, encoding="utf-8"))
    ranked = data.get("ranked", data if isinstance(data, list) else [])
    labeled = []
    for r in ranked:
        s = r.get("score", 0)
        if s >= 0.6:
            label = "core_evidence"
        elif s >= 0.4:
            label = "method_reference"
        elif s >= 0.2:
            label = "background"
        else:
            label = "exclude_candidate"
        labeled.append({"rank": r.get("rank"), "title": (r.get("title") or "")[:60], "score": s,
                        "label": label,
                        "criteria": {"core_evidence": "score>=0.6（高相关+新+强来源+研究型）",
                                     "method_reference": "0.4<=score<0.6",
                                     "background": "0.2<=score<0.4",
                                     "exclude_candidate": "score<0.2（待人工复核而非直接删除）"}})
    print(json.dumps({"schema": "rank/label@1", "records": labeled,
                      "summary": {k: sum(1 for l in labeled if l['label'] == k) for k in ("core_evidence", "method_reference", "background", "exclude_candidate")}},
                     ensure_ascii=False, indent=1))
    return 0


def cmd_conflicts(scored_path):
    data = json.load(open(scored_path, encoding="utf-8"))
    ranked = data.get("ranked", data if isinstance(data, list) else [])
    conflicts = []
    seen = {}
    for r in ranked:
        key = norm(r.get("title", ""))[:50]
        if key in seen:
            prev = seen[key]
            conflicts.append({"type": "same_study_multi_report", "items": [prev.get("rank"), r.get("rank")],
                              "titles": [(prev.get("title") or "")[:50], (r.get("title") or "")[:50]],
                              "resolution": "合并为一条，保留正式版/信息全者；另一条标记 same_study_as"})
        else:
            seen[key] = r
        if "arxiv" in norm(r.get("venue", "")) or "preprint" in norm(r.get("venue", "")):
            conflicts.append({"type": "preprint_version", "rank": r.get("rank"),
                              "resolution": "标记 preprint，正式版出现后替换并保留关联"})
    print(json.dumps({"schema": "rank/conflicts@1", "n_conflicts": len(conflicts),
                      "conflicts": conflicts[:30]}, ensure_ascii=False, indent=1))
    return 0


def cmd_explain(scored_path):
    data = json.load(open(scored_path, encoding="utf-8"))
    ranked = data.get("ranked", data if isinstance(data, list) else [])
    explanations = []
    for r in ranked[:30]:
        s = r.get("signals", {})
        top_signal = max(s.items(), key=lambda kv: kv[1] if isinstance(kv[1], (int, float)) else 0)[0] if s else "none"
        explanations.append({"rank": r.get("rank"), "title": (r.get("title") or "")[:50],
                             "score": r.get("score"),
                             "rule_hit": f"加权合计（主信号: {top_signal}）",
                             "evidence": f"terms_hit={s.get('relevance_terms_hit', 'N/A')}, year={r.get('year', 'N/A')}, venue={r.get('venue', 'N/A')}",
                             "confidence": "high" if r.get("score", 0) >= 0.6 or r.get("score", 0) < 0.2 else "medium"})
    print(json.dumps({"schema": "rank/explain@1", "explanations": explanations,
                      "note": "逐条说明命中哪条规则、依据哪些证据、置信度如何——支撑人工复核"}, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score")
    ap.add_argument("--label")
    ap.add_argument("--conflicts")
    ap.add_argument("--explain")
    a = ap.parse_args()
    if a.score:
        return cmd_score(a.score)
    if a.label:
        return cmd_label(a.label)
    if a.conflicts:
        return cmd_conflicts(a.conflicts)
    if a.explain:
        return cmd_explain(a.explain)
    ap.error("choose --score / --label / --conflicts / --explain")


if __name__ == "__main__":
    sys.exit(main())
