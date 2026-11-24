"""Typed audit ledger with anti-fabrication validation.

A finding is only accepted into the ledger if it carries:
  - a verbatim quote from the source (verifiable via locate.verify_quote),
  - a machine-parseable locator (§/¶/p.N/Table N),
  - a justification (why this is a defect / why it needs review).
Findings failing validation are not silently dropped: they are recorded with
status=rejected and a reject_reason, so false positives stay visible and
countable. An empty ledger is a VALID honest outcome ("no defect found").

Types:    fact | citation | method | stats | logic | norm
Kinds:    error | insufficient_evidence | norm_issue | suggestion
Severity: critical | major | minor   (must come with severity_basis)
Status:   open -> confirmed | rejected | needs_review(待复核)
"""
from __future__ import annotations

import json
import re
import sys

from . import locate

TYPES = ("fact", "citation", "method", "stats", "logic", "norm")
KINDS = ("error", "insufficient_evidence", "norm_issue", "suggestion")
SEVERITIES = ("critical", "major", "minor")
STATUSES = ("open", "confirmed", "rejected", "needs_review")
MIN_QUOTE = 12


def new_ledger(source_path: str = "") -> dict:
    return {"version": 1, "source": source_path, "findings": [],
            "policy": "no finding without verifiable quote+locator+justification; "
                      "empty ledger is an honest 'no defect found' outcome"}


def add(ledger: dict, *, type: str, kind: str, severity: str, quote: str,
        locator: str, justification: str, suggestion: str = "",
        severity_basis: str = "", status: str = "open", note: str = "") -> dict:
    n = len(ledger["findings"]) + 1
    f = {"id": f"F{n:03d}", "type": type, "kind": kind, "severity": severity,
         "quote": quote, "locator": locator, "justification": justification,
         "suggestion": suggestion, "severity_basis": severity_basis,
         "status": status, "note": note, "reject_reason": ""}
    ledger["findings"].append(f)
    return f


def validate(ledger: dict, source_text: str) -> dict:
    """Reject unverifiable findings in-place; return a validation summary."""
    n_rej = 0
    for f in ledger["findings"]:
        if f["status"] == "rejected":
            continue
        reason = ""
        if f["type"] not in TYPES:
            reason = f"unknown type {f['type']!r}"
        elif f["kind"] not in KINDS:
            reason = f"unknown kind {f['kind']!r}"
        elif f["severity"] not in SEVERITIES:
            reason = f"unknown severity {f['severity']!r}"
        elif len(locate.norm_text(f["quote"])) < MIN_QUOTE:
            reason = "quote missing or too short"
        elif not locate.parse_locator(f["locator"]):
            reason = "locator not parseable (need §/¶/p.N/Table N)"
        elif not locate.norm_text(f["justification"]):
            reason = "justification missing"
        else:
            v = locate.verify_quote(source_text, f["quote"])
            f["quote_check"] = v
            if not v["verified"]:
                reason = (f"quote not found in source (best={v['score']}"
                          f"{', nearest ' + v.get('nearest_locator', '') if v.get('nearest_locator') else ''})")
        if reason:
            f["status"] = "rejected"
            f["reject_reason"] = reason
            n_rej += 1
    live = [f for f in ledger["findings"] if f["status"] != "rejected"]
    return {"total": len(ledger["findings"]), "accepted": len(live),
            "rejected": n_rej,
            "rejected_ids": [f["id"] for f in ledger["findings"] if f["status"] == "rejected"],
            "honest_empty": len(ledger["findings"]) == 0,
            "note": "rejected findings stay in the ledger with reject_reason for audit"}


def by(ledger: dict, key: str, live_only: bool = True) -> dict:
    out: dict = {}
    for f in ledger["findings"]:
        if live_only and f["status"] == "rejected":
            continue
        out[f[key]] = out.get(f[key], 0) + 1
    return out


def save(ledger: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=1)


def load(path: str) -> dict:
    return json.load(open(path, encoding="utf-8"))


def _demo() -> int:
    src = ("# Methods\n\nWe recruited n = 42 adults from one campus.\n\n"
           "# Results\n\nRecall improved by 18.5% (p = 0.032).")
    led = new_ledger("demo.md")
    # a real, verifiable finding
    add(led, type="stats", kind="insufficient_evidence", severity="minor",
        quote="Recall improved by 18.5% (p = 0.032).", locator="§Results ¶2 s1",
        justification="reports p without confidence interval or effect-size CI",
        suggestion="add 95% CI for the 18.5% improvement",
        severity_basis="minor: does not change main conclusion; report-completeness gap")
    # a fabricated finding: quote not in source -> must be rejected
    add(led, type="fact", kind="error", severity="critical",
        quote="The placebo arm was entirely unblinded throughout the trial.",
        locator="§Methods ¶1 s1", justification="hallucinated example")
    # a locator-less finding -> must be rejected
    add(led, type="logic", kind="suggestion", severity="minor",
        quote="We recruited n = 42 adults from one campus.",
        locator="in the methods part", justification="vague locator example")
    rep = validate(led, src)
    assert rep["total"] == 3 and rep["accepted"] == 1 and rep["rejected"] == 2, rep
    assert "quote not found" in led["findings"][1]["reject_reason"]
    assert "locator" in led["findings"][2]["reject_reason"]
    # honest empty outcome: no defect found is valid
    clean = new_ledger("clean.md")
    rep2 = validate(clean, src)
    assert rep2["honest_empty"] and rep2["accepted"] == 0
    print(json.dumps({"demo": "findings.validate", "accepted": rep["accepted"],
                      "rejected": rep["rejected"], "honest_empty_ok": rep2["honest_empty"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m arkit.findings validate <ledger.json> <source_text_file> [out.json]
    if len(sys.argv) >= 4 and sys.argv[1] == "validate":
        led = load(sys.argv[2])
        src = open(sys.argv[3], encoding="utf-8").read()
        rep = validate(led, src)
        out = sys.argv[4] if len(sys.argv) > 4 else sys.argv[2]
        save(led, out)
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        print(__doc__)
