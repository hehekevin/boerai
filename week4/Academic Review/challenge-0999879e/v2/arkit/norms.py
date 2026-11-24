"""Academic norms & compliance presence detectors.

For 学术规范与合规检查. The engine scans for presence/absence of required
declarations (ethics approval, informed consent, conflict of interest, data
availability, funding, author contributions, license statements) and for
patterns that LOOK like personal data (emails, phone numbers, ID-like numbers).
Presence/absence and pattern hits are observations with locators. Absence of
a declaration is "not found in the provided text" — never "the study is
unethical"; a pattern hit is "worth a human look", never "this IS a leak".
"""
from __future__ import annotations

import json
import re
import sys

from . import locate

DECLARATIONS = {
    "ethics_approval": r"(ethic(s|al)? (approval|committee|review board)|IRB|"
                       r"伦理(委员会|审批|审查)|批件|批准号)",
    "informed_consent": r"(informed consent|知情同意)",
    "conflict_of_interest": r"(conflict(s)? of interest|competing interest|利益冲突)",
    "data_availability": r"(data (are |is )?available|availability of data|"
                         r"数据(可|的)可用性|数据获取|共享数据)",
    "funding": r"(funding|supported by|grant(s)? (no\.?|number)|基金|资助)",
    "author_contributions": r"(author contribution|contributions?:|作者贡献)",
    "animal_welfare": r"(animal (care|welfare|ethics)|IACUC|实验动物|动物伦理)",
    "license_reuse": r"(licen[cs]e|CC-?BY|Creative Commons|permission (was )?obtained|"
                       r"获得授权|许可)",
}
PII_PATTERNS = {
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "phone": r"(?<!\d)(?:\+?\d[\d\- ]{8,14}\d)(?!\d)",
    "id_like": r"(?<!\d)\d{15,18}[0-9Xx]?(?!\d)",
}


def scan(text: str) -> dict:
    decl = {}
    for name, pat in DECLARATIONS.items():
        hits = locate.find_mentions(text, pat)
        decl[name] = {"present": bool(hits), "n_hits": len(hits),
                      "locations": [h["locator"] for h in hits[:5]],
                      "examples": [h["context"][:120] for h in hits[:2]],
                      "note": ("found in provided text" if hits else
                               "NOT found in provided text — observation, not a violation verdict")}
    pii = {}
    for name, pat in PII_PATTERNS.items():
        hits = locate.find_mentions(text, pat, flags=0)
        pii[name] = {"n_hits": len(hits),
                     "hits": [{"locator": h["locator"], "match": h["match"]} for h in hits[:10]],
                     "note": "pattern hit = worth a human look, not proof of a privacy leak"}
    missing = [k for k, v in decl.items() if not v["present"]]
    return {"declarations": decl, "pii_scan": pii, "missing_declarations": missing,
            "policy": "absence in provided text != violation; report as 待复核 when the "
                      "declaration could live outside the provided material"}


def _demo() -> int:
    text = ("# Methods\n\nThe protocol was approved by the institutional ethics committee "
            "(approval no. 2021-034) and all participants gave informed consent.\n\n"
            "# Declarations\n\nThe authors declare no conflict of interest. "
            "Data are available on request. Contact: jdoe@example.edu for materials.")
    rep = scan(text)
    assert rep["declarations"]["ethics_approval"]["present"]
    assert rep["declarations"]["informed_consent"]["present"]
    assert rep["declarations"]["conflict_of_interest"]["present"]
    assert rep["declarations"]["data_availability"]["present"]
    assert not rep["declarations"]["funding"]["present"]
    assert "funding" in rep["missing_declarations"]
    assert rep["pii_scan"]["email"]["n_hits"] == 1
    clean = "# Results\n\nNothing to declare here, just results text."
    rep2 = scan(clean)
    assert len(rep2["missing_declarations"]) == len(DECLARATIONS)
    print(json.dumps({"demo": "norms.scan", "missing": rep["missing_declarations"],
                      "pii_email_hits": rep["pii_scan"]["email"]["n_hits"],
                      "all_missing_on_bare_text": len(rep2["missing_declarations"])},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m arkit.norms <text_file> [out.json]
    rep = scan(open(sys.argv[1], encoding="utf-8").read())
    if len(sys.argv) > 2:
        json.dump(rep, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"missing_declarations": rep["missing_declarations"],
                      "pii": {k: v["n_hits"] for k, v in rep["pii_scan"].items()}},
                     ensure_ascii=False))
