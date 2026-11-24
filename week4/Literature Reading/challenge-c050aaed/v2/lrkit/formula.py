"""Formula parsing & numeric verification: 认得准、讲得清、推得顺、算得回。

职责：
  - check_latex: LaTeX 结构体检（括号/环境配对、上下标完整性、OCR 常见错位信号）
  - symbols: 抽取符号候选（单字母+上下标、希腊字母），供变量表对齐
  - validate_variable_table: 每个符号必须有定义条目；定义来源区分
    paper（须带逐字证据 loc+quote）/ context / common_sense（须显式标注）
  - numeric_check: 安全求值（AST 白名单，无 __import__/无内建函数），
    逐条记录中间值，期望值不符时报比值（便于发现数量级/单位错误）
"""
from __future__ import annotations

import ast
import json
import math
import re
import sys

from . import locate

GREEK = ("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi "
         "pi rho sigma tau phi chi psi omega Gamma Delta Theta Lambda Xi Pi Sigma "
         "Phi Psi Omega").split()

_SAFE_FUNCS = {k: getattr(math, k) for k in
               ("sqrt", "exp", "log", "log10", "sin", "cos", "tan", "fabs", "pow")}
_SAFE_FUNCS.update({"abs": abs, "min": min, "max": max, "pi": math.pi, "e": math.e})


def check_latex(expr: str) -> dict:
    problems = []
    if expr.count("{") != expr.count("}"):
        problems.append(f"braces unbalanced: {expr.count('{')} '{{' vs {expr.count('}')} '}}'")
    if expr.count("(") != expr.count(")"):
        problems.append("parentheses unbalanced")
    for env in re.findall(r"\\begin\{(\w+)\}", expr):
        if f"\\end{{{env}}}" not in expr:
            problems.append(f"environment '{env}' not closed")
    if re.search(r"[_^]\s|[_^]$", expr):
        problems.append("dangling sub/superscript marker (上下标悬空)")
    if re.search(r"\\frac\s*[^{\s]", expr):
        problems.append("\\frac without braced numerator")
    return {"expr": expr[:200], "problems": problems, "ok": not problems,
            "rule": "结构错误必须先修复再进变量表与代入核验"}


def symbols(expr: str) -> list[str]:
    out = set(re.findall(r"\\(?:%s)" % "|".join(GREEK), expr))
    cleaned = re.sub(r"\\[A-Za-z]+", " ", expr)  # 去掉命令名，避免 frac→f,r,a,c
    for m in re.finditer(r"([A-Za-z])(?:_\{?([A-Za-z0-9]+)\}?)?", cleaned):
        name = m.group(1)
        if m.group(2):
            name += "_" + m.group(2)
        out.add(name)
    return sorted(out)


def validate_variable_table(table: list[dict], formula_symbols: list[str],
                            blocks: list[dict]) -> dict:
    problems, entries = [], []
    by_name = {t.get("symbol"): t for t in table}
    for s in formula_symbols:
        t = by_name.get(s)
        if t is None:
            problems.append(f"symbol '{s}' has no variable-table entry")
            continue
        src = t.get("source") or {}
        kind = src.get("kind", "")
        if kind not in ("paper", "context", "common_sense"):
            problems.append(f"symbol '{s}': source.kind must be paper|context|common_sense")
        if kind == "paper":
            r = locate.verify_quote(blocks, str(src.get("loc", "")), src.get("quote", ""))
            if not r["verified"]:
                problems.append(f"symbol '{s}': paper definition unverified ({r['reason']})")
        if kind == "common_sense" and not t.get("flagged_assumption"):
            problems.append(f"symbol '{s}': common-sense definition must set "
                            f"flagged_assumption:true (常识补充不得按原文定义写)")
        entries.append({"symbol": s, "kind": kind, "unit": t.get("unit", ""),
                        "range": t.get("range", "")})
    return {"entries": entries, "problems": problems, "ok": not problems,
            "rule": "每个符号有可指回原文的定义，或显式标为上下文推断/常识补充"}


class _Eval(ast.NodeVisitor):
    ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name,
               ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
               ast.USub, ast.UAdd, ast.Call)

    def __init__(self, values):
        self.values = values

    def visit(self, node):  # noqa: D102
        if not isinstance(node, self.ALLOWED):
            raise ValueError(f"disallowed node {type(node).__name__}")
        return super().visit(node)

    def eval(self, expr: str):
        tree = ast.parse(expr, mode="eval")
        self.visit(tree)
        return _do(tree.body, self.values)


def _do(node, values):
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError("only numeric constants allowed")
        return node.value
    if isinstance(node, ast.Name):
        if node.id in values:
            return values[node.id]
        if node.id in _SAFE_FUNCS and isinstance(_SAFE_FUNCS[node.id], (int, float)):
            return _SAFE_FUNCS[node.id]
        raise ValueError(f"unknown name '{node.id}'")
    if isinstance(node, ast.UnaryOp):
        v = _do(node.operand, values)
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.BinOp):
        a, b = _do(node.left, values), _do(node.right, values)
        op = node.op
        if isinstance(op, ast.Add):
            return a + b
        if isinstance(op, ast.Sub):
            return a - b
        if isinstance(op, ast.Mult):
            return a * b
        if isinstance(op, ast.Div):
            return a / b
        if isinstance(op, ast.Pow):
            return a ** b
        if isinstance(op, ast.Mod):
            return a % b
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _SAFE_FUNCS:
            raise ValueError("only whitelisted math functions allowed")
        fn = _SAFE_FUNCS[node.func.id]
        if not callable(fn):
            raise ValueError("not callable")
        return fn(*[_do(a, values) for a in node.args])
    raise ValueError(f"unsupported node {type(node).__name__}")


