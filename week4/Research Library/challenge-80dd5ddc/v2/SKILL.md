---
name: kb-grounded-qa
description: "Answer questions over a real multi-file research library with per-claim source citations that are mechanically verified (quote must occur in the located block), exact evidence coordinates (file + version + locator + sha256), and graded insufficient-evidence handling. Use when: a case asks for multi-file retrieval, cited Q&A, evidence back-links and honest 'not in the library' answers. NOT for: fluent answers with unverifiable citations, or semantic gold answers invented beyond the provided materials."
---

# 科研知识库问答：整理文件，也保留版本关系

面向"多文件检索、带来源引用的问答、证据回链、不确定性提示"任务。分工：Agent 负责阅读与作答（语义判断），引擎负责确定性簿记——`kb` 把抽取材料建成带定位（文件+段落/页码+sha256）的块索引，检索返回带分数的候选；**每条引用经 `kb validate` 机械核验：引用文本必须真实出现在所定位的块中，否则引用作废**；对库里确实没有依据的问题，按 no_evidence/weak_evidence/conflicting_evidence 分级并说明缺什么，而不是硬答。

## 何时使用
* 用例给出真实文件库（含重复副本与历史版本）与问题清单，要求带引用的回答与证据回链。
* 判定标准（题面原文的"三件事"）：答案里的每个关键论断是否都能落到具体文件、具体版本和具体段落；对于知识库里确实没有依据的问题，成果是否敢说"没有"并说明缺什么；换一个人拿着提交的记录，能不能把同样的问答重新走一遍。

**不适用**：无引用的自由作答、编造语义金标准、把不可读文件当作已读证据。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：文件库、问题清单、版本说明等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" kb index $WORK/materials_full.json $WORK/kb_index.json
python "$SKILL/run.py" kb search $WORK/kb_index.json "<问题或子问题>"
python "$SKILL/run.py" kb validate $WORK/kb_index.json $WORK/claims.json $WORK/answer_audit.json
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/qa_report.md --artifact data=$WORK/answer_audit.json
```

**第 1 步 建组织基础。** `filelib inventory` + `versions`：重复副本与版本链先理清，检索与引用才有稳定的"具体版本"坐标；不可读文件进 skips。

**第 2 步 建索引。** `kb index`：每块带 source_id、文件 rel、locator（p.n/para.n/block.n）、sha256；索引可复建。

**第 3 步 检索。** `kb search` 按 BM25 式打分返回候选块（分数、定位、原文片段）；覆盖不足时如实说明检索范围与召回缺口。

**第 4 步 作答与引用。** Agent 写 `claims.json`：`[{claim, citations:[{block_id, quote}]}]`——每个关键论断至少一条引用，quote 必须逐字来自所引块。

**第 5 步 机械核验与缺证分级。** `kb validate`：逐论断 supported / citation_invalid / no_citation；无证据问题输出 `grade:no_evidence` 与"缺什么"；`qa_report.md` 汇总逐题回答、引用坐标表、核验覆盖率与不确定性。

## 本题判据对齐（题面原文的"三件事"）
1. **"每个关键论断落到具体文件、版本和段落"** → 引用坐标 = 文件 rel + sha256 + locator + 逐字 quote，`kb validate` 逐条 verified。
2. **"敢说'没有'并说明缺什么"** → no_evidence/weak_evidence 分级 + missing 说明，unsupported 论断不计入答案结论。
3. **"别人能把同样的问答重新走一遍"** → index/search/validate 三步全部 JSON 落盘，命令固定可复跑，覆盖率（supported/claims）明示。

## 交付物
* `inventory.json`/`versions.json`（组织基础）、`kb_index.json`、`claims.json`、`answer_audit.json`、`qa_report.md`、`result.json`

## 证据与审计规则
* 引用未通过机械核验的论断必须降级或撤回，禁止"看起来有引用"就计入。
* 扫描件/无文本层/不可读文件：extract 的 blocks 为空即不可作为证据，进 skips 并在报告声明。
* 版本冲突时以题目指定版本为准并注明；引用坐标含版本（sha256）区分。
* 覆盖六个维度（文件类型、元数据字段、目录层级、重复文件、版本差异、权限与来源）的组织信息随报告附上。

## 异常处理
| 情况 | 处置 |
|---|---|
| 检索零命中 | 如实报 no_evidence + 缺什么；不硬答 |
| 引用文本与定位块不符 | citation_invalid，该论断降级，failures 留痕 |
| 证据互相矛盾 | conflicting_evidence 分级，两说并陈 + 坐标 |
| 文件不可读/扫描件无文本 | skips + 报告声明该部分库不可用 |
| 目录为空/问题超出库范围 | no_evidence + uncertainty，status=partial |
| 重复副本版本歧义 | versions 输出版本链，引用坐标绑定 sha256 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：11 个引擎模块 demo（kb demo 含"引用文本必须真实出现在定位块"的正反断言）+ 一次端到端（合成 case → probe → extract → 模块命令 → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Research%20Library/challenge-80dd5ddc/v2
