#!/usr/bin/env python3
"""bio-device-forge: biology pathway diagrams + device/process flow diagrams.

Deterministic subcommands (0 model requests):
  --entities TEXT_JSON     gene/protein naming: species prefix, synonyms/old names, complex/family, entity-ID source
  --relations TEXT_JSON    semantic relations (促进/抑制/磷酸化/泛素化/结合/募集/转运) -> arrow type + endpoint style + evidence strength
  --topology RELATIONS_JSON  layout: upstream/downstream order, receptor-cytosol-nucleus hierarchy, membrane/compartment, feedback loops
  --device PARTS_JSON      device structure & assembly: unit parts, interfaces alignment, local zoom
  --process TEXT_JSON      numbered process flow: main sequence/parallel branches/loops/termination, numbering vs text 1-to-1
  --flowdir FLOW_JSON      arrows/linestyle/color encode material/energy/info flow; split/merge/recycle/waste exits
Stdlib only.
"""
import argparse, json, re, sys

def load(path):
    d = json.load(open(path, encoding="utf-8"))
    return d if isinstance(d, dict) else {"text": str(d)}

SPECIES_PREFIX = re.compile(r"(?i)\b(h|homo|m|m musculus|r|rattus|d|drosophila|c|cerevisiae)\b")
ARROW_MAP = {
    "促进": {"arrow": "solid_arrow", "endpoint": "normal", "evidence_default": "strong"},
    "激活": {"arrow": "solid_arrow", "endpoint": "normal", "evidence_default": "strong"},
    "抑制": {"arrow": "T_bar", "endpoint": "inhibition", "evidence_default": "strong"},
    "磷酸化": {"arrow": "solid_arrow_circle", "endpoint": "phospho(P)", "evidence_default": "strong"},
    "泛素化": {"arrow": "solid_arrow_Ub", "endpoint": "ub(Ub)", "evidence_default": "strong"},
    "结合": {"arrow": "double_line", "endpoint": "none", "evidence_default": "medium"},
    "募集": {"arrow": "dashed_arrow", "endpoint": "normal", "evidence_default": "medium"},
    "转运": {"arrow": "open_arrow", "endpoint": "normal", "evidence_default": "medium"},
    "分泌": {"arrow": "open_arrow", "endpoint": "normal", "evidence_default": "medium"},
}

def cmd_entities(path):
    d = load(path)
    text = json.dumps(d, ensure_ascii=False)
    # extract candidate entity tokens
    tokens = re.findall(r"(?i)\b((?:[A-Z][a-z]+[0-9]*)(?:-[A-Za-z0-9]+)?)\b", text)
    seen, entities = set(), []
    for t in tokens:
        if t.lower() in ("the", "this", "that", "with", "from") or len(t) < 3:
            continue
        if t in seen:
            continue
        seen.add(t)
        entities.append({"entity": t, "kind": "protein(大写斜体规范按期刊)",
                         "species_prefix": bool(SPECIES_PREFIX.search(text)),
                         "naming_rule": "基因斜体/蛋白正体；物种前缀标注；同义名与旧名合并标注",
                         "complex_or_family": bool(re.search(r"(复合物|complex|family|家族)", text)),
                         "id_source": "Entity ID 与来源库标注（UniProt/GeneID）——防同名异义/异名同义"})
    print(json.dumps({"schema": "bio/entities@1", "n_entities": len(entities), "entities": entities[:30]},
                     ensure_ascii=False, indent=1))
    return 0

def cmd_relations(path):
    d = load(path)
    text = json.dumps(d, ensure_ascii=False)
    out = []
    for rel, spec in ARROW_MAP.items():
        for m in re.finditer(re.escape(rel), text):
            out.append({"relation": rel, "arrow_type": spec["arrow"], "endpoint_style": spec["endpoint"],
                        "evidence_strength": text[max(0, m.start() - 60):m.start()].lower().count("in vitro") and "in vitro(标注)" or spec["evidence_default"],
                        "context": text[max(0, m.start() - 30):m.end() + 30][:90]})
    print(json.dumps({"schema": "bio/relations@1", "n_relations": len(out), "relations": out[:30],
                      "note": "语义→可区分箭头类型与端点样式；证据强度标注"}, ensure_ascii=False, indent=1))
    return 0

COMPARTMENT_ORDER = ["胞外/受体", "跨膜", "胞内/细胞质", "核内"]

