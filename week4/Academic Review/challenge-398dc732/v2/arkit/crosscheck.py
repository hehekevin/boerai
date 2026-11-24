"""Reference-claim cross-check: does the cited source support the in-text claim?

Inputs come from the agent/materials: an in-text claim (quote + locator in the
manuscript) and a snippet from the cited source (quote + source id). The engine
computes token-level similarity, highlights shared/missing content words, and
proposes one of four statuses: supported | partial | unsupported | undeterminable.
The proposal is advisory: the agent confirms or overrides it with a reason,
and only then may a citation finding enter the ledger.
"""
from __future__ import annotations

import json
import re
import sys

STOP = set("""the a an of to in and or is are was were be been by for with on at as that this
these those it its we our they their from into over under between among can could may might
shall should will would have has had do does did not no than then thus hence also more most
such other which who whom what when where why how all any each both few many much some very
s et al 的 了 和 与 在 是 对 为 等 及 其 中 由 于 或 而 被 所 以 之""".split())


def tokens(text: str) -> list[str]:
    toks = re.findall(r"[A-Za-z][A-Za-z\-]{2,}|[0-9]+(?:\.[0-9]+)?|[一-鿿]", text or "")
    return [t.lower() for t in toks if t.lower() not in STOP]


def content_overlap(a: str, b: str) -> dict:
    ta, tb = set(tokens(a)), set(tokens(b))
    if not ta or not tb:
        return {"score": 0.0, "shared": [], "claim_only": sorted(ta)[:20],
                "source_only": sorted(tb)[:20]}
    shared = ta & tb
    # asymmetric: how much of the *claim* is covered by the source
    cover = len(shared) / len(ta)
    jac = len(shared) / len(ta | tb)
    return {"score": round(0.7 * cover + 0.3 * jac, 4),
            "claim_coverage": round(cover, 4), "jaccard": round(jac, 4),
            "shared": sorted(shared)[:40], "claim_only": sorted(ta - tb)[:20],
            "source_only": sorted(tb - ta)[:20]}


def compare(claim: dict, source: dict) -> dict:
    """claim={quote,locator,ref_key} source={quote,source_id,locator?}."""
    ov = content_overlap(claim.get("quote", ""), source.get("quote", ""))
    s = ov["score"]
    if not source.get("quote"):
        proposal = "undeterminable"
    elif s >= 0.55:
        proposal = "supported"
    elif s >= 0.30:
        proposal = "partial"
    else:
        proposal = "unsupported"
    return {"ref_key": claim.get("ref_key", ""), "source_id": source.get("source_id", ""),
            "side_by_side": {"claim_quote": claim.get("quote", ""),
                             "claim_locator": claim.get("locator", ""),
                             "source_quote": source.get("quote", ""),
                             "source_locator": source.get("locator", "")},
            "overlap": ov, "proposal": proposal,
            "note": "proposal is advisory; agent must confirm/override with reason before "
                    "any citation finding enters the ledger"}


def batch(pairs: list[dict]) -> dict:
    out = [compare(p.get("claim", {}), p.get("source", {})) for p in pairs]
    tally: dict = {}
    for o in out:
        tally[o["proposal"]] = tally.get(o["proposal"], 0) + 1
    return {"n": len(out), "tally": tally, "pairs": out,
            "policy": "unsupported/partial proposals need agent confirmation + both quotes "
                      "in the ledger side by side"}


def _demo() -> int:
    claim = {"quote": "Sleep deprivation impairs memory consolidation in adults [12].",
             "locator": "§Introduction ¶1 s3", "ref_key": "[12]"}
    good = {"quote": "We show that sleep deprivation significantly impairs memory "
                     "consolidation in healthy adults.", "source_id": "S12", "locator": "p.3 ¶2"}
    bad = {"quote": "Caffeine intake was unrelated to reaction time in adolescents.",
           "source_id": "S12", "locator": "p.5 ¶1"}
    r1 = compare(claim, good)
    r2 = compare(claim, bad)
    r3 = compare(claim, {"quote": "", "source_id": "S12"})
    assert r1["proposal"] == "supported", r1["overlap"]
    assert r2["proposal"] == "unsupported", r2["overlap"]
    assert r3["proposal"] == "undeterminable"
    rep = batch([{"claim": claim, "source": good}, {"claim": claim, "source": bad}])
    assert rep["tally"] == {"supported": 1, "unsupported": 1}
    print(json.dumps({"demo": "crosscheck.compare", "supported_score": r1["overlap"]["score"],
                      "unsupported_score": r2["overlap"]["score"],
                      "undeterminable_when_no_source_text": r3["proposal"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m arkit.crosscheck <pairs.json> [out.json]
    # pairs.json: [{"claim": {quote,locator,ref_key}, "source": {quote,source_id,locator}}, ...]
    rep = batch(json.load(open(sys.argv[1], encoding="utf-8")))
    if len(sys.argv) > 2:
        json.dump(rep, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"n": rep["n"], "tally": rep["tally"]}, ensure_ascii=False))
