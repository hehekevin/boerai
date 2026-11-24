"""Skill self-compliance check (run before every submission).

Limits from the Harbor contract: at most 50 UTF-8 text files, 500 KB each,
2 MB total, no symlinks, valid name/description YAML frontmatter, and (week 4)
a GITHUB_URL.txt whose first line is a public GitHub link.
"""
from __future__ import annotations

import os


def check_skill(root: str) -> dict:
    files, total, big, links, not_utf8 = [], 0, [], [], []
    for base, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(base, f)
            if os.path.islink(p):
                links.append(p)
                continue
            s = os.path.getsize(p)
            total += s
            if s > 500_000:
                big.append((p, s))
            files.append(p)
            try:
                open(p, "rb").read().decode("utf-8")
            except UnicodeDecodeError:
                not_utf8.append(p)
    fm_ok, fm_err = False, ""
    skill_md = os.path.join(root, "SKILL.md")
    if os.path.exists(skill_md):
        text = open(skill_md, encoding="utf-8").read()
        parts = text.split("---")
        if len(parts) >= 3:
            try:
                import yaml
                fm = yaml.safe_load(parts[1]) or {}
                fm_ok = bool(fm.get("name")) and bool(fm.get("description"))
                if not fm_ok:
                    fm_err = "frontmatter missing name/description"
            except Exception as e:  # noqa: BLE001
                fm_err = f"frontmatter YAML error: {e}"
        else:
            fm_err = "no --- frontmatter block ---"
    else:
        fm_err = "SKILL.md missing"
    gh = ""
    gh_path = os.path.join(root, "GITHUB_URL.txt")
    if os.path.exists(gh_path):
        gh = open(gh_path, encoding="utf-8").readline().strip()
    checks = {
        "files_le_50": len(files) <= 50,
        "total_le_2mb": total <= 2_000_000,
        "no_oversize_file": not big,
        "no_symlinks": not links,
        "all_utf8": not not_utf8,
        "frontmatter": fm_ok,
        "github_url": gh.startswith("https://github.com/"),
    }
    return {"ok": all(checks.values()), "checks": checks, "n_files": len(files), "bytes": total,
            "problems": {"oversize": big, "symlinks": links, "not_utf8": not_utf8,
                         "frontmatter_error": fm_err, "github_url": gh}}


if __name__ == "__main__":
    import json
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    rep = check_skill(root)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    sys.exit(0 if rep["ok"] else 1)