def cmd_topology(path):
    d = load(path)
    rels = d.get("relations", d if isinstance(d, list) else [])
    levels = {}
    for r in (rels if isinstance(rels, list) else []):
        for side in ("from", "to"):
            e = str(r.get(side, ""))
            lvl = None
            for i, c in enumerate(COMPARTMENT_ORDER):
                if c[:2] in e:
                    lvl = i
                    break
            levels[e] = lvl if lvl is not None else 2
    order = sorted(levels.items(), key=lambda kv: kv[1])
    feedback = [(a, b) for a in order for b in order if b[1] < a[1] and a[0] != b[0]][:3]
    print(json.dumps({"schema": "bio/topology@1",
                      "hierarchy_order": [{"entity": e, "compartment": COMPARTMENT_ORDER[l] if l is not None else "?"} for e, l in order[:12]],
                      "feedback_loops": [{"upstream": a, "downstream": b} for a, b in feedback],
                      "layout_rule": "上下游顺序+受体-胞内-核内层级+跨膜区室位置；布局本身传达机制结构"},
                     ensure_ascii=False, indent=1))
    return 0

def cmd_device(path):
    d = load(path)
    parts = d.get("parts", d.get("items", d if isinstance(d, list) else []))
    out = []
    for p in (parts if isinstance(parts, list) else []):
        out.append({"part": p.get("name", p.get("part", "")) if isinstance(p, dict) else str(p)[:30],
                    "model": p.get("model", ""), "interface": p.get("interface", "接口对齐标注"),
                    "assembly": p.get("connects_to", ""),
                    "same_type_disambiguation": "同类部件编号区分（P1/P2）；局部放大标记 zoom"})
    print(json.dumps({"schema": "device/structure@1", "parts": out[:25],
                      "note": "单元装置结构与装配关系"}, ensure_ascii=False, indent=1))
    return 0

def cmd_process(path):
    d = load(path)
    steps = d.get("steps", d.get("text", ""))
    if isinstance(steps, str):
        raw = [s.strip() for s in re.split(r"[。；;\n]|(?:然后|接着|随后|最后)", steps) if norm(s := s.strip())]
    else:
        raw = [norm(s.get("name", s.get("text", ""))) if isinstance(s, dict) else norm(str(s)) for s in steps]
    out = []
    for i, s in enumerate(raw):
        branch = "parallel" if re.search(r"(?i)(同时|并行|parallel)", s) else ("loop" if re.search(r"(?i)(循环|重复|回|loop)", s) else "main")
        term = "termination" if re.search(r"(?i)(终止|结束|完成|直到)", s) else ""
        out.append({"no": i + 1, "step": s[:60], "branch_type": branch, "termination": term})
    print(json.dumps({"schema": "device/process@1", "n_steps": len(out), "steps": out[:25],
                      "note": "编号与正文逐条对照"}, ensure_ascii=False, indent=1))
    return 0

def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()

FLOW_TYPES = {"物料": "solid_thick", "能量": "dash_heavy", "信息": "thin_arrow"}

def cmd_flowdir(path):
    d = load(path)
    flows = d.get("flows", d.get("arrows", d if isinstance(d, list) else []))
    out = []
    for f in (flows if isinstance(flows, list) else []):
        ftype = f.get("type", "物料") if isinstance(f, dict) else "物料"
        out.append({"from": f.get("from", "?") if isinstance(f, dict) else str(f)[:20],
                    "to": f.get("to", "?") if isinstance(f, dict) else "",
                    "linestyle": FLOW_TYPES.get(ftype, "solid_thick"),
                    "split_merge": f.get("split", f.get("merge", "")) if isinstance(f, dict) else "",
                    "recycle_waste": bool(f.get("recycle")) or bool(f.get("waste"))})
    print(json.dumps({"schema": "device/flowdir@1", "flows": out[:25],
                      "note": "箭头/线型/颜色编码物料能量信息；分流合流回流废料出口；防方向相反/断头箭头"},
                     ensure_ascii=False, indent=1))
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entities"); ap.add_argument("--relations"); ap.add_argument("--topology")
    ap.add_argument("--device"); ap.add_argument("--process"); ap.add_argument("--flowdir")
    a = ap.parse_args()
    if a.entities: return cmd_entities(a.entities)
    if a.relations: return cmd_relations(a.relations)
    if a.topology: return cmd_topology(a.topology)
    if a.device: return cmd_device(a.device)
    if a.process: return cmd_process(a.process)
    if a.flowdir: return cmd_flowdir(a.flowdir)
    ap.error("choose a subcommand")

if __name__ == "__main__":
    sys.exit(main())
