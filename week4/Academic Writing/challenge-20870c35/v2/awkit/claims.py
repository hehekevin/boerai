"""句级论断 → 来源引文绑定校验（source-fidelity 核心）。

数据流（全部落盘 JSON，可复算）：
  sources.json   [{"id": "S1", "text": "...", "loc": "paper.pdf p.3"}, ...]
  draft.md       待校验稿件（任意 UTF-8 文本 / Markdown）
  bindings.json  [{"sentence_id": "d0042", "source_id": "S1",
                   "quote": "来源中的原文片段"}, ...]      —— 由 Agent 填写
  computed.json  [{"value": "12.5", "formula": "(10+15)/2",
                   "inputs": {"a": "10", "b": "15"},
                   "basis_sentence_ids": ["d0007"]}, ...]  —— 推导出的数字

硬性规则（引擎强制执行，不接受自述）：
1. 每个绑定 quote 必须是所引 source 文本的（规范化空白后的）子串——防止编引文。
2. 含数字的句子必须有绑定；草稿中每个数字要么字面出现在该句绑定的
   quote 合集里，要么在 computed.json 登记且公式可用输入数字安全求值得到。
3. strict 模式下，除 Agent 显式声明为 non_factual（过渡句、标题、设问等）
   的句子外，每个句子都必须有绑定。
4. 材料不足不许硬写：没有来源可绑定的论断必须删去或改写为
   “材料不足，待补来源”式标注句（引擎提供 insufficient() 生成该标注）。

CLI:  python -m awkit.claims validate DRAFT SOURCES BINDINGS [COMPUTED] OUT [--strict] [--nonfactual IDS]
"""
from __future__ import annotations

import ast
import json
import re
import sys

_WS = re.compile(r"\s+")
_NUM = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?(?:%|％)?)(?![\w%])")
_SENT_SPLIT = re.compile(r"(?<=[。！？!?；;])|(?<=[.])\s+|(?<=\n)")


def norm(s: str) -> str:
    return _WS.sub(" ", s).strip()


def split_sentences(text: str) -> list[dict]:
    """稳定句切分：返回 [{id, text}]，id 形如 d0007，可定位。"""
    out, buf, n = [], [], 0
    for line in text.splitlines(keepends=True):
        if not line.strip():
            continue
        for part in _SENT_SPLIT.split(line):
            part = part.strip()
            if not part:
                continue
            buf.append(part)
            joined = " ".join(buf)
            if re.search(r"[。！？!?;；]$", part) or (part.endswith(".") and not re.search(r"\d\.$", part)):
                n += 1
                out.append({"id": f"d{n:04d}", "text": norm(joined)})
                buf = []
    if buf:
        n += 1
        out.append({"id": f"d{n:04d}", "text": norm(" ".join(buf))})
    return out


def numbers_in(text: str) -> list[str]:
    return [m.group(1) for m in _NUM.finditer(text)]


def _canon_num(s: str) -> str:
    return s.replace("％", "%").rstrip(".")


def number_in_text(num: str, text: str) -> bool:
    """数字字面出现（允许 1,000 分隔符与全角百分号差异）。"""
    num = _canon_num(num)
    flat = text.replace(",", "").replace("％", "%")
    return num.replace(",", "") in flat


def safe_eval(formula: str) -> float | None:
    """只允许数字与 +-*/()%. 的算术式；其余一律拒绝。"""
    if not re.fullmatch(r"[\d\s.+\-*/()%]+", formula):
        return None
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                                 ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
                                 ast.USub, ast.UAdd, ast.Load)):
            return None
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            return None
    try:
        return float(eval(compile(tree, "<formula>", "eval"), {"__builtins__": {}}))  # noqa: S307
    except Exception:
        return None


def insufficient(claim_desc: str) -> str:
    """材料不足时的合法写法（不编造事实）。"""
    return f"【材料不足】{claim_desc}：现有材料未提供可绑定来源，待补充后再写。"


def validate(draft: str, sources: list[dict], bindings: list[dict],
             computed: list[dict] | None = None, strict: bool = False,
             nonfactual: list[str] | None = None) -> dict:
    src_by_id = {s.get("id"): norm(s.get("text", "")) for s in sources}
    sents = split_sentences(draft)
    by_sid: dict[str, list[dict]] = {}
    violations: list[dict] = []
    for b in bindings:
        sid, src = b.get("sentence_id"), b.get("source_id")
        q = norm(b.get("quote", ""))
        rec = {"sentence_id": sid, "quote": q, "source_id": src}
        if sid not in {s["id"] for s in sents}:
            violations.append({"type": "binding_unknown_sentence", **rec})
            continue
        if src not in src_by_id:
            violations.append({"type": "binding_unknown_source", **rec})
            continue
        if not q or q not in src_by_id[src]:
            violations.append({"type": "quote_not_in_source", **rec,
                               "note": "引文不是来源原文子串（规范化空白后比对）"})
            continue
        by_sid.setdefault(sid, []).append(b)
    computed = computed or []
    comp_ok = []
    for c in computed:
        val, formula = str(c.get("value", "")).replace("％", "%"), c.get("formula", "")
        basis = c.get("basis_sentence_ids") or []
        basis_quotes = " ".join(norm(b.get("quote", "")) for sid in basis for b in by_sid.get(sid, []))
        bad = None
        got = safe_eval(formula)
        if got is None:
            bad = "formula_rejected_or_unevaluable"
        elif not basis:
            bad = "no_basis_sentence_ids"  # 推导数字必须声明依据句
        else:
            try:
                target = float(val.rstrip("%"))
            except ValueError:
                bad = "value_not_numeric"
            else:
                if abs(got - target) > max(1e-6, abs(target) * 1e-9):
                    bad = f"formula={got} != declared {target}"
                else:
                    # 公式里的每个数字字面量必须能在依据句的绑定引文中找到
                    unsourced = [n for n in numbers_in(formula)
                                 if not number_in_text(n, basis_quotes)
                                 and n not in ("100",)]  # 允许百分号换算常量
                    if unsourced:
                        bad = f"formula_inputs_not_in_bound_sources: {unsourced}"
        if bad:
            violations.append({"type": "computed_rejected", "value": val,
                               "formula": formula, "reason": bad})
        else:
            comp_ok.append(_canon_num(val))
    nf = set(nonfactual or [])
    checked = 0
    for s in sents:
        bound_quotes = " ".join(norm(b.get("quote", "")) for b in by_sid.get(s["id"], []))
        nums = numbers_in(s["text"])
        is_insufficient = s["text"].startswith("【材料不足】")
        if nums and not by_sid.get(s["id"]) and not is_insufficient:
            violations.append({"type": "factual_sentence_without_binding",
                               "sentence_id": s["id"], "text": s["text"][:160]})
            continue
        for num in nums:
            if number_in_text(num, bound_quotes) or _canon_num(num) in comp_ok:
                checked += 1
            elif is_insufficient:
                pass
            else:
                violations.append({"type": "number_not_in_bound_sources",
                                   "sentence_id": s["id"], "number": num,
                                   "text": s["text"][:160],
                                   "note": "数字须字面出现在绑定引文中，或登记 computed+公式"})
        if strict and not by_sid.get(s["id"]) and s["id"] not in nf and not is_insufficient:
            violations.append({"type": "strict_sentence_without_binding",
                               "sentence_id": s["id"], "text": s["text"][:160]})
    return {"ok": not violations, "sentences": len(sents),
            "bound_sentences": len(by_sid), "numbers_checked": checked,
            "computed_registered": len(comp_ok), "violations": violations}


