"""arkit — academic review engine (stdlib only).

Deterministic bookkeeping for manuscript/literature audit. The engine never
decides that a defect exists: it locates text, validates that every finding
carries a verifiable quote + locator + justification, counts coverage, and
assembles reports. Semantic judgment belongs to the agent; the engine makes
it auditable and refuses unverifiable claims. "No defect found" is a valid,
honest outcome.

Modules:
  locate       text anchoring: §/p.N/paragraph/table locators, quote verification
  findings     typed audit ledger + validator (rejects quote-less / unverifiable findings)
  checklist    facet checklists with per-item rule, required evidence, coverage
  stats        statistics-report detectors (numeric claims -> observations, not verdicts)
  crosscheck   in-text claim vs cited-source snippet side-by-side comparison
  claims       claim/argument candidates: author vs cited vs hypothesis, causal markers
  consistency  cross-section numeric/statement consistency observations
  quality      literature quality-appraisal scale (dimension-judgment-evidence-grade)
  respond      reviewer-response ledger (decompose, decide, anchor, verify)
  norms        academic norms/compliance presence detectors (ethics, COI, data, PII)
  report       review-report builder (counts, coverage, 待复核, status)
"""
__version__ = "1.0.0"
MODULES = ["locate", "findings", "checklist", "stats", "crosscheck", "claims",
           "consistency", "quality", "respond", "norms", "report"]
