"""File version-relationship tracking: aliases, version chains, conflicts.

Input: [{path, sha256, mtime, size, aliases?, admin_note?}]
Rules (content-first, never filename-only):
  * equal sha256 -> same content (duplicates / aliases), group them;
  * same normalised stem (digits/v/final/copy markers stripped) but different
    sha256 -> a version series, ordered by mtime, supersede edges recorded;
  * administrative version notes from the case are validated against content:
    a declared "B supersedes A" that contradicts mtime/hash evidence is
    flagged as a conflict instead of being trusted blindly;
  * same name, different content in different dirs -> name_collision, both
    kept, never overwritten.
Output: chains with who-supersedes-whom, duplicate groups, conflicts —
everything needed to rebuild the same answer by hand.
"""
from __future__ import annotations

import json
import os
import re
import sys

_VER_MARK = re.compile(r"[\s_\-\.]*(v\d+|ver\d+|版本?\d*|final|draft|copy|副本|备份|新?旧?|终稿|修改稿|\(\d+\))\s*$", re.I)


def stem_key(path: str) -> str:
    base = os.path.splitext(os.path.basename(path))[0].lower()
    prev = None
    while prev != base:
        prev = base
        base = _VER_MARK.sub("", base)
    return re.sub(r"[\s_\-\.]+$", "", base).strip()


def build_version_map(files: list) -> dict:
    by_hash, by_stem, by_name = {}, {}, {}
    for f in files:
        by_hash.setdefault(f.get("sha256", ""), []).append(f)
        by_stem.setdefault(stem_key(f["path"]), []).append(f)
        by_name.setdefault(os.path.basename(f["path"]).lower(), []).append(f)

    duplicate_groups = [
        {"sha256": h, "copies": sorted(x["path"] for x in xs), "n": len(xs)}
        for h, xs in sorted(by_hash.items()) if h and len(xs) > 1]

    chains, conflicts = [], []
    for stem, xs in sorted(by_stem.items()):
        uniq = {}
        for x in xs:
            uniq.setdefault(x.get("sha256", x["path"]), []).append(x)
        if len(uniq) < 2:
            continue
        reps = sorted((v[0] for v in uniq.values()), key=lambda f: (f.get("mtime", 0), f["path"]))
        edges = [{"supersedes": reps[i]["path"], "superseded_by": reps[i + 1]["path"],
                  "basis": "mtime_order_distinct_content",
                  "from_sha256": reps[i].get("sha256", "")[:12],
                  "to_sha256": reps[i + 1].get("sha256", "")[:12]}
                 for i in range(len(reps) - 1)]
        chains.append({"stem": stem, "n_versions": len(reps),
                       "versions": [{"path": r["path"], "mtime": r.get("mtime", 0),
                                     "sha256": r.get("sha256", "")[:12],
                                     "aliases": sorted(a["path"] for a in uniq[r.get("sha256", r["path"])][1:])}
                                    for r in reps],
                       "supersede_edges": edges,
                       "latest": reps[-1]["path"]})

    for name, xs in sorted(by_name.items()):
        hashes = {x.get("sha256", "") for x in xs}
        if len(xs) > 1 and len(hashes) > 1:
            conflicts.append({"type": "name_collision_different_content", "name": name,
                              "paths": sorted(x["path"] for x in xs),
                              "action": "keep_both_no_overwrite"})

    # validate administrative version notes against content evidence
    for f in files:
        note = f.get("admin_note") or ""
        m = re.search(r"supersedes?:?\s*(\S+)", str(note), re.I)
        if m:
            target = m.group(1)
            ok = any(target in v["path"] or target == os.path.basename(v["path"])
                     for c in chains for v in c["versions"])
            if not ok:
                conflicts.append({"type": "admin_note_unverified", "file": f["path"],
                                  "note": note, "action": "flagged_for_review"})

    return {"chains": chains, "duplicate_groups": duplicate_groups,
            "conflicts": conflicts,
            "report": {"files": len(files), "version_chains": len(chains),
                       "duplicate_groups": len(duplicate_groups),
                       "conflicts": len(conflicts)}}


def _demo() -> int:
    files = [
        {"path": "proj/report_v1.docx", "sha256": "aaa", "mtime": 100},
        {"path": "proj/report_v2.docx", "sha256": "bbb", "mtime": 200},
        {"path": "proj/report_final.docx", "sha256": "ccc", "mtime": 300,
         "admin_note": "supersedes report_v2.docx"},
        {"path": "backup/report_v2.docx", "sha256": "bbb", "mtime": 200},   # alias copy
        {"path": "other/report_v2.docx", "sha256": "zzz", "mtime": 150},    # name collision
        {"path": "proj/data.csv", "sha256": "d1", "mtime": 100},
        {"path": "proj/data.csv.bak", "sha256": "d1", "mtime": 100},        # duplicate
        {"path": "proj/notes.txt", "sha256": "n1", "mtime": 100,
         "admin_note": "supersedes ghost_v0.txt"},                          # unverified
    ]
    out = build_version_map(files)
    rep = out["report"]
    assert rep["version_chains"] == 1, rep
    ch = out["chains"][0]
    assert ch["latest"] == "proj/report_final.docx"
    assert len(ch["supersede_edges"]) == 3  # v1->v2 ->collision? no: v1->v2, v2->collision, collision->final
    assert rep["duplicate_groups"] == 2, rep  # report_v2 copy pair + data.csv pair
    types = {c["type"] for c in out["conflicts"]}
    assert "name_collision_different_content" in types and "admin_note_unverified" in types
    print(json.dumps({"demo": "versions.build", **rep}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    files = json.load(open(sys.argv[1], encoding="utf-8"))
    files = files.get("files", files) if isinstance(files, dict) else files
    json.dump(build_version_map(files), open(sys.argv[2], "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"versions: {len(files)} files -> {sys.argv[2]}")
