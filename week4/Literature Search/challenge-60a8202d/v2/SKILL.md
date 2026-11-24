---
name: citation-graph-tracer
description: "Expand seed papers along citation-graph snapshot edges with full per-edge provenance and clean deduplicated output. Use when: a case asks to expand a seed set along citation edges from provided snapshots with per-edge provenance. NOT for: plain keyword search, full-text reading, citation-content understanding, or unauthorized scraping."
---

# 引文追踪与关联文献发现：找到文献，也保留筛选依据

面向"沿引用边扩展，每条边都有数据源依据"任务。本技能把检索过程变成可复跑的确定性簿记：Agent 负责语义判断（相关性、翻译、纳排理由），引擎负责匹配、去重、计数、差异、停止判据与审计轨迹——每一步落盘为 JSON，第三方可按记录复算。

## 何时使用
* 用例给出种子文献与引用关系快照，要求前向/后向追踪并交付关联文献清单。
* 判定标准：扩展文献说清来路、每条引用边可回指数据源、去重后清单干净。

**不适用**：普通关键词检索、全文阅读、引文内容理解、未授权抓取。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：文献快照、参考集、查询日志、引文图、PDF/表格等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 本题处理步骤（见下），中间产物全部写入 $WORK ——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/<主交付物> --artifact data=$WORK/<数据文件>
```

**第 1 步 图快照落盘。** 整理 `graph.json`：`{nodes:[{id,title,authors,year,doi,source_db}], edges:[{from,to,kind,source}]}`；edge.source 必须指到具体快照文件，禁止凭记忆补边。

**第 2 步 扩展。** `python -m lskit.graph graph.json seeds.json $WORK/expanded.json [both|forward|backward] [depth]`：每条扩展记录带完整 path。

**第 3 步 去重与身份合并。** 种子+扩展一起过 identity.dedupe；同一文献多路径到达时全部路径保留。

**第 4 步 路径解释。** 报告逐条给出：经哪条边、来自哪个快照、与种子相距几度；无法用图解释的记录不得入清单。

## 本题判据对齐（题面原文的"三件事"）
1. **扩展文献说清来路** → 每条记录的 path[].edge_source 链。
2. **每条引用边有数据源依据** → edges 全部带 source；无 source 的边列出并剔除。
3. **去重后清单干净** → dedupe 审计 + 合并后计数。

## 交付物
* `graph.json`、`expanded.json`（含 path）、`merged.json`、`paths.md`、图快照清单。

## 证据与审计规则
* 每条记录的判定必须带来由与依据片段；引擎拒绝无理由码的排除/收录（screen validate 会报问题清单）。
* 分子分母只用冻结的参考集/快照，绝不用结果集反推（coverage 的 denominator_note 强制声明）。
* 增量、合并、命中判定都输出所用规则与分数，可手工复算（identity 的 merge 日志、increment 的 basis 字段、graph 的 path[].edge_source）。
* 材料没有的内容不补：无法判断写入 uncertainty，status 降级为 partial 并在 limits 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 边存在但目标节点缺元数据 | 保留边与 id，节点字段标 missing，不编造 |
| 同一文献多路径到达 | 全部路径保留并说明 |
| 快照间边冲突 | 两条都保留并标 conflict，交 Agent 核对 |
| 深度扩展收益骤降 | 用 iterloop 停止判据记录停止理由 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：10 个引擎模块 demo + 一次端到端（合成 case → probe → extract → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Search/challenge-60a8202d/v2
