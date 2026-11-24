---
name: crosslang-search-audit
description: "Cross-language literature retrieval via bilingual term alignment, language detection and per-hit language/version provenance. Use when: a case asks to retrieve non-English literature via bilingual term alignment and prove each hit's language and version. NOT for: full-text translation, writing polish, or unauthorized cross-border data scraping."
---

# 跨语言文献检索：找到文献，也保留筛选依据

面向"非英语文献真实找回，术语对齐可人工核对"任务。本技能把检索过程变成可复跑的确定性簿记：Agent 负责语义判断（相关性、翻译、纳排理由），引擎负责匹配、去重、计数、差异、停止判据与审计轨迹——每一步落盘为 JSON，第三方可按记录复算。

## 何时使用
* 用例要求跨语言检索：术语扩展、非英语候选匹配、结果按语种与版本交付。
* 判定标准：非英语文献真实找回、术语对齐经得起人工核对、每条命中说清语种与版本。

**不适用**：整篇翻译、写作润色、未授权跨境抓取。

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

**第 1 步 术语对齐表。** 编写 `glossary.json`：`[{concept, en, zh, synonyms}]`；对齐表随结果交付供人工核对。

**第 2 步 查询矩阵。** `python -m lskit.crosslang matrix glossary.json $WORK/queries.json`：按语种机械展开查询式。

**第 3 步 语种识别与匹配。** 候选逐条 detect_language；非英语标题译名只能来自对齐表或记录自带 title_en；`crosslang match` 给 jaccard/containment 与 match/review/no_match 判定及译名来源。

**第 4 步 命中交付。** 每条命中带 language、title_used、translation_source、verdict；review 档进复核队列。

**第 5 步 误译复核。** 高风险词条（一词多义）在报告列出所用译法与备选。

## 本题判据对齐（题面原文的"三件事"）
1. **非英语文献真实找回** → 每条非英语命中的语言标识+所用译名+匹配分数。
2. **术语对齐经得起人工核对** → glossary.json 全文交付+高风险词条说明。
3. **命中说清语种与版本** → language/version_note/translation_source 逐条齐全。

## 交付物
* `glossary.json`、`queries.json`、`matches.json`、`review_queue.json`、`report.md`（误译风险）。

## 证据与审计规则
* 每条记录的判定必须带来由与依据片段；引擎拒绝无理由码的排除/收录（screen validate 会报问题清单）。
* 分子分母只用冻结的参考集/快照，绝不用结果集反推（coverage 的 denominator_note 强制声明）。
* 增量、合并、命中判定都输出所用规则与分数，可手工复算（identity 的 merge 日志、increment 的 basis 字段、graph 的 path[].edge_source）。
* 材料没有的内容不补：无法判断写入 uncertainty，status 降级为 partial 并在 limits 说明。

## 异常处理
| 情况 | 处置 |
|---|---|
| 候选无译名且对齐表未覆盖 | verdict=no_match_pending_glossary，不机翻硬凑 |
| 一词多义术语 | 对齐表列多译法，命中注明所用译法 |
| 同标题多语种版本 | 各版本分别列出并标版本关系 |
| 语种识别置信低 | language=unknown，匹配降档 review |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：10 个引擎模块 demo + 一次端到端（合成 case → probe → extract → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Search/challenge-802a7115/v2
