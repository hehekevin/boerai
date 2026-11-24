"""Citation-graph expansion with per-edge provenance (offline snapshots).

Graph file: {"nodes": [{id, title, authors, year, doi, source_db}],
             "edges": [{"from": id, "to": id, "kind": "cites"|"cited_by",
                        "source": "snapshot file or api name"}]}
The agent only supplies graph snapshots shipped with the case; the engine
never invents edges.  Every expanded record carries its full evidence path.
"""
from __future__ import annotations

import json
import sys

from . import identity


def load_graph(path: str) -> dict:
    g = json.load(open(path, encoding="utf-8"))
    return {"nodes": {str(n["id"]): n for n in g.get("nodes", [])}, "edges": g.get("edges", [])}


def expand(graph: dict, seeds: list[str], direction: str = "both", depth: int = 1) -> dict:
    nodes, edges = graph["nodes"], graph["edges"]
    found: dict[str, dict] = {}
    frontier = [(s, []) for s in seeds]
    for _ in range(depth):
        nxt = []
        for cur, path in frontier:
            for e in edges:
                if direction in ("backward", "both") and str(e.get("from")) == cur:
                    tgt, via = str(e.get("to")), e
                elif direction in ("forward", "both") and str(e.get("to")) == cur:
                    tgt, via = str(e.get("from")), e
                else:
                    continue
                if tgt not in nodes or tgt in found or tgt in seeds:
                    continue
                found[tgt] = {"record": nodes[tgt],
                              "path": path + [{"from": cur, "to": tgt, "kind": e.get("kind"),
                                               "edge_source": e.get("source")}]}
                nxt.append((tgt, found[tgt]["path"]))
        frontier = nxt
    return {"seeds": seeds, "expanded_n": len(found), "expanded": found,
            "note": "every record traceable via path[].edge_source; no invented edges"}


def merge_expansion(seed_records: list[dict], expanded: dict) -> dict:
    allr = list(seed_records) + [v["record"] for v in expanded["expanded"].values()]
    dd = identity.dedupe(allr)
    return {"merged": dd, "paths_kept": len(expanded["expanded"])}


def _demo() -> int:
    g = {"nodes": [{"id": "A", "title": "Seed Paper", "authors": ["Smith"], "year": 2020},
                    {"id": "B", "title": "Cited Work", "authors": ["Lee"], "year": 2018},
                    {"id": "C", "title": "Citing Work", "authors": ["Wang"], "year": 2022},
                    {"id": "D", "title": "Second Generation", "authors": ["Chen"], "year": 2023}],
         "edges": [{"from": "A", "to": "B", "kind": "cites", "source": "snapshot1.json"},
                    {"from": "C", "to": "A", "kind": "cites", "source": "snapshot1.json"},
                    {"from": "D", "to": "C", "kind": "cites", "source": "snapshot2.json"}]}
    graph = {"nodes": {n["id"]: n for n in g["nodes"]}, "edges": g["edges"]}
    out = expand(graph, ["A"], direction="both", depth=2)
    assert out["expanded_n"] == 3, out["expanded_n"]
    p = out["expanded"]["D"]["path"]
    assert len(p) == 2 and p[0]["edge_source"] == "snapshot1.json"
    print(json.dumps({"demo": "graph.expand", "seeds": 1, "expanded": out["expanded_n"],
                      "path_D": [f"{e['from']}->{e['to']}" for e in p]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    graph = load_graph(sys.argv[1])
    seeds = json.load(open(sys.argv[2], encoding="utf-8"))
    direction = sys.argv[4] if len(sys.argv) > 4 else "both"
    depth = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    rep = expand(graph, seeds.get("seeds", seeds), direction, depth)
    json.dump(rep, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"expanded {rep['expanded_n']} records -> {sys.argv[3]}")
