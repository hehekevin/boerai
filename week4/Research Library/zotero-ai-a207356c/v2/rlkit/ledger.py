"""Operation ledger for software automation: state snapshots, idempotence
assertions, failure recovery with rollback-to-state, terminal-state checks.

Every step of an automation chain (导入—设置—运行—导出—检查) records:
  pre_state  : sha256 of every file in the watched directory before the step
  post_state : same after the step
  terminal check: expected artifacts exist with size > 0
On failure the step is recorded with its error and rollback(step) restores
the watched directory to the pre-state copy — never retrying over half-made
output and never labelling an unrun step as done.  assert_idempotent re-runs
a step and asserts the post-state is identical (same file set, same hashes).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import traceback


def snapshot_state(root: str) -> dict:
    state = {}
    if not os.path.isdir(root):
        return state
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {"__pycache__", ".git"}]
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root)
            h = hashlib.sha256()
            try:
                with open(p, "rb") as fh:
                    for chunk in iter(lambda: fh.read(1 << 20), b""):
                        h.update(chunk)
                state[rel] = {"sha256": h.hexdigest(), "bytes": os.path.getsize(p)}
            except OSError:
                state[rel] = {"error": "unreadable"}
    return state


def diff_states(before: dict, after: dict) -> dict:
    keys = set(before) | set(after)
    return {"added": sorted(k for k in keys if k not in before),
            "removed": sorted(k for k in keys if k not in after),
            "changed": sorted(k for k in keys
                              if k in before and k in after and before[k] != after[k]),
            "unchanged": sorted(k for k in keys
                                if k in before and k in after and before[k] == after[k])}


class OpLedger:
    def __init__(self, watch_dir: str, ledger_path: str = None):
        self.watch = os.path.abspath(watch_dir)
        os.makedirs(self.watch, exist_ok=True)
        self.path = ledger_path or os.path.join(self.watch, ".op_ledger.json")
        self.entries = []
        self._snap_dir = os.path.join(self.watch, ".op_snapshots")
        os.makedirs(self._snap_dir, exist_ok=True)

    def _copy_tree(self, dest: str):
        if os.path.exists(dest):
            shutil.rmtree(dest)
        os.makedirs(dest)
        for rel in snapshot_state(self.watch):
            if rel.startswith(".op_"):
                continue
            src = os.path.join(self.watch, rel)
            tgt = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(tgt), exist_ok=True)
            shutil.copy2(src, tgt)

    def run_step(self, name: str, fn, expected_artifacts: list = None) -> dict:
        """fn() performs the real work inside watch_dir and returns detail dict."""
        pre = {k: v for k, v in snapshot_state(self.watch).items() if not k.startswith(".op_")}
        snap = os.path.join(self._snap_dir, f"step{len(self.entries) + 1:03d}_{name}")
        self._copy_tree(snap)
        entry = {"seq": len(self.entries) + 1, "step": name,
                 "pre_state": pre, "snapshot": snap}
        try:
            detail = fn() or {}
            post = {k: v for k, v in snapshot_state(self.watch).items()
                    if not k.startswith(".op_")}
            entry.update(status="done", detail=detail, post_state=post,
                         state_diff=diff_states(pre, post))
            missing = [a for a in (expected_artifacts or [])
                       if not (os.path.exists(os.path.join(self.watch, a))
                               and os.path.getsize(os.path.join(self.watch, a)) > 0)]
            entry["terminal_check"] = {"expected": expected_artifacts or [],
                                       "missing_or_empty": missing,
                                       "ok": not missing}
            if missing:
                entry["status"] = "terminal_failed"
        except Exception as exc:  # noqa: BLE001
            entry.update(status="failed", error=f"{type(exc).__name__}: {exc}",
                         traceback=traceback.format_exc()[-1200:])
        self.entries.append(entry)
        self._flush()
        return entry

    def rollback(self, seq: int) -> dict:
        entry = self.entries[seq - 1]
        snap = entry["snapshot"]
        for rel in list(snapshot_state(self.watch)):
            if not rel.startswith(".op_"):
                os.remove(os.path.join(self.watch, rel))
        restored = 0
        for dirpath, _, filenames in os.walk(snap):
            for fn in filenames:
                src = os.path.join(dirpath, fn)
                rel = os.path.relpath(src, snap)
                tgt = os.path.join(self.watch, rel)
                os.makedirs(os.path.dirname(tgt), exist_ok=True)
                shutil.copy2(src, tgt)
                restored += 1
        rec = {"seq": len(self.entries) + 1, "step": f"rollback:{entry['step']}",
               "status": "done", "restored_files": restored,
               "rollback_of": entry["seq"]}
        self.entries.append(rec)
        self._flush()
        return rec

    def assert_idempotent(self, name: str, fn) -> dict:
        """Run fn twice; the second run must not change any watched file."""
        e1 = self.run_step(name, fn)
        pre2 = {k: v for k, v in snapshot_state(self.watch).items() if not k.startswith(".op_")}
        e2 = self.run_step(name + "#rerun", fn)
        post2 = {k: v for k, v in snapshot_state(self.watch).items() if not k.startswith(".op_")}
        d = diff_states(pre2, post2)
        ok = not d["added"] and not d["removed"] and not d["changed"]
        rec = {"seq": len(self.entries) + 1, "step": f"idempotence:{name}",
               "status": "done" if ok else "idempotence_violation",
               "second_run_diff": d}
        self.entries.append(rec)
        self._flush()
        return {"ok": ok, "first": e1["status"], "second": e2["status"], "diff": d}

    def _flush(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"watch_dir": self.watch, "entries": self.entries}, fh,
                      ensure_ascii=False, indent=1)


def _demo() -> int:
    import tempfile
    tmp = tempfile.mkdtemp(prefix="ledger-demo-")
    led = OpLedger(tmp)

    def good_step():
        with open(os.path.join(tmp, "out.txt"), "w") as fh:
            fh.write("result")
        return {"wrote": "out.txt"}

    def bad_step():
        with open(os.path.join(tmp, "partial.tmp"), "w") as fh:
            fh.write("half-made")
        raise RuntimeError("simulated crash mid-step")

    e1 = led.run_step("export", good_step, expected_artifacts=["out.txt"])
    assert e1["status"] == "done" and e1["terminal_check"]["ok"]
    e2 = led.run_step("run", bad_step)
    assert e2["status"] == "failed" and "simulated crash" in e2["error"]
    rb = led.rollback(e2["seq"])
    assert not os.path.exists(os.path.join(tmp, "partial.tmp")), "rollback must remove half-made output"
    assert os.path.exists(os.path.join(tmp, "out.txt")), "rollback must keep earlier good state"
    # idempotence: writing identical content is idempotent
    idem = led.assert_idempotent("stable-export", good_step)
    assert idem["ok"], idem
    # a non-idempotent step (appends) must be caught
    def appender():
        with open(os.path.join(tmp, "log.txt"), "a") as fh:
            fh.write("x")
    bad_idem = led.assert_idempotent("appending-export", appender)
    assert not bad_idem["ok"]
    rep = json.load(open(led.path, encoding="utf-8"))
    assert len(rep["entries"]) == 9, len(rep["entries"])  # 2 steps + rollback + 2×(2 runs + verdict)
    print(json.dumps({"demo": "ledger.steps+rollback+idempotence",
                      "entries": len(rep["entries"]),
                      "rollback_restored": rb["restored_files"] >= 1,
                      "idempotent_ok": idem["ok"],
                      "violation_caught": not bad_idem["ok"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "snapshot":
        json.dump(snapshot_state(sys.argv[2]), open(sys.argv[3], "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"snapshot: {sys.argv[2]} -> {sys.argv[3]}")
    elif cmd == "diff":
        a = json.load(open(sys.argv[2], encoding="utf-8"))
        b = json.load(open(sys.argv[3], encoding="utf-8"))
        print(json.dumps(diff_states(a, b), ensure_ascii=False, indent=1))
    else:
        print("usage: ledger.py snapshot <dir> <out.json> | diff <before.json> <after.json>")
        sys.exit(2)
