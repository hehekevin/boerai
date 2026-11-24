"""Statistics-report detectors: locate numeric claims, record OBSERVATIONS.

The engine never says "the statistics are wrong". It locates numeric claims
(p-values, CIs, effect sizes, n=, percentages, mean±SD) with locators and
records which companion quantities are present or absent nearby. Absence of
a companion quantity is an *observation* the agent may turn into a finding —
or may legitimately dismiss (e.g. descriptive table). This keeps verdicts
honest and false positives controllable.
"""
from __future__ import annotations

import json
import re
import sys

from . import locate

RX = {
    "p_value": re.compile(r"\bp\s*[<=>≤≥]\s*0?\.\d+", re.I),
    "ci": re.compile(r"(95\s*%\s*CI|confidence interval|置信区间)[:：]?\s*[\[\(]?\-?\d", re.I),
    "n_size": re.compile(r"\bn\s*=\s*\d+", re.I),
    "percent": re.compile(r"\d+(?:\.\d+)?\s*%"),
    "mean_sd": re.compile(r"\d+(?:\.\d+)?\s*[±\+/-]\s*\d+(?:\.\d+)?"),
    "effect": re.compile(r"\b(OR|RR|HR|Cohen'?s?\s*d|odds ratio|risk ratio|hazard ratio|"
                         r"效应量)\s*[=of为]*\s*\d*\.\d+", re.I),
    "df_stat": re.compile(r"\b(t|F|χ2|chi-?square|z|U)\s*\(\s*\d+[\d, ]*\)\s*=\s*\d", re.I),
    "sample_words": re.compile(r"\b(\d+)\s+(participants|patients|subjects|donors|mice|rats|"
                               r"samples|名|例)(?!\d)", re.I),
}


def detect(text: str) -> dict:
    """All numeric/statistical mentions with locators + companion-presence window."""
    units = locate.split_units(text)
    claims = []
    for u in units:
        found = {k: [m.group(0) for m in rx.finditer(u["text"])] for k, rx in RX.items()}
        found = {k: v for k, v in found.items() if v}
        if not found:
            continue
        has_n = bool(found.get("n_size") or found.get("sample_words"))
        has_p = bool(found.get("p_value"))
        has_ci = bool(found.get("ci"))
        claims.append({"locator": u["locator"], "section": u["section"],
                       "text": u["text"][:240], "quantities": found,
                       "companions": {"n": has_n, "p": has_p, "ci": has_ci}})
    # observations: significance claims without CI / effect size nearby (same sentence)
    obs = []
    for c in claims:
        q = c["quantities"]
        if q.get("p_value") and not c["companions"]["ci"] and not q.get("effect"):
            obs.append({"kind": "p_without_ci_or_effect", "locator": c["locator"],
                        "quote": c["text"],
                        "note": "observation only: p reported without CI/effect size in the same "
                                "sentence; agent decides if this is a report-completeness issue"})
        if (q.get("percent") or q.get("mean_sd")) and not c["companions"]["n"]:
            obs.append({"kind": "numeric_without_n", "locator": c["locator"],
                        "quote": c["text"],
                        "note": "observation only: percentage/± value without n in the same sentence"})
    sig_words = locate.find_mentions(
        text, r"\b(significant|significantly|highly significant|显著|极显著)\b")
    vague_sig = [s for s in sig_words
                 if not RX["p_value"].search(s["context"]) and not RX["ci"].search(s["context"])]
    for s in vague_sig:
        obs.append({"kind": "significance_word_without_stats", "locator": s["locator"],
                    "quote": s["context"],
                    "note": "observation only: 'significant' without p/CI in the same sentence"})
    return {"n_claim_sentences": len(claims), "claims": claims,
            "observations": obs,
            "policy": "detectors emit observations; only the agent (with quote+locator+"
                      "justification, validated by findings.validate) may enter a finding"}


def _demo() -> int:
    text = ("# Methods\n\nWe enrolled 60 participants (n = 60 in the final analysis).\n\n"
            "# Results\n\nThe treatment group improved by 18.5% (p = 0.032) versus control. "
            "Mean score was 7.2 ± 1.1 in controls. "
            "The secondary endpoint was significantly higher. "
            "Reaction time dropped (OR = 0.61, 95% CI [0.40, 0.93], p = 0.021).")
    rep = detect(text)
    kinds = sorted({o["kind"] for o in rep["observations"]})
    assert "p_without_ci_or_effect" in kinds, kinds          # 18.5% (p=0.032) lacks CI/effect
    assert "significance_word_without_stats" in kinds        # 'significantly higher'
    assert "numeric_without_n" in kinds                      # 7.2 ± 1.1 without n in sentence
    # the fully reported OR sentence must NOT raise p_without_ci_or_effect
    assert not any(o["kind"] == "p_without_ci_or_effect" and "OR = 0.61" in o["quote"]
                   for o in rep["observations"])
    print(json.dumps({"demo": "stats.detect", "claim_sentences": rep["n_claim_sentences"],
                      "observations": len(rep["observations"]), "kinds": kinds},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m arkit.stats <text_file> [out.json]
    rep = detect(open(sys.argv[1], encoding="utf-8").read())
    if len(sys.argv) > 2:
        json.dump(rep, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{rep['n_claim_sentences']} claim sentences, {len(rep['observations'])} observations -> {sys.argv[2]}")
    else:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
