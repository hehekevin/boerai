"""File-library inventory, content-hash dedupe, landing plan, archive manifest.

inventory(root) walks a real directory and records {rel, bytes, sha256, mtime,
kind}; unreadable / oversized entries are recorded as skips with reasons —
never silently dropped while the report says "全部完成".
plan_landing(manifest, rules) maps each file to a destination path built from
rule fields (project/year/kind), resolving destination collisions by renaming
with a content-hash suffix — never overwriting a different file with the same
name.  archive_manifest produces the交接清单: per-file hash, source,
destination and totals so a third party can re-run and verify one-to-one
correspondence.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

KIND_BY_EXT = {".pdf": "pdf", ".csv": "table", ".tsv": "table", ".xlsx": "spreadsheet",
               ".docx": "document", ".doc": "document", ".md": "text", ".txt": "text",
               ".json": "json", ".bib": "biblio", ".ris": "biblio", ".png": "image",
               ".jpg": "image", ".zip": "archive", ".fods": "spreadsheet", ".ods": "spreadsheet"}


def sha256_file(path: str, limit: int = 60_000_000) -> str:
    if os.path.getsize(path) > limit:
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory(root: str, hash_limit: int = 60_000_000) -> dict:
    files, skips = [], []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {"__pycache__", ".git"}]
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root)
            try:
                size = os.path.getsize(p)
                entry = {"path": p, "rel": rel, "bytes": size,
                         "mtime": int(os.path.getmtime(p)),
                         "kind": KIND_BY_EXT.get(os.path.splitext(fn)[1].lower(), "other"),
                         "sha256": sha256_file(p, hash_limit)}
                if not entry["sha256"] and size > hash_limit:
                    skips.append({"rel": rel, "reason": f"over_hash_limit({size}B)",
                                  "action": "listed_without_hash"})
                files.append(entry)
            except OSError as exc:
                skips.append({"rel": rel, "reason": f"unreadable: {exc}", "action": "skipped"})
    by_hash = {}
    for f in files:
        if f["sha256"]:
            by_hash.setdefault(f["sha256"], []).append(f["rel"])
    dupes = [{"sha256": h, "copies": sorted(v)} for h, v in sorted(by_hash.items()) if len(v) > 1]
    return {"root": os.path.abspath(root), "files": files, "skips": skips,
            "duplicates": dupes,
            "report": {"n_files": len(files), "n_skips": len(skips),
                       "n_duplicate_groups": len(dupes),
                       "total_bytes": sum(f["bytes"] for f in files)}}


def plan_landing(manifest: dict, rules: dict) -> dict:
    """rules: {"template": "{project}/{year}/{kind}", "defaults": {"project": "misc", ...},
               "fields": {rel: {"project": ..., "year": ...}}}  — fields may come from
               the case workorder or the Agent's reading; the plan is deterministic
               given the same fields, and collisions are resolved, never overwritten."""
    tmpl = rules.get("template", "{project}/{kind}")
    defaults = rules.get("defaults", {})
    ffields = rules.get("fields", {})
    plan, collisions = [], []
    used = {}
    for f in manifest.get("files", []):
        rel = f["rel"]
        ctx = dict(defaults)
        ctx.update(ffields.get(rel, {}))
        ctx.setdefault("project", "misc")
        ctx.setdefault("year", "undated")
        ctx.setdefault("kind", f.get("kind", "other"))
        dest = tmpl.format(**{k: str(v).replace("/", "_") for k, v in ctx.items()})
        dest = os.path.join(dest, os.path.basename(rel))
        key = dest.lower()
        if key in used and used[key]["sha256"] != f.get("sha256"):
            suffix = (f.get("sha256") or "nohash")[:8]
            base, ext = os.path.splitext(dest)
            dest = f"{base}__{suffix}{ext}"
            collisions.append({"original": key, "renamed_to": dest,
                               "reason": "dest_name_taken_by_different_content",
                               "action": "rename_with_hash_suffix_no_overwrite"})
        used[dest.lower()] = f
        plan.append({"src": rel, "dest": dest, "sha256": f.get("sha256", ""),
                     "bytes": f.get("bytes", 0), "fields": ctx})
    return {"plan": plan, "collisions": collisions,
            "report": {"planned": len(plan), "collisions_resolved": len(collisions),
                       "template": tmpl}}


def archive_manifest(manifest: dict, landing: dict = None) -> dict:
    files = manifest.get("files", [])
    by_rel = {p["src"]: p for p in (landing or {}).get("plan", [])}
    entries = []
    for f in sorted(files, key=lambda x: x["rel"]):
        entries.append({"source": f["rel"], "sha256": f.get("sha256", ""),
                        "bytes": f["bytes"], "kind": f["kind"],
                        "destination": by_rel.get(f["rel"], {}).get("dest", "")})
    return {"entries": entries,
            "totals": {"files": len(entries), "bytes": sum(e["bytes"] for e in entries),
                       "hashed": sum(1 for e in entries if e["sha256"])},
            "skips": manifest.get("skips", []),
            "note": "one entry per input file; third party re-hashes sources to verify"}


def _demo() -> int:
    import tempfile
    root = tempfile.mkdtemp(prefix="filelib-demo-")
    os.makedirs(os.path.join(root, "raw"))
    open(os.path.join(root, "raw", "a.txt"), "w").write("alpha")
    open(os.path.join(root, "raw", "a_copy.txt"), "w").write("alpha")  # duplicate content
    open(os.path.join(root, "b.txt"), "w").write("beta")
    open(os.path.join(root, "sub_b.txt"), "w").write("gamma")
    inv = inventory(root)
    assert inv["report"]["n_files"] == 4 and inv["report"]["n_duplicate_groups"] == 1
    land = plan_landing(inv, {"template": "{project}/{kind}",
                              "fields": {"raw/a.txt": {"project": "px"}},
                              "defaults": {"project": "misc"}})
    assert land["report"]["planned"] == 4
    dests = [p["dest"] for p in land["plan"]]
    assert len(set(d.lower() for d in dests)) == 4  # no overwrite
    arc = archive_manifest(inv, land)
    assert arc["totals"]["files"] == 4 and arc["totals"]["hashed"] == 4
    print(json.dumps({"demo": "filelib.inventory+landing+archive",
                      **inv["report"], "planned": land["report"]["planned"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    if sys.argv[1] == "inventory":
        json.dump(inventory(sys.argv[2]), open(sys.argv[3], "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"inventory: {sys.argv[2]} -> {sys.argv[3]}")
    elif sys.argv[1] == "plan":
        man = json.load(open(sys.argv[2], encoding="utf-8"))
        rules = json.load(open(sys.argv[3], encoding="utf-8"))
        json.dump(plan_landing(man, rules), open(sys.argv[4], "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"landing plan -> {sys.argv[4]}")
    else:
        print("usage: filelib.py inventory <root> <out.json> | plan <manifest> <rules> <out.json>")
        sys.exit(2)
