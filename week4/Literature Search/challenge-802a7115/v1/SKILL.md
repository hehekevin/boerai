---
name: crosslang-search-forge
description: 跨语言文献检索。双语术语扩展矩阵（同义/缩写/音译/本地名）提高非英语召回同时控制发散，语言与版本识别避免错配，跨语言匹配留证据，高风险命中回译/人工抽检队列识别"词面对应语义不同"的假阳性。触发词：跨语言、双语检索、术语表、误译、回译。
---

# crosslang-search-forge — 跨语言文献检索

一句话：**术语矩阵控发散、语种先识别、匹配留证据、高风险必回译。**

## 核心原则（不可违反）

1. **术语矩阵控发散**：双语术语表（zh↔en，标注类型 synonym/abbr/translit/localname）先建后查；每个英文词生成形态变体（单复数/大小写）；提高非英语召回的同时，音译类命中强制降置信。
2. **语种先识别**：查询与记录先做语言与版本判定（原文/译文/双语刊）——语种标错会导致查询词与结果错配；识别规则与证据显式记录。
3. **匹配留证据**：每条命中记录命中的双语术语与类型；不命中不编造。
4. **高风险必复核**：音译/本地名命中、单术语命中 → 回译或人工抽检队列；识别"词面对应、语义不同"的假阳性并记录判定依据。
5. **受控翻译**：查询翻译明确服务与版本，保留译文与原文对照；不用无出处的机翻词。
6. **脚本先行**：术语矩阵/语种识别/跨语言匹配/回译队列恒为0模型请求。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：双语术语矩阵（0请求 + 1次模型请求补充语义）
```bash
python <SKILL_DIR>/scripts/crosslang_search.py --termmatrix <术语表.tsv> > /app/work/terms.json
```
脚本生成变体矩阵；模型按领域补充专业译名（记录补充依据）。

### 阶段 2：语种与版本识别（0请求）
```bash
python <SKILL_DIR>/scripts/crosslang_search.py --detect <记录集.json> > /app/work/lang.json
```

### 阶段 3：跨语言匹配（0请求）
```bash
python <SKILL_DIR>/scripts/crosslang_search.py --match <记录集.json> <terms.json> > /app/work/hits.json
```

### 阶段 4：误译复核队列（0请求）+ 语义裁决（约2-4次模型请求）
```bash
python <SKILL_DIR>/scripts/crosslang_search.py --backtranslate /app/work/hits.json > /app/work/review-queue.json
```
high_risk 命中：模型做回译复核或标记人工抽检；每条判定记录依据。

### 阶段 5：交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：术语矩阵、语种识别、匹配结果、复核队列、gaps/anomalies、status。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/crosslang-report.md --require "术语|term|矩阵|matrix,语种|language|识别|detect,匹配|match|命中,复核|review|回译|backtranslate" --names "terms,lang,match,review"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 无双语术语表输入 | 从查询关键词构建骨架 + 模型补充，标注待确认 |
| 语种识别不确定 | mixed 标注，不强行归类 |
| 音译假阳性 | 进复核队列，不自动纳入结果 |
| 预算不足 | terms/lang/hits JSON 先落盘 status=partial |

## 资源清单
- `scripts/crosslang_search.py` — 术语矩阵/语种识别/匹配/复核队列（确定性引擎）
- `scripts/search_audit.py` — 匹配后覆盖率复算
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/crosslang-rules.md`、`templates/result.schema.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。矩阵/识别/匹配/队列恒为0请求；模型仅语义裁决（≤5次）。过60%时间冻结。