def numeric_check(steps: list[dict], tolerance: float = 1e-6) -> dict:
    """steps: [{step_id, expr, values: {var: number}, expect?, unit?, note?}]
    逐条求值并记录中间值；expect 不符时报 computed/expected 比值。"""
    results, problems = [], []
    for st in steps:
        sid = st.get("step_id", "?")
        try:
            val = _Eval(st.get("values") or {}).eval(st["expr"])
        except Exception as exc:  # noqa: BLE001
            problems.append({"step_id": sid, "error": str(exc)})
            results.append({"step_id": sid, "computed": None, "error": str(exc)})
            continue
        rec = {"step_id": sid, "expr": st["expr"], "values": st.get("values"),
               "computed": val, "unit": st.get("unit", "")}
        if st.get("expect") is not None:
            exp = float(st["expect"])
            ok = abs(val - exp) <= tolerance * max(1.0, abs(exp))
            rec["expect"] = exp
            rec["match"] = ok
            if not ok:
                rec["ratio"] = round(val / exp, 6) if exp else None
                rec["hint"] = ("比值接近 10 的幂 → 疑数量级/单位错误" if exp and
                               abs(math.log10(abs(val / exp)) - round(math.log10(abs(val / exp)))) < 0.01
                               else "数值不符，回查符号定义与单位")
        results.append(rec)
    bad = [r for r in results if r.get("match") is False]
    return {"results": results, "errors": problems, "mismatches": bad,
            "ok": not problems and not bad,
            "rule": "每步代入留中间值；不符时给 computed/expected 比值与排查提示"}


def _demo() -> int:
    blocks = [{"loc": "p.4", "text": "where m is the sample mass in kg and v is the "
              "impact velocity in m/s."}]
    latex = r"E_k = \frac{1}{2} m v^{2}"
    cl = check_latex(latex)
    assert cl["ok"], cl
    bad = check_latex(r"E = \frac{1}{2 m v^2")
    assert not bad["ok"]
    syms = symbols(latex)
    assert set(syms) == {"E_k", "m", "v"}, syms
    table = [{"symbol": "E_k", "meaning": "kinetic energy", "unit": "J",
              "source": {"kind": "common_sense"}, "flagged_assumption": True},
             {"symbol": "m", "meaning": "sample mass", "unit": "kg",
              "source": {"kind": "paper", "loc": "p.4",
                         "quote": "m is the sample mass in kg"}},
             {"symbol": "v", "meaning": "impact velocity", "unit": "m/s",
              "source": {"kind": "paper", "loc": "p.4",
                         "quote": "v is the impact velocity in m/s"}}]
    vt = validate_variable_table(table, syms, blocks)
    assert vt["ok"], vt
    nc = numeric_check([{"step_id": "s1", "expr": "0.5 * m * v**2",
                         "values": {"m": 2.0, "v": 3.0}, "expect": 9.0, "unit": "J"},
                        {"step_id": "s2", "expr": "0.5 * m * v**2",
                         "values": {"m": 2000.0, "v": 3.0}, "expect": 9.0}])
    assert not nc["ok"] and nc["mismatches"][0]["ratio"] == 1000.0  # 数量级错误被抓
    vt2 = validate_variable_table(table[:1], syms, blocks)
    assert not vt2["ok"]  # m、v 缺定义被抓
    print(json.dumps({"demo": "formula", "latex_ok": cl["ok"], "symbols": syms,
                      "vtable_ok": vt["ok"],
                      "magnitude_error_caught": nc["mismatches"][0]["ratio"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    cmd = sys.argv[1]
    if cmd == "check":
        rep = check_latex(open(sys.argv[2], encoding="utf-8").read())
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        sys.exit(0 if rep["ok"] else 1)
    elif cmd == "vtable":
        table = json.load(open(sys.argv[2], encoding="utf-8"))
        latex = open(sys.argv[3], encoding="utf-8").read()
        blocks = json.load(open(sys.argv[4], encoding="utf-8"))
        rep = validate_variable_table(table.get("symbols", table), symbols(latex),
                                      blocks.get("blocks", blocks))
        out = sys.argv[5] if len(sys.argv) > 5 else None
    elif cmd == "numeric":
        steps = json.load(open(sys.argv[2], encoding="utf-8"))
        rep = numeric_check(steps.get("steps", steps))
        out = sys.argv[3] if len(sys.argv) > 3 else None
    else:
        print("usage: formula.py [check|vtable|numeric] ...")
        sys.exit(2)
    if out:
        json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"-> {out}")
    print(f"ok={rep.get('ok', True)}")
    sys.exit(0 if rep.get("ok", True) else 1)
