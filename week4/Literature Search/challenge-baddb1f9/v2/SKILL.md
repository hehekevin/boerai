---
name: literature-search-suite
description: "Route any literature-search case to the right engine module: coverage, screening, merge, citation graph, increment, cross-language, patents. Use when: a case asks to a literature-search case of any subtype: coverage, screening, multi-db merge, citation tracing, tracking, cross-language or patents. NOT for: full-text reading, review writing, or unauthorized data access."
---

# 文献检索领域总课题：找到文献，也保留筛选依据

面向"按任务类型路由到对应检索引擎模块"任务。本技能把检索过程变成可复跑的确定性簿记：Agent 负责语义判断（相关性、翻译、纳排理由），引擎负责匹配、去重、计数、差异、停止判据与审计轨迹——每一步落盘为 JSON，第三方可按记录复算。

## 何时使用
* 本题为领域总课题。按材料类型路由：参考集+查询日志→coverage；纳排标准→screen；多库快照→identity 归并；引文图→graph；双快照→increment；术语表→crosslang；专利号→patents；开放检索→qplan+iterloop。

**不适用**：全文阅读、综述写作、未授权数据访问。

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

**路由表（按材料与任务说明选择）：**
| 材料特征 | 主模块 | 对应子课题 |
|---|---|---|
| 参考集 + 查询日志 | coverage | 覆盖率与遗漏 |
| 纳入/排除标准 | screen | 纳排筛选、排序 |
| 多库响应快照 | identity | 多库归并 |
| 引文图快照 | graph | 引文追踪 |
| 双时间快照 | increment | 增量追踪 |
| 双语术语/非英语候选 | crosslang | 跨语言检索 |
| 专利号/法律状态 | patents | 专利检索 |
| 检索问题/多轮查询 | qplan + iterloop | 问题驱动检索、迭代 Agent |

不确定时先 probe 读材料清单，再在 uncertainty 说明路由选择理由。各子课题判据见其专属段落。

## 本题判据对齐（题面原文的"三件事"）
1. **路由正确** → 材料特征与所选模块的对应写进报告。
2. **所选子课题的三件事全部满足** → 见各子课题判据。
3. **过程可复跑** → 中间产物 JSON 全套落盘。

## 交付物
* 按路由结果交付对应子课题全套产物 + `routing_note.md`。

## 证据与审计规则
* 每条记录的判定必须带来由与依据片段；引擎拒绝无理由码的排除/收录（screen validate 会报问题清单）。
* 分子分母只用冻结的参考集/快照，绝不用结果集反推（coverage 的 denominator_note 强制声明）。
* 增量、合并、命中判定都输出所用规则与分数，可手工复算（identity 的 merge 日志、increment 的 basis 字段、graph 的 path[].edge_source）。
* 材料没有的内容不补：无法判断写入 uncertainty，status 降级为 partial 并在 limits 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 材料同时命中多个子课题 | 主任务选其一，其余写 uncertainty |
| 材料不足 | status=partial，说明缺什么 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：10 个引擎模块 demo + 一次端到端（合成 case → probe → extract → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Search/challenge-baddb1f9/v2
