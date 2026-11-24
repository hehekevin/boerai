"""Tag / collection operations with audit log, idempotence and rollback.

Library state: {item_key: {"tags": [...], "collections": [...]}}.
Operations: add_tag / remove_tag / assign_collection / remove_collection.
Guarantees:
  * idempotent — applying the same op twice leaves state unchanged and the
    second application is logged with status "already" (no fake "applied");
  * audited — every op logs {seq, op, item, value, before, after, status};
  * rollback — inverse_ops(audit) returns the exact inverse sequence, and
    applying it restores the initial state (asserted in _demo);
  * wrong-target protection — ops on unknown items are refused and logged,
    tags never silently land on a neighbouring item.
"""
from __future__ import annotations

import copy
import json
import sys

OPS = {
    "add_tag": ("tags", "add"), "remove_tag": ("tags", "remove"),
    "assign_collection": ("collections", "add"),
    "remove_collection": ("collections", "remove"),
}
INVERSE = {"add_tag": "remove_tag", "remove_tag": "add_tag",
           "assign_collection": "remove_collection",
           "remove_collection": "assign_collection"}


def apply_op(state: dict, op: dict, audit: list, strict: bool = True) -> dict:
    name, item, value = op.get("op"), op.get("item"), op.get("value")
    seq = len(audit) + 1
    if name not in OPS:
        audit.append({"seq": seq, "op": name, "item": item, "value": value,
                      "status": "refused", "reason": "unknown_op"})
        return state
    field, how = OPS[name]
    st = copy.deepcopy(state)
    if item not in st:
        if strict:
            audit.append({"seq": seq, "op": name, "item": item, "value": value,
                          "status": "refused", "reason": "unknown_item"})
            return state
        st[item] = {"tags": [], "collections": []}
    before = sorted(st[item][field])
    cur = set(st[item][field])
    if how == "add":
        cur.add(value)
    else:
        cur.discard(value)
    after = sorted(cur)
    if before == after:
        status = "already" if how == "add" else "absent"
    else:
        st[item][field] = after
        status = "applied"
    audit.append({"seq": seq, "op": name, "item": item, "value": value,
                  "before": before, "after": after, "status": status})
    return st


def apply_ops(state: dict, ops: list, strict: bool = True) -> dict:
    st, audit = copy.deepcopy(state), []
    for op in ops:
        st = apply_op(st, op, audit, strict=strict)
    return {"state": st, "audit": audit,
            "report": {"ops": len(ops),
                       "applied": sum(1 for a in audit if a["status"] == "applied"),
                       "already": sum(1 for a in audit if a["status"] == "already"),
                       "absent": sum(1 for a in audit if a["status"] == "absent"),
                       "refused": sum(1 for a in audit if a["status"] == "refused")}}


def inverse_ops(audit: list) -> list:
    """Exact inverse of the applied ops, in reverse order."""
    return [{"op": INVERSE[a["op"]], "item": a["item"], "value": a["value"]}
            for a in reversed(audit) if a["status"] == "applied"]


def rollback(state: dict, audit: list) -> dict:
    res = apply_ops(state, inverse_ops(audit), strict=False)
    return {"state": res["state"], "rollback_audit": res["audit"],
            "report": {"rolled_back_ops": len(inverse_ops(audit))}}


def _demo() -> int:
    state = {"A1": {"tags": ["protein"], "collections": ["proj-x"]},
             "B2": {"tags": [], "collections": []}}
    ops = [
        {"op": "add_tag", "item": "A1", "value": "ml"},
        {"op": "add_tag", "item": "A1", "value": "ml"},          # idempotent
        {"op": "remove_tag", "item": "A1", "value": "protein"},
        {"op": "assign_collection", "item": "B2", "value": "proj-x"},
        {"op": "add_tag", "item": "GHOST", "value": "oops"},     # refused
        {"op": "remove_tag", "item": "B2", "value": "nothing"},  # absent
    ]
    res = apply_ops(state, ops)
    rep = res["report"]
    assert rep["applied"] == 3 and rep["already"] == 1 and rep["refused"] == 1, rep
    assert res["state"]["A1"]["tags"] == ["ml"]
    assert "GHOST" not in res["state"]
    rb = rollback(res["state"], res["audit"])
    assert rb["state"] == state, "rollback must restore the exact initial state"
    print(json.dumps({"demo": "tags.apply+rollback", **rep,
                      "rollback_restored": rb["state"] == state}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    state = json.load(open(sys.argv[1], encoding="utf-8"))
    ops = json.load(open(sys.argv[2], encoding="utf-8"))
    ops = ops.get("ops", ops) if isinstance(ops, dict) else ops
    json.dump(apply_ops(state, ops), open(sys.argv[3], "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"tags: {len(ops)} ops -> {sys.argv[3]}")
