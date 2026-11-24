---
name: file-evidence-search
description: "Search across local research files and return ranked passages with file+section evidence links and a recomputable score formula. Use when: a case asks to search across local research files and return ranked passages with file+section evidence links. NOT for: database retrieval, full-text translation, or file content summarization without locators."
---

# 科研文件智能检索：找到文献，也保留筛选依据

面向"跨文件检索，命中回链到文件与章节"任务。本技能把检索过程变成可复跑的确定性簿记：Agent 负责语义判断（相关性、翻译、纳排理由），引擎负责匹配、去重、计数、差异、停止判据与审计轨迹——每一步落盘为 JSON，第三方可按记录复算。

## 何时使用
* 用例给出一组科研文件（PDF/文本/表格）与查询，要求跨文件检索并给出证据定位。
* 聚焦：跨文件语义检索、章节定位、过滤条件、证据回链。

**不适用**：数据库检索、全文翻译、无定位的文件摘要。

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

**第 1 步 抽取。** `run.py extract` 把全部材料抽成带 [p.N]/表格定位的文本块。

**第 2 步 建索引。** `python -m lskit.filesearch index materials_full.json $WORK/index.json`：按文件×段落建索引，评分公式随索引输出。

**第 3 步 检索。** `filesearch search index.json "<query>" $WORK/hits.json [top_k]`：每条命中含 file、locator、score、matched_terms、snippet；支持过滤。

**第 4 步 证据回链。** 报告引用写 `file:locator` 并可打开原文核对；命中不足时明说覆盖缺口。

**第 5 步 版本与组织。** 同名/多版本文件记录版本关系；过滤条件写明。

## 本题判据对齐（题面原文的"三件事"）
1. **命中可回链** → 每条 file+locator+snippet，分数公式可手工复算。
2. **过滤条件生效且写明** → 查询与过滤参数落盘。
3. **缺口明说** → 未覆盖文件/章节列出。

## 交付物
* `index.json`、`hits.json`、`answer.md`（带 file:locator 回链）、`coverage_note.md`。

## 证据与审计规则
* 每条记录的判定必须带来由与依据片段；引擎拒绝无理由码的排除/收录（screen validate 会报问题清单）。
* 分子分母只用冻结的参考集/快照，绝不用结果集反推（coverage 的 denominator_note 强制声明）。
* 增量、合并、命中判定都输出所用规则与分数，可手工复算（identity 的 merge 日志、increment 的 basis 字段、graph 的 path[].edge_source）。
* 材料没有的内容不补：无法判断写入 uncertainty，status 降级为 partial 并在 limits 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 扫描 PDF 无文字层 | extract 记录 error；列入未覆盖清单 |
| 查询无命中 | 报告零命中与已尝试的同义改写 |
| 文件损坏/乱码 | 列入问题清单，不静默跳过 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：10 个引擎模块 demo + 一次端到端（合成 case → probe → extract → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Search/challenge-139745c7/v2
