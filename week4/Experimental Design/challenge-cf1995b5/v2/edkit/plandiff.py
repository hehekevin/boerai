"""Version diff: two plan structures -> added / removed / changed items.

Both versions are typed structures (edkit.planparse schema). Items are keyed
by id (fallback: name/index). Changed items carry the differing fields with
old and new values AND the locators from both versions, so a reviewer can
tell whether the plan changed or the review was wrong. Any change to typed
content is conservatively judged feasibility-affecting: the checklist must be
re-run, never inherited from the previous version's verdict.
"""
from __future__ import annotations

import json
import sys

LISTS = ("sections", "parameters", "steps", "resources", "controls", "variables", "risks_stated")


def _key(item: dict) -> str:
    return str(item.get("id") or item.get("name") or item.get("index") or json.dumps(item, sort_keys=True, ensure_ascii=False)[:40])


def diff_structures(old: dict, new: dict) -> dict:
    added, removed, changed = [], [], []
    for lst in LISTS:
        o = {_key(i): i for i in old.get(lst) or []}
        n = {_key(i): i for i in new.get(lst) or []}
        for k in sorted(n.keys() - o.keys()):
            added.append({"list": lst, "key": k, "item": n[k],
                          "locator": n[k].get("locator", "")})
        for k in sorted(o.keys() - n.keys()):
            removed.append({"list": lst, "key": k, "item": o[k],
                            "locator": o[k].get("locator", "")})
        for k in sorted(o.keys() & n.keys()):
            fields = {}
            for f in sorted(set(o[k]) | set(n[k])):
                if o[k].get(f) != n[k].get(f):
                    fields[f] = {"old": o[k].get(f), "new": n[k].get(f)}
            if fields:
                changed.append({"list": lst, "key": k, "fields": fields,
                                "locator_old": o[k].get("locator", ""),
                                "locator_new": n[k].get("locator", "")})
    n_changes = len(added) + len(removed) + len(changed)
    verdict = "no_changes" if n_changes == 0 else "changes_affect_feasibility"
    return {"verdict": verdict,
            "verdict_label": {"no_changes": "两版一致，原审查结论可沿用",
                              "changes_affect_feasibility": "存在内容变更，检查项必须重跑，不得沿用旧结论"}[verdict],
            "added": added, "removed": removed, "changed": changed,
            "counts": {"added": len(added), "removed": len(removed), "changed": len(changed)},
            "rule_note": "any typed-content change forces a checklist re-run; "
                         "locators from BOTH versions are carried so plan-edit vs review-error is decidable"}


def _demo() -> int:
    v1 = {"source": "plan v1",
          "parameters": [{"id": "P1", "name": "温度", "value": "37", "unit": "℃", "locator": "L5"},
                          {"id": "P2", "name": "时长", "value": "48", "unit": "h", "locator": "L6"}],
          "steps": [{"id": "ST1", "index": 1, "text": "准备样品", "locator": "L10"},
                     {"id": "ST2", "index": 2, "text": "记录基线", "locator": "L11"}],
          "resources": [{"id": "R1", "text": "盐雾箱 SY-9", "locator": "L15"}]}
    v2 = {"source": "plan v2",
          "parameters": [{"id": "P1", "name": "温度", "value": "40", "unit": "℃", "locator": "L5"},
                          {"id": "P2", "name": "时长", "value": "48", "unit": "h", "locator": "L6"}],
          "steps": [{"id": "ST1", "index": 1, "text": "准备样品", "locator": "L10"},
                     {"id": "ST3", "index": 3, "text": "增加平行重复", "locator": "L12"}],
          "resources": []}
    rep = diff_structures(v1, v2)
    assert rep["verdict"] == "changes_affect_feasibility"
    assert rep["counts"] == {"added": 1, "removed": 2, "changed": 1}, rep["counts"]
    ch = rep["changed"][0]
    assert ch["key"] == "P1" and ch["fields"]["value"] == {"old": "37", "new": "40"}
    assert ch["locator_old"] == "L5" and ch["locator_new"] == "L5"
    same = diff_structures(v1, v1)
    assert same["verdict"] == "no_changes"
    print(json.dumps({"demo": "plandiff", "counts": rep["counts"],
                      "verdict": rep["verdict"], "identical_verdict": same["verdict"]},
                     ensure_ascii=False))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[0] == "diff":
        old = json.load(open(argv[1], encoding="utf-8"))
        new = json.load(open(argv[2], encoding="utf-8"))
        rep = diff_structures(old, new)
        out = argv[3] if len(argv) > 3 else None
        if out:
            json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps({"verdict": rep["verdict"], "counts": rep["counts"]}, ensure_ascii=False))
        return 0
    print("usage: plandiff diff <old_struct.json> <new_struct.json> [out.json]")
    return 2


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    sys.exit(main(sys.argv[1:]))
