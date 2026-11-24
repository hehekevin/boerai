---
name: webread-translate-forge
description: 网页文献阅读与翻译。正文识别（切导航/广告/参考文献，保留章节标题/图表题注/脚注上下标），段落级翻译（非整页；长句切分/公式单位/术语/跨句指代），术语一致性（glossary落地：同义词/缩写/首次全称统一译法），可抓范围与失效条件显式说明。触发词：网页阅读、正文识别、段落翻译、术语一致性。
---

# webread-translate-forge — 网页文献阅读与翻译

一句话：**先切正文去噪声、段落级翻译不漏补、术语表保一致、抓取边界说清楚。**

## 核心原则（不可违反）

1. **可抓范围显式**：出版社页面/预印本平台/机构仓储/动态渲染/需登录页面——能抓什么、失效条件（改版/付费墙/反爬）写明；登录墙内内容不抓取不编造。
2. **正文识别**：从导航、广告、参考文献列表、相关推荐中切出正文——标签+类名+文本三重启发式；保留章节标题、图表标题、脚注和上下标结构标记。
3. **段落级翻译**：按段落而非整页翻译；长句切分、公式与单位保留、专业术语按表、跨句指代衔接；漏译与补写都不允许（verify_translation 校验）。
4. **术语一致性**：glossary 落地（同义词/缩写/首次出现全称与译名），全文译法统一——脚本校验逐段术语命中。
5. **脚本先行**：正文识别/分段/glossary/一致性校验恒为0模型请求；模型只做翻译成文与语义复核。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：正文识别（0请求）
```bash
python <SKILL_DIR>/scripts/content_extract.py --extract <页面.html> > /app/work/content.json
```

### 阶段 2：分段（0请求）
```bash
python <SKILL_DIR>/scripts/content_extract.py --segments <正文.txt> > /app/work/segments.json
python <SKILL_DIR>/scripts/segment_source.py --segment <正文.txt> --text --out /app/work/segments.json
```

### 阶段 3：术语表与翻译（0请求建表 + 2-4次请求翻译）
```bash
python <SKILL_DIR>/scripts/build_glossary.py --segments /app/work/segments.json --out /app/work/glossary.csv
```
模型按段翻译（段号对应）；新术语即时入 glossary。

### 阶段 4：一致性校验（0请求）
```bash
python <SKILL_DIR>/scripts/verify_translation.py --source <原文> --bilingual <对照表> --glossary <glossary.csv>
```
FAIL 项修正译法后重校。

### 阶段 5：交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：正文结构、分段、双语对照、glossary、校验结果、gaps/anomalies、status。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/webread-report.md --require "正文|content|识别|extract,分段|segment|段落,翻译|translate|双语|bilingual,术语|glossary|一致" --names "content,segments,translation,glossary"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 动态渲染页面 | gaps 声明静态抓取限制，输出可获取部分 |
| 付费墙/登录墙 | 不抓取不编造；抓取范围声明中列明 |
| 公式/单位 | 原样保留不翻译（LaTeX/单位符号），标记 formula_preserved |
| 术语冲突 | glossary 首次全称优先；冲突入 uncertainties |
| 预算不足 | content/segments 先落盘 status=partial |

## 资源清单
- `scripts/content_extract.py` — 正文识别/分段（确定性引擎，新增）
- `scripts/segment_source.py`、`scripts/build_glossary.py`、`scripts/verify_translation.py`（复用第3周验证资产）
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/webread-rules.md`、`references/translation-rules.md`（复用）
- `templates/bilingual-table.md`、`templates/glossary.csv`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。识别/分段/glossary/校验恒为0请求；模型翻译（≤6次）。过60%时间冻结。