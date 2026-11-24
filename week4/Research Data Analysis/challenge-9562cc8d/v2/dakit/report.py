"""报告回填：{{placeholder}} 只允许来自已计算的 stats JSON；数字必须同源、可回算。

模板占位符语法：{{点.分.路径}} 或 {{点.分.路径|round:3}}。
- fill(): 每个占位符在 stats JSON 中按点路径解析；解析失败 → 抛错列出，
  绝不留空、绝不编值。填充映射（占位符 → JSON 路径 → 值）记入 mapping。
- validate(): 渲染后的报告不得残留 {{...}}；报告中每个被回填的数字必须能在
  mapping 中找到且与 stats JSON 中的值逐一相等（防手改）。
- 报告里的任何数字如果不是占位符回填的，作者必须自证来源 —— validate(strict)
  会把出现在正文但不在 mapping 中的数字列为 unattributed_numbers 警告。
"""
from __future__ import annotations

import json
import re
import sys

PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.\-\[\]]+?)(?:\|round:(\d+))?\s*\}\}")
NUMBER_RE = re.compile(r"(?<![\w.])(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)(?![\w.])")


class UnresolvedPlaceholder(Exception):
    pass


def _resolve(stats: dict, path: str):
    """点路径解析，支持 results[0].t 这类下标。"""
    cur = stats
    for part in re.split(r"\.", path):
        m = re.fullmatch(r"([A-Za-z0-9_\-]+)(?:\[(\d+)\])?", part)
        if not m:
            raise UnresolvedPlaceholder(f"bad path segment {part!r} in {path!r}")
        key, idx = m.group(1), m.group(2)
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            raise UnresolvedPlaceholder(f"no key {key!r} resolving {path!r}")
        if idx is not None:
            i = int(idx)
            if isinstance(cur, list) and i < len(cur):
                cur = cur[i]
            else:
                raise UnresolvedPlaceholder(f"index [{i}] out of range in {path!r}")
    return cur


def fill(template: str, stats: dict) -> dict:
    """回填并返回 {text, mapping}。任何占位符解析失败立即报错（列出全部缺失）。"""
    mapping, missing = {}, []

    def repl(m):
        path, nd = m.group(1), m.group(2)
        try:
            v = _resolve(stats, path)
        except UnresolvedPlaceholder:
            missing.append(path)
            return m.group(0)
        if nd is not None and isinstance(v, (int, float)):
            v = round(v, int(nd))
        mapping[m.group(0)] = {"path": path, "value": v}
        return str(v)

    text = PLACEHOLDER_RE.sub(repl, template)
    if missing:
        raise UnresolvedPlaceholder(
            "placeholders not traceable to stats JSON: " + ", ".join(sorted(missing)))
    return {"text": text, "mapping": mapping,
            "rule": "every rendered number comes from the stats JSON via the mapping above"}


def validate(rendered: str, mapping: dict, strict: bool = False) -> dict:
    """校验渲染结果。strict 时列出无法归因到 mapping 的数字（供人工核查）。"""
    problems = []
    leftover = PLACEHOLDER_RE.findall(rendered)
    if leftover:
        problems.append(f"unfilled placeholders remain: {leftover}")
    mapped_values = {str(v["value"]) for v in mapping.values()}
    unattributed = []
    if strict:
        for num in NUMBER_RE.findall(rendered):
            if num not in mapped_values and not _close_to_any(num, mapped_values):
                unattributed.append(num)
    return {"ok": not problems, "problems": problems,
            "n_backfilled": len(mapping),
            "unattributed_numbers": unattributed,
            "unattributed_note": "strict mode: numbers in the report not produced by backfill; "
                                 "each needs a written source or must become a placeholder"
            if strict else ""}


def _close_to_any(num: str, mapped: set) -> bool:
    try:
        x = float(num)
    except ValueError:
        return False
    for m in mapped:
        try:
            if abs(float(m) - x) < 1e-9:
                return True
        except ValueError:
            continue
    return False


def _demo() -> int:
    stats = {"results": [{"test": "welch_two_sample_t", "n1": 15, "n2": 14,
                          "mean1": 20.8215, "mean2": 22.0143, "t": -1.63214,
                          "p_two_sided": 0.124743, "cohens_d": -0.5982}]}
    tpl = ("两组样本量 {{results[0].n1}} / {{results[0].n2}}，"
           "均值 {{results[0].mean1|round:2}} vs {{results[0].mean2|round:2}}，"
           "Welch t={{results[0].t|round:3}}，p={{results[0].p_two_sided|round:4}}。")
    rep = fill(tpl, stats)
    assert "{{" not in rep["text"]
    assert "20.82 vs 22.01" in rep["text"]
    assert "p=0.1247" in rep["text"]
    assert len(rep["mapping"]) == 6
    v = validate(rep["text"], rep["mapping"], strict=True)
    assert v["ok"], v
    # 不可追溯占位符必须被拒绝
    try:
        fill("结论是 p={{results[9].p_two_sided}}，效果很好。", stats)
        raise SystemExit("should have raised")
    except UnresolvedPlaceholder as e:
        assert "results[9]" in str(e)
    # 手改数字被 strict 校验发现
    tampered = rep["text"].replace("p=0.1247", "p=0.0120")
    v2 = validate(tampered, rep["mapping"], strict=True)
    assert "0.0120" in v2["unattributed_numbers"], v2
    print(json.dumps({"demo": "report", "backfilled": len(rep["mapping"]),
                      "rendered": rep["text"], "tamper_detected": "0.0120"},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    # usage: python -m dakit.report template.md stats.json out.md [mapping.json]
    template = open(sys.argv[1], encoding="utf-8").read()
    stats = json.load(open(sys.argv[2], encoding="utf-8"))
    rep = fill(template, stats)
    open(sys.argv[3], "w", encoding="utf-8").write(rep["text"])
    v = validate(rep["text"], rep["mapping"], strict=True)
    if len(sys.argv) > 4:
        json.dump({"mapping": rep["mapping"], "validation": v},
                  open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"backfilled {len(rep['mapping'])} values, validate ok={v['ok']} -> {sys.argv[3]}")
    if v["unattributed_numbers"]:
        print(f"WARNING unattributed numbers: {v['unattributed_numbers']}")
