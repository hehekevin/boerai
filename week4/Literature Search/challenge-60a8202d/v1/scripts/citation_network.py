#!/usr/bin/env python3
"""citation-tracking-forge: citation network expansion, path explanation, identity merge.

Deterministic subcommands (0 model requests):
  --trace SEEDS_JSON LINKS_JSON   forward/backward expansion with hop pruning & stop rules
  --network EXPANDED_JSON          seed-centric network: hub/bridge/hotspot roles
  --path EXPANDED_JSON A B         shortest/most-trusted citation chain seed->target with per-hop evidence
  --merge RECORDS_JSON             identity merge (doi/title/author/year inconsistency)
Stdlib only.
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict, deque


def norm_title(s):
    s = unicodedata.normalize("NFKC", s or "")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", s.lower())).strip()


def rec_key(r):
    if r.get("doi"):
        return "doi:" + r["doi"]
    return "title:" + norm_title(r.get("title", ""))


def cmd_trace(seeds_path, links_path):
    seeds = json.load(open(seeds_path, encoding="utf-8"))
    if isinstance(seeds, dict):
        seeds = seeds.get("seeds", [])
    links = json.load(open(links_path, encoding="utf-8"))
    if isinstance(links, dict):
        links = links.get("links", [])
    # links: [{from, to, direction: backward|forward, source_db, context_hint}]
    adj = defaultdict(list)
    for l in links:
        adj[l["from"]].append(l)
    expanded = {}
    queue = deque()
    for s in seeds:
        queue.append((s if isinstance(s, str) else s.get("id"), 0))
    visited = set()
    stop_at_hop = 3
    while queue:
        node, hop = queue.popleft()
        if node in visited or hop >= stop_at_hop:
            continue
        visited.add(node)
        for l in adj.get(node, []):
            nxt = l["to"]
            if nxt not in visited:
                queue.append((nxt, hop + 1))
            expanded.setdefault(nxt, []).append({"via": node, "hop": hop + 1,
                                                  "direction": l.get("direction", ""),
                                                  "source_db": l.get("source_db", ""),
                                                  "context_hint": (l.get("context_hint") or "")[:80],
                                                  "pruned": False})
    # branch pruning: nodes with >8 inbound edges flagged
    pruned = []
    for node, edges in expanded.items():
        if len(edges) > 8:
            for e in edges[8:]:
                e["pruned"] = True
            pruned.append({"node": node, "n_inbound": len(edges), "note": "入边过多（ hub 节点），超出前8条标记 pruned，需相关性剪枝"})
    print(json.dumps({"schema": "citnet/trace@1", "stop_at_hop": stop_at_hop,
                      "n_reached": len(visited), "expanded": {k: v[:6] for k, v in list(expanded.items())[:20]},
                      "pruned": pruned,
                      "stop_rules": ["hop>=3 剪枝（避免只取一层后又无限扩展）", "单节点入边>8 标记剪枝待相关性过滤"]},
                     ensure_ascii=False, indent=1))
    return 0


def cmd_network(expanded_path):
    data = json.load(open(expanded_path, encoding="utf-8"))
    if isinstance(data, dict) and "expanded" not in data:
        data = {"expanded": data}
    expanded = data.get("expanded", {})
    indeg = {k: len(v) for k, v in expanded.items()}
    hubs = sorted(indeg.items(), key=lambda x: -x[1])[:5]
    hops = defaultdict(int)
    for k, v in expanded.items():
        for e in v:
            hops[e["hop"]] += 1
    net = {"schema": "citnet/network@1", "n_nodes": len(expanded),
           "hubs": [{"node": n, "inbound": c, "role": "hub/bridge(连接多分支)" if c > 3 else "leaf"} for n, c in hubs],
           "hop_distribution": dict(sorted(hops.items())),
           "readable_structure": "奠基性节点=被引最多的早期hop；近期热点=hop最小入边多的新节点；桥接=连接两个以上分支",
           "note": "给出可读的领域结构而不是一张无法解释的连边图"}
    print(json.dumps(net, ensure_ascii=False, indent=1))
    return 0


def bfs_path(adj_map, start, target):
    if start == target:
        return [{"node": start, "note": "seed"}]
    prev = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        for l in adj_map.get(cur, []):
            nxt = l["to"]
            if nxt not in prev:
                prev[nxt] = (cur, l)
                if nxt == target:
                    path = []
                    node = target
                    while prev[node]:
                        pnode, plink = prev[node]
                        path.append({"node": node, "via": pnode, "direction": plink.get("direction", ""),
                                     "source_db": plink.get("source_db", ""),
                                     "context_hint": (plink.get("context_hint") or "")[:60]})
                        node = pnode
                    path.append({"node": start, "note": "seed"})
                    path.reverse()
                    return path
                q.append(nxt)
    return None


def cmd_path(expanded_path, target):
    data = json.load(open(expanded_path, encoding="utf-8"))
    expanded = data.get("expanded", data)
    adj_map = defaultdict(list)
    for node, edges in expanded.items():
        for e in edges:
            adj_map[e["via"]].append({"to": node, "direction": e.get("direction", ""),
                                       "source_db": e.get("source_db", ""),
                                       "context_hint": e.get("context_hint", "")})
    seed = next(iter(expanded.values()))[0]["via"] if expanded else None
    path = bfs_path(adj_map, seed, target) if seed else None
    print(json.dumps({"schema": "citnet/path@1", "seed": seed, "target": target,
                      "found": bool(path),
                      "path": path,
                      "path_note": "逐跳标注引用方向、数据源与引用语境线索；直接引用 vs 间接可达（经中转节点）"} if path else
                     {"schema": "citnet/path@1", "found": False,
                      "note": "目标不在扩展图中（未被追踪到）"}, ensure_ascii=False, indent=1))
    return 0


def cmd_merge(records_path):
    recs = json.load(open(records_path, encoding="utf-8"))
    if isinstance(recs, dict):
        recs = recs.get("records", recs.get("items", []))
    groups = defaultdict(list)
    for r in recs:
        groups[norm_title(r.get("title", ""))[:60]].append(r)
    merges = []
    for key, members in groups.items():
        if len(members) < 2:
            continue
        fields_conflict = {}
        for f in ("doi", "year", "venue", "authors"):
            vals = {str(m.get(f, "")) for m in members if m.get(f)}
            if len(vals) > 1:
                fields_conflict[f] = sorted(vals)
        merges.append({"identity_key": "title:" + key, "n_members": len(members),
                       "members": [{"doi": m.get("doi", ""), "year": m.get("year", ""), "venue": m.get("venue", "")} for m in members],
                       "version_type": "preprint_vs_journal" if any("arxiv" in str(m.get("doi", "")).lower() or "arXiv" in str(m.get("venue", "")) for m in members) else "multi_venue",
                       "conflicts": fields_conflict,
                       "merge_rule": "保留正式版为主记录；预印本关联 version_of；字段冲突保留信息全者并记录备选"})
    print(json.dumps({"schema": "citnet/merge@1", "n_input": len(recs), "n_merge_groups": len(merges),
                      "merges": merges[:20]}, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", nargs=2, metavar=("SEEDS", "LINKS"))
    ap.add_argument("--network")
    ap.add_argument("--path", nargs=2, metavar=("EXPANDED", "TARGET"))
    ap.add_argument("--merge")
    a = ap.parse_args()
    if a.trace:
        return cmd_trace(a.trace[0], a.trace[1])
    if a.network:
        return cmd_network(a.network)
    if a.path:
        return cmd_path(a.path[0], a.path[1])
    if a.merge:
        return cmd_merge(a.merge)
    ap.error("choose --trace / --network / --path / --merge")


if __name__ == "__main__":
    sys.exit(main())
