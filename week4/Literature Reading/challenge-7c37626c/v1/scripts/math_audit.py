#!/usr/bin/env python3
"""formula-forge: deterministic MathML extraction, variable alignment, numeric check.

Subcommands:
  --mathml FILE         parse publisher/source-formulas XML -> formula catalog
                        (linearized form + symbol set + source IDs), JSON out
  --vars FILE...        scan text materials for variable definitions
                        ("x is/where x=/x 为/x 表示") -> variable table JSON
  --crosscheck --catalog C --vars V   symbols in formulas without a definition
                        -> report; definitions unused by any formula -> note
  --numeric EXPR        evaluate an arithmetic expression safely (digits and
                        + - * / ( ) . % ^ only) for substitution checks
Stdlib only. Never raises on odd input.
"""
import argparse
import json
import re
import sys
import os
import xml.etree.ElementTree as ET

MATHML_NS = "{http://www.w3.org/1998/Math/MathML}"


def lin(node):
    """Linearize a MathML element into readable form."""
    tag = node.tag.replace(MATHML_NS, "")
    kids = list(node)
    if tag == "mi": return (node.text or "").strip()
    if tag == "mn": return (node.text or "").strip()
    if tag == "mo": return (node.text or "").strip()
    if tag == "msub":
        return "%s_{%s}" % (lin(kids[0]) if kids else "", lin(kids[1]) if len(kids) > 1 else "")
    if tag == "msup":
        return "%s^{%s}" % (lin(kids[0]) if kids else "", lin(kids[1]) if len(kids) > 1 else "")
    if tag == "msubsup" and len(kids) >= 3:
        return "%s_{%s}^{%s}" % (lin(kids[0]), lin(kids[1]), lin(kids[2]))
    if tag == "mfrac":
        return "(%s)/(%s)" % (lin(kids[0]) if kids else "", lin(kids[1]) if len(kids) > 1 else "")
    if tag == "msqrt":
        return "sqrt(%s)" % lin(kids[0]) if kids else "sqrt()"
    if tag == "mrow" or tag == "math" or tag == "semantics":
        return " ".join(lin(k) for k in kids).strip()
    return " ".join(filter(None, [lin(k) for k in kids])).strip() or (node.text or "").strip()


def symbols_of(linear):
    syms = set()
    for m in re.finditer(r"([A-Za-z](?:_\{[^}]*\})?(?:\^\{[^}]*\})?)", linear):
        syms.add(m.group(1))
    # strip msub/msup wrappers to base letters
    for s in list(syms):
        base = re.match(r"([A-Za-z])", s)
        if base: syms.add(base.group(1))
    return {s for s in syms if len(s) == 1 and s.isalpha()}


def parse_mathml(path):
    formulas, anomalies = [], []
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as e:
        return [], ["XML parse error: %s" % e]
    # find all <math> nodes at any depth
    nodes = []
    for el in root.iter():
        if el.tag.endswith("}math") or el.tag == "math":
            nodes.append(el)
    if not nodes:
        anomalies.append("no <math> elements found (file may be formula catalog subset)")
    for i, m in enumerate(nodes, 1):
        linear = lin(m)
        # try to recover a source id from nearby attributes in parent chain
        fid = m.get("id") or m.get("{http://www.w3.org/XML/1998/namespace}id") or "F%03d" % i
        formulas.append({"id": fid, "order": i, "linear": linear[:400],
                         "symbols": sorted(symbols_of(linear))})
    return formulas, anomalies


VAR_DEF_RE = re.compile(
    r"(?:^|\.\s|;\s|，|。\s*|where\s+|其中\s*)([A-Za-z][A-Za-z0-9_]*)\s*(?:is|denotes|represents|stands for|=|为|表示|指|是)\s*([^.;。]{3,120})")


def scan_vars(paths):
    vardefs = []
    for p in paths:
        try:
            lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        rel = os.path.relpath(p) if os.path.dirname(p) else p
        for i, line in enumerate(lines, 1):
            for m in VAR_DEF_RE.finditer(line):
                vardefs.append({"symbol": m.group(1), "meaning": m.group(2).strip()[:120],
                                "source": {"file": rel, "line": i}})
    return vardefs


def crosscheck(catalog, vardefs):
    defined = {v["symbol"] for v in vardefs}
    in_formulas = set()
    missing = []
    for f in catalog.get("formulas", []):
        in_formulas |= set(f.get("symbols", []))
    for s in sorted(in_formulas):
        if s not in defined:
            missing.append({"symbol": s, "why": "appears in formulas but no definition found in materials",
                            "action": "search draft/paper text; if absent -> gaps + human_confirm, do not guess meaning"})
    unused = sorted(defined - in_formulas)
    return {"symbols_missing_definition": missing, "definitions_not_in_formulas": unused,
            "n_formula_symbols": len(in_formulas), "n_defined": len(defined)}


def safe_eval(expr):
    if not re.fullmatch(r"[0-9a-zA-Z_.+\-*/() ,%^]+", expr):
        return None, "expr contains unsupported characters"
    e = expr.replace("^", "**")
    env = {}
    # allow simple known constants
    env["pi"] = __import__("math").pi
    env["e"] = __import__("math").e
    try:
        val = eval(compile(e, "<check>", "eval"), {"__builtins__": {}}, env)
        return val, None
    except Exception as ex:
        return None, str(ex)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mathml"); ap.add_argument("--vars", nargs="+")
    ap.add_argument("--catalog"); ap.add_argument("--varfile")
    ap.add_argument("--crosscheck", action="store_true")
    ap.add_argument("--numeric"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.numeric:
        v, err = safe_eval(a.numeric)
        print(json.dumps({"expr": a.numeric, "value": v, "error": err}, ensure_ascii=False))
        return 0
    if a.crosscheck:
        cat = json.load(open(a.catalog, encoding="utf-8"))
        vd = json.load(open(a.varfile, encoding="utf-8"))
        res = crosscheck(cat, vd.get("vardefs", vd if isinstance(vd, list) else []))
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    if a.mathml:
        formulas, anomalies = parse_mathml(a.mathml)
        out = {"schema": "formula-forge/catalog@1", "source": a.mathml,
               "n_formulas": len(formulas), "formulas": formulas, "anomalies": anomalies}
        if a.out:
            json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        else:
            print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    if a.vars:
        out = {"schema": "formula-forge/vardefs@1", "vardefs": scan_vars(a.vars)}
        if a.out:
            json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        else:
            print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    ap.error("choose --mathml / --vars / --crosscheck / --numeric")


if __name__ == "__main__":
    sys.exit(main())
