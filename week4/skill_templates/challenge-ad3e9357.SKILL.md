---
name: patent-search-audit
description: "Patent and technical-literature search from authorized sources: number normalisation, family grouping, legal-status annotation and risk flags. Use when: a case asks to search patents and technical literature from authorized sources with family grouping and legal-status annotation. NOT for: bypassing register restrictions or inventing legal status."
---

# 专利与技术文献检索：找到文献，也保留筛选依据

面向"授权来源、同族归并、法律状态核验"任务。本技能把检索过程变成可复跑的确定性簿记：Agent 负责语义判断（相关性、翻译、纳排理由），引擎负责匹配、去重、计数、差异、停止判据与审计轨迹——每一步落盘为 JSON，第三方可按记录复算。

## 何时使用
* 用例给出授权来源的专利/技术文献快照，要求检索、同族归并与法律状态标注。
* 判定标准：结果只来自授权来源并标注库名/版本/查询日期；专利号、同族、法律状态对得上官方登记快照；过程可复跑。

**不适用**：绕过登记限制、编造法律状态。

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

**第 1 步 授权核验。** `python -m lskit.patents authz records.json $WORK/authz.json`：来源不在授权清单的一律剔除或显式说明理由。

**第 2 步 专利号归一与同族。** `patents families records.json $WORK/families.json`：号型解析、同族归并、成员国列表、法律状态冲突标记。

**第 3 步 法律状态标注。** 只标注快照中给出的状态与查询日期；冲突标 status_conflict 并写明须人工核对官方登记。

**第 4 步 风险分级。** `patents risk records.json $WORK/risk.json`：缺法律状态/缺查询日期/缺摘要逐条列出。

## 本题判据对齐（题面原文的"三件事"）
1. **只来自授权来源** → authz.json 零未授权（或逐条书面理由）。
2. **专利号/同族/法律状态对得上登记快照** → families.json 归一化号型与冲突标记。
3. **过程可复跑** → 全部输入快照 sha256 + 命令序列记录。

## 交付物
* `authz.json`、`families.json`、`risk.json`、`records.json`（含库名/版本/查询日期）、`report.md`。

## 证据与审计规则
* 每条记录的判定必须带来由与依据片段；引擎拒绝无理由码的排除/收录（screen validate 会报问题清单）。
* 分子分母只用冻结的参考集/快照，绝不用结果集反推（coverage 的 denominator_note 强制声明）。
* 增量、合并、命中判定都输出所用规则与分数，可手工复算（identity 的 merge 日志、increment 的 basis 字段、graph 的 path[].edge_source）。
* 材料没有的内容不补：无法判断写入 uncertainty，status 降级为 partial 并在 limits 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 专利号无法解析 | problems 列出，不进同族，不猜测归并 |
| 同族法律状态冲突 | status_conflict=true，写明需核对官方登记 |
| 快照无查询日期 | risk 标记 no_query_date_recorded |
| 未授权来源混入 | 剔除并报告剔除数量与来源 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：10 个引擎模块 demo + 一次端到端（合成 case → probe → extract → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Search/challenge-ad3e9357/v2
