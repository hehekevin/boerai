"""Claim candidates: strength, attribution and causal language.

For logic/argument review the agent needs a checklist of claims, not prose.
The engine flags candidate claim sentences and classifies, by markers only:
  attribution: author | cited_other | hypothesis  (who is speaking)
  strength:    strong | hedged                    (modal/hedge words)
  causality:   causal | correlational | none      (verb markers)
Candidates are starting points; the agent verifies attribution (a frequent
false positive is reporting another group's view as if it were the authors').
"""
from __future__ import annotations

import json
import re
import sys

from . import locate

CLAIM_MARKERS = re.compile(
    r"\b(we (show|demonstrate|found|find|conclude|propose|argue|observed?|report)|"
    r"our (results|data|findings|analysis) (show|suggest|demonstrate|indicate)|"
    r"these results (show|suggest|demonstrate|indicate|prove)|"
    r"therefore|thus|hence|we conclude|in conclusion|"
    r"表明|证明|显示|说明|得出结论|我们认为|本文发现)\b", re.I)
CITED = re.compile(r"\[\d+[\d,\-\s]*\]|\([A-Z][A-Za-z\-]+( et al\.?)?,? \d{4}\)|"
                   r"(previous|prior) (work|studies|research)|据报道|已有研究", re.I)
HYPOTHESIS = re.compile(r"\b(we hypothesi[sz]e|hypothesis|we assume|if .+ then|"
                        r"假设|假定|若.*则)\b", re.I)
HEDGE = re.compile(r"\b(may|might|could|possibly|potentially|suggest|appear|seem|"
                   r"likely|perhaps|似乎|可能|或许|也许)\b", re.I)
STRONG = re.compile(r"\b(prove|proven|demonstrate|establish|conclusively|definitively|"
                    r"clearly|undoubtedly|证实|证明|明确表明)\b", re.I)
CAUSAL = re.compile(r"\b(cause[sd]?|causes|causal|lead[sd]? to|leads to|result[sd]? in|"
                    r"drive[ns]?|determine[sd]?|increase[sd]?|decrease[sd]?|reduce[sd]?|"
                    r"improve[sd]?|impair[sd]?|affect[sd]?|导致|引起|促进|抑制|改善)\b", re.I)
CORREL = re.compile(r"\b(associat\w+|correlat\w+|linked|related to|co-?var\w+|"
                    r"相关|伴随|联系)\b", re.I)


def extract(text: str) -> dict:
    cands = []
    for u in locate.split_units(text):
        t = u["text"]
        if not (CLAIM_MARKERS.search(t) or CAUSAL.search(t) or STRONG.search(t)
                or CORREL.search(t) or HYPOTHESIS.search(t)):
            continue
        attr = ("hypothesis" if HYPOTHESIS.search(t)
                else "cited_other" if CITED.search(t) else "author")
        strength = "strong" if STRONG.search(t) and not HEDGE.search(t) else "hedged"
        causality = ("causal" if CAUSAL.search(t)
                     else "correlational" if CORREL.search(t) else "none")
        cands.append({"locator": u["locator"], "section": u["section"],
                      "quote": t[:240], "attribution": attr, "strength": strength,
                      "causality": causality,
                      "needs": "agent verifies attribution & evidence support"})
    causal_strong = [c for c in cands if c["causality"] == "causal"
                     and c["strength"] == "strong" and c["attribution"] == "author"]
    return {"n_candidates": len(cands), "candidates": cands,
            "review_queue": {"strong_causal_author_claims":
                             [c["locator"] for c in causal_strong]},
            "note": "markers only; cited_other/hypothesis must NOT be reported as "
                    "author self-contradiction (common false positive)"}


def _demo() -> int:
    text = ("# Introduction\n\nPrior work showed that caffeine improves alertness [3].\n\n"
            "# Results\n\nOur results demonstrate that the intervention improves recall "
            "performance. We hypothesize that sleep mediates this effect. "
            "Reaction time was associated with dosage.")
    rep = extract(text)
    by_attr = {}
    for c in rep["candidates"]:
        by_attr[c["attribution"]] = by_attr.get(c["attribution"], 0) + 1
    assert by_attr.get("cited_other", 0) >= 1      # prior-work sentence not an author claim
    assert by_attr.get("hypothesis", 0) >= 1       # hypothesize sentence
    assert rep["review_queue"]["strong_causal_author_claims"]  # 'demonstrate ... improves'
    assoc = [c for c in rep["candidates"] if "associated" in c["quote"]]
    assert assoc and assoc[0]["causality"] == "correlational"
    print(json.dumps({"demo": "claims.extract", "candidates": rep["n_candidates"],
                      "by_attribution": by_attr,
                      "review_queue": rep["review_queue"]["strong_causal_author_claims"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m arkit.claims <text_file> [out.json]
    rep = extract(open(sys.argv[1], encoding="utf-8").read())
    if len(sys.argv) > 2:
        json.dump(rep, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"n_candidates": rep["n_candidates"],
                      "review_queue": rep["review_queue"]}, ensure_ascii=False))
