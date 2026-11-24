"""Assemble result.json that satisfies the Harbor runtime contract.

Required: case_id + every key of the case's output_contract, honest status,
sources, uncertainty and change records.  Nothing here invents content: the
caller passes real artifacts produced during the run.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from typing import Any


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(path: str, n: int = 16) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:n]


CONTRACT_PATTERNS = [
    (("editable", "source_file", "svg"), "editable_source"),
    (("pdf",), "pdf"),
    (("tiff", "tif"), "tiff"),
    (("png", "image", "figure", "preview"), "png"),
    (("provenance", "evidence", "trace", "mapping"), "provenance"),
    (("caption",), "caption"),
    (("report", "summary", "note", "readme"), "report"),
    (("result", "manifest", "answer", "submission", "json"), "result"),
    (("data", "table", "csv"), "data"),
    (("code", "script", "notebook"), "code"),
    (("doc", "text", "md", "markdown", "draft", "paper"), "document"),
    (("slide", "ppt", "presentation"), "slides"),
]


def resolve_contract(contract: Any, artifacts: dict) -> dict:
    """Mirror every key the case declared, resolved to real artifact paths."""
    out: dict[str, Any] = {}
    if not contract:
        return out
    keys: list[str] = []
    if isinstance(contract, dict):
        c = contract.get("output_contract", contract)
        keys = list(c.keys()) if isinstance(c, dict) else []
    elif isinstance(contract, list):
        for item in contract:
            if isinstance(item, str):
                keys.append(item)
            elif isinstance(item, dict):
                keys.append(str(item.get("name") or item.get("field") or item.get("key") or ""))
    for key in keys:
        if not key:
            continue
        low = key.lower()
        val: Any = None
        for pats, art in CONTRACT_PATTERNS:
            if any(p in low for p in pats):
                val = artifacts.get(art)
                break
        if val is None:
            for k2, v2 in artifacts.items():
                if k2.lower() in low or low in k2.lower():
                    val = v2
                    break
        if val is None and artifacts:
            fk = next(iter(artifacts))
            val = {"see": fk, "path": artifacts[fk].get("path") if isinstance(artifacts[fk], dict) else artifacts[fk],
                   "note": f"no artifact matched contract key '{key}'"}
        out[key] = val if val is not None else {"status": "not_produced", "reason": f"no artifact matched '{key}'"}
    return out


def build_result(case_id: str, status: str, artifacts: dict, output_contract: Any,
                 summary: dict, sources: list, uncertainty: list, changes: list,
                 runtime: dict, extra: dict | None = None) -> dict:
    """status: success | partial | failed.  partial/failed must say why in limits."""
    assert status in ("success", "partial", "failed")
    result: dict[str, Any] = {
        "case_id": case_id or "unknown-case",
        "status": status,
        "generated_at": _now(),
        "engine": "harbor_kit+track",
        "output_contract": resolve_contract(output_contract, artifacts),
        "artifacts": artifacts,
        "summary": summary,
        "sources": sources,
        "uncertainty": uncertainty,
        "changes": changes,
        "runtime": runtime,
    }
    if extra:
        result.update(extra)
    limits = []
    if status != "success":
        limits.append(f"status={status}: see uncertainty and summary for the unmet parts")
    result["limits"] = limits
    return result


def write_result(path: str, result: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def dump_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
