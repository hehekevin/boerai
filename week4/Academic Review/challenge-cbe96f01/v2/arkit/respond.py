"""Reviewer-response ledger for the revision workflow (审稿回复与论文修改).

Tracks the four failure axes from the brief — 答得全/改得准/证得住/对得上:
  1. decompose each review comment into numbered sub-requests (nothing half-answered);
  2. every sub-request gets a decision: adopt | partial | rebut | cannot_do + reason;
  3. every "we revised X" claim must carry anchors (locators) that VERIFY against
     the revised manuscript text — an anchor that does not resolve is flagged;
  4. evidence requests (new experiment/data/reference) track status and source;
consistency() then reports unanswered sub-requests, unverifiable modification
claims, and open evidence items. Tone is the agent's job; the ledger records it.
"""
from __future__ import annotations

import json
import sys

from . import locate

DECISIONS = ("adopt", "partial", "rebut", "cannot_do", "pending")
TONES = ("accept", "clarify", "polite_rebuttal", "appeal")
EV_STATUS = ("provided", "planned", "cannot_provide", "not_requested")


def new_ledger(manuscript_version: str = "") -> dict:
    return {"manuscript_version": manuscript_version, "comments": [],
            "policy": "every sub-request needs a decision; every 'revised' claim needs "
                      "locators verifiable in the current manuscript version"}


def add_comment(led: dict, comment_id: str, text: str, *, reviewer: str = "",
                ctype: str = "", severity: str = "") -> dict:
    c = {"comment_id": comment_id, "reviewer": reviewer, "text": text,
         "type": ctype, "severity": severity, "sub_requests": [], "response_draft": ""}
    led["comments"].append(c)
    return c


def add_sub(led: dict, comment_id: str, sub_id: str, requirement: str, *,
            decision: str = "pending", reason: str = "", anchors: list | None = None,
            evidence: list | None = None, tone: str = "accept") -> dict:
    assert decision in DECISIONS, decision
    assert tone in TONES, tone
    c = _comment(led, comment_id)
    s = {"sub_id": sub_id, "requirement": requirement, "decision": decision,
         "reason": reason, "anchors": anchors or [], "evidence": evidence or [],
         "tone": tone, "anchor_check": []}
    c["sub_requests"].append(s)
    return s


def add_evidence(led: dict, comment_id: str, sub_id: str, *, item: str,
                 status: str, source: str = "", note: str = "") -> dict:
    assert status in EV_STATUS, status
    s = _sub(led, comment_id, sub_id)
    e = {"item": item, "status": status, "source": source, "note": note}
    s["evidence"].append(e)
    return e


def _comment(led, cid):
    for c in led["comments"]:
        if c["comment_id"] == cid:
            return c
    raise KeyError(cid)


def _sub(led, cid, sid):
    for s in _comment(led, cid)["sub_requests"]:
        if s["sub_id"] == sid:
            return s
    raise KeyError(sid)


def consistency(led: dict, revised_text: str) -> dict:
    """Cross-check the ledger against the revised manuscript text."""
    unanswered, bad_anchors, open_evidence, verified = [], [], [], 0
    n_subs = 0
    for c in led["comments"]:
        for s in c["sub_requests"]:
            n_subs += 1
            if s["decision"] == "pending":
                unanswered.append(f"{c['comment_id']}/{s['sub_id']}")
            if s["decision"] in ("adopt", "partial") and not s["anchors"]:
                bad_anchors.append({"sub": f"{c['comment_id']}/{s['sub_id']}",
                                    "reason": "claims revision but no locator anchor"})
            s["anchor_check"] = []
            for a in s["anchors"]:
                quote_ok = locate.verify_quote(revised_text, a.get("quote", ""))
                loc_ok = locate.parse_locator(a.get("locator", ""))
                ok = quote_ok["verified"] and loc_ok
                s["anchor_check"].append({"locator": a.get("locator", ""),
                                          "quote_verified": quote_ok["verified"],
                                          "locator_ok": loc_ok, "ok": ok})
                if ok:
                    verified += 1
                else:
                    bad_anchors.append({"sub": f"{c['comment_id']}/{s['sub_id']}",
                                        "reason": f"anchor not verifiable: {a.get('locator')}",
                                        "quote_score": quote_ok.get("score")})
            for e in s["evidence"]:
                if e["status"] in ("planned",):
                    open_evidence.append({"sub": f"{c['comment_id']}/{s['sub_id']}",
                                          "item": e["item"], "status": e["status"]})
    n_comments = len(led["comments"])
    answered_comments = sum(1 for c in led["comments"]
                            if c["sub_requests"] and all(s["decision"] != "pending"
                                                         for s in c["sub_requests"]))
    return {"n_comments": n_comments, "answered_comments": answered_comments,
            "n_sub_requests": n_subs, "unanswered": unanswered,
            "anchors_verified": verified, "bad_anchors": bad_anchors,
            "open_evidence": open_evidence,
            "答得全": not unanswered and answered_comments == n_comments,
            "改得准": not bad_anchors,
            "证得住": not open_evidence,
            "note": "对得上 = re-run consistency() on each manuscript version; "
                    "ledger stores manuscript_version for round tracking"}


def _demo() -> int:
    revised = ("# Methods\n\nWe added a power analysis: n = 42 gives 80% power at alpha = 0.05.\n\n"
               "# Results\n\nRecall improved by 18.5% (95% CI [9.1, 27.9], p = 0.032).")
    led = new_ledger("v2")
    add_comment(led, "R1-1", "Please justify the sample size and add CIs.", reviewer="R1",
                ctype="stats", severity="major")
    add_sub(led, "R1-1", "a", "justify sample size", decision="adopt",
            reason="added power analysis",
            anchors=[{"quote": "We added a power analysis: n = 42 gives 80% power",
                      "locator": "§Methods ¶1 s1"}])
    add_sub(led, "R1-1", "b", "add confidence intervals", decision="adopt",
            reason="CI added to primary result",
            anchors=[{"quote": "Recall improved by 18.5% (95% CI [9.1, 27.9]",
                      "locator": "§Results ¶2 s1"}])
    add_comment(led, "R1-2", "Add the missing baseline table.", reviewer="R1")
    add_sub(led, "R1-2", "a", "provide baseline characteristics table",
            decision="pending")  # unanswered on purpose for the demo
    rep = consistency(led, revised)
    assert rep["anchors_verified"] == 2 and rep["unanswered"] == ["R1-2/a"], rep
    assert rep["改得准"] and not rep["答得全"]
    # a fabricated modification claim must be caught
    add_sub(led, "R1-2", "b", "add Table 1 with demographics", decision="adopt",
            reason="claimed but text never added",
            anchors=[{"quote": "Table 1 shows the baseline demographics of both arms.",
                      "locator": "§Results ¶1 s1"}])
    rep2 = consistency(led, revised)
    assert rep2["bad_anchors"], "unverifiable anchor must be flagged"
    print(json.dumps({"demo": "respond.consistency", "subs": rep["n_sub_requests"],
                      "verified_anchors": rep["anchors_verified"],
                      "fabricated_change_caught": bool(rep2["bad_anchors"])},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m arkit.respond <ledger.json> <revised_text_file> [out.json]
    led = json.load(open(sys.argv[1], encoding="utf-8"))
    rep = consistency(led, open(sys.argv[2], encoding="utf-8").read())
    if len(sys.argv) > 3:
        json.dump(led, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