def _demo() -> int:
    sources = [{"id": "S1", "text": "We screened 500 genes across 3 donors. "
                                    "The hit rate was 4.2% in the primary screen.",
                "loc": "paper p.4"},
               {"id": "S2", "text": "对照组纳入 120 例受试者，随访 12 个月。", "loc": "数据表 T2"}]
    draft = ("本研究筛选了 500 个基因，覆盖 3 名供体。初筛命中率为 4.2%。"
             "合计约 21 个基因命中。对照组随访 12 个月。该方法的灵敏度为 99%。")
    bindings = [
        {"sentence_id": "d0001", "source_id": "S1", "quote": "We screened 500 genes across 3 donors."},
        {"sentence_id": "d0002", "source_id": "S1", "quote": "The hit rate was 4.2% in the primary screen."},
        {"sentence_id": "d0003", "source_id": "S1", "quote": "The hit rate was 4.2% in the primary screen."},
        {"sentence_id": "d0004", "source_id": "S2", "quote": "对照组纳入 120 例受试者，随访 12 个月。"},
    ]
    computed = [{"value": "21", "formula": "500*4.2/100", "inputs": {"n": "500", "rate": "4.2%"},
                 "basis_sentence_ids": ["d0001", "d0002"]}]
    rep = validate(draft, sources, bindings, computed, strict=True,
                   nonfactual=[])
    assert not rep["ok"], "d0005 的 99% 无来源，必须被抓出"
    kinds = {v["type"] for v in rep["violations"]}
    assert "factual_sentence_without_binding" in kinds, kinds
    # 补上诚实标注后应通过（strict 下材料不足句免绑定）
    draft2 = draft.replace("该方法的灵敏度为 99%。", insufficient("灵敏度"))
    rep2 = validate(draft2, sources, bindings, computed, strict=True)
    assert rep2["ok"], rep2["violations"]
    assert rep2["numbers_checked"] >= 5
    # 编造的引文必须被拒
    bad = validate("对照组随访 12 个月。", sources,
                   [{"sentence_id": "d0001", "source_id": "S2", "quote": "随访 24 个月"}])
    assert any(v["type"] == "quote_not_in_source" for v in bad["violations"])
    # 公式造假必须被拒：0.8 不在任何绑定引文中，且无依据句
    badc = validate("命中率 5%。", sources,
                    [{"sentence_id": "d0001", "source_id": "S1", "quote": "The hit rate was 4.2%"}],
                    [{"value": "5", "formula": "4.2+0.8", "inputs": {}}])
    assert not badc["ok"]
    assert any(v["type"] == "computed_rejected" for v in badc["violations"])
    # 合法推导：21 = 500*4.2/100，输入 500 与 4.2 都在依据句引文中
    goodc = validate("合计约 21 个基因命中。", sources,
                     [{"sentence_id": "d0001", "source_id": "S1",
                       "quote": "We screened 500 genes across 3 donors. The hit rate was 4.2%"}],
                     [{"value": "21", "formula": "500*4.2/100", "inputs": {},
                       "basis_sentence_ids": ["d0001"]}])
    assert goodc["ok"], goodc["violations"]
    return 0


def main(argv: list[str]) -> int:
    if "--demo" in argv:
        return _demo()
    if len(argv) >= 1 and argv[0] == "validate":
        import argparse
        ap = argparse.ArgumentParser(prog="awkit.claims validate")
        ap.add_argument("draft"); ap.add_argument("sources"); ap.add_argument("bindings")
        ap.add_argument("computed", nargs="?", default="")
        ap.add_argument("out")
        ap.add_argument("--strict", action="store_true")
        ap.add_argument("--nonfactual", nargs="*", default=[])
        a = ap.parse_args(argv[1:])
        draft = open(a.draft, encoding="utf-8").read()
        sources = json.load(open(a.sources, encoding="utf-8"))
        bindings = json.load(open(a.bindings, encoding="utf-8"))
        computed = (json.load(open(a.computed, encoding="utf-8"))
                    if a.computed and a.computed != "-" else [])
        rep = validate(draft, sources, bindings, computed, strict=a.strict,
                       nonfactual=a.nonfactual)
        json.dump(rep, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"claims: ok={rep['ok']} sentences={rep['sentences']} "
              f"violations={len(rep['violations'])} -> {a.out}")
        return 0 if rep["ok"] else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
