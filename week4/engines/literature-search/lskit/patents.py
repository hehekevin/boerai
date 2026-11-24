"""Patent & technical-literature helpers: number normalisation, family
grouping, legal-status annotation, authorized-source tracking, risk flags.

All inputs come from case-provided snapshots; the engine never fetches live
registers and never invents a legal status.
"""
from __future__ import annotations

import json
import re
import sys

PAT_RE = re.compile(r"\b([A-Z]{2})\s?(\d{4,12})\s?([AB]\d?)?\b")


def norm_patent_number(s: str) -> dict:
    m = PAT_RE.search((s or "").upper().replace("-", " ").replace(",", ""))
    if not m:
        return {"raw": s, "ok": False}
    return {"raw": s, "ok": True, "country": m.group(1), "number": m.group(2),
            "kind": m.group(3) or "", "normalized": f"{m.group(1)}{m.group(2)}{m.group(3) or ''}"}


def group_families(records: list[dict]) -> dict:
    """records: [{id, patent, family_id?, title, source_db, legal_status?, register_date?}]"""
    families: dict[str, list] = {}
    problems = []
    for r in records:
        pn = norm_patent_number(r.get("patent", ""))
        if not pn["ok"]:
            problems.append({"id": r.get("id"), "problem": f"unparseable patent number '{r.get('patent')}'"})
            fam = r.get("family_id") or f"UNPARSED:{r.get('id')}"
        else:
            fam = r.get("family_id") or f"{pn['country']}:{pn['number']}"
        r2 = dict(r)
        r2["normalized"] = pn.get("normalized")
        families.setdefault(fam, []).append(r2)
    out = []
    for fam, members in sorted(families.items()):
        statuses = {m.get("legal_status") for m in members if m.get("legal_status")}
        out.append({"family_id": fam, "members": [m.get("id") for m in members],
                    "member_n": len(members),
                    "countries": sorted({(norm_patent_number(m.get("patent", "")).get("country") or "?")
                                          for m in members}),
                    "legal_statuses": sorted(s for s in statuses if s),
                    "status_conflict": len(statuses) > 1,
                    "sources": sorted({m.get("source_db") or "unknown" for m in members})})
    return {"families": out, "family_n": len(out), "problems": problems,
            "note": "法律状态只标注来源快照中给出的值；status_conflict 须人工核对官方登记"}


AUTHORIZED = {"crossref", "europepmc", "openalex", "lens_snapshot", "espacenet_snapshot",
              "cnipa_snapshot", "uspto_snapshot", "case_provided"}


def authorization_check(records: list[dict], extra_authorized: list[str] | None = None) -> dict:
    allowed = set(AUTHORIZED) | set(extra_authorized or [])
    bad = [{"id": r.get("id"), "source_db": r.get("source_db"),
            "problem": "source not in authorized list; exclude or justify"} for r in records
           if (r.get("source_db") or "unknown") not in allowed]
    return {"checked": len(records), "unauthorized": bad, "ok": not bad,
            "note": "结果只来自有授权来源，并标注库名/版本/查询日期"}


def risk_flags(records: list[dict]) -> list[dict]:
    flags = []
    for r in records:
        f = []
        if not r.get("legal_status"):
            f.append("legal_status_missing")
        if not r.get("register_date") and not r.get("query_date"):
            f.append("no_query_date_recorded")
        if r.get("title") and not r.get("abstract"):
            f.append("abstract_missing")
        if f:
            flags.append({"id": r.get("id"), "flags": f})
    return flags


def _demo() -> int:
    recs = [{"id": "X1", "patent": "US 10,000,111 B2", "family_id": "F1", "source_db": "uspto_snapshot",
             "legal_status": "active", "query_date": "2026-11-01"},
            {"id": "X2", "patent": "CN110000111A", "family_id": "F1", "source_db": "cnipa_snapshot",
             "legal_status": "pending", "query_date": "2026-11-01"},
            {"id": "X3", "patent": "EP 3000000", "family_id": "F2", "source_db": "random_blog"}]
    fam = group_families(recs)
    assert fam["family_n"] == 2
    f1 = next(f for f in fam["families"] if f["family_id"] == "F1")
    assert f1["status_conflict"] is True
    auth = authorization_check(recs)
    assert not auth["ok"] and auth["unauthorized"][0]["id"] == "X3"
    flags = risk_flags(recs)
    assert any(fl["id"] == "X3" for fl in flags)
    print(json.dumps({"demo": "patents", "families": fam["family_n"],
                      "f1_conflict": f1["status_conflict"],
                      "unauthorized": len(auth["unauthorized"]),
                      "flagged": len(flags)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    recs = json.load(open(sys.argv[2], encoding="utf-8"))
    recs = recs.get("records", recs)
    if cmd == "families":
        rep = group_families(recs)
    elif cmd == "authz":
        rep = authorization_check(recs)
    elif cmd == "risk":
        rep = {"flags": risk_flags(recs)}
    else:
        print("usage: patents.py [families|authz|risk] records.json out.json"); sys.exit(2)
    json.dump(rep, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{cmd} done -> {sys.argv[3]}")
