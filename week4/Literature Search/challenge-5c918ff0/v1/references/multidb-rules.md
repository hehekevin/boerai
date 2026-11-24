# 多库联合检索规则（multidb-rules.md）

## 1. 查询方言适配
| 库 | 语法特征 |
|-|-|
| PubMed | MeSH 词、[tiab] 字段标签、AND/OR/MeSH Terms |
| Web of Science | TS=(...)、PY=、SO= |
| Scopus | TITLE-ABS-KEY()、AND/OR/AND NOT |
每库查询式单独记录（不允许同一查询式无转换直接复用）。

## 2. 字段映射与缺失语义
missing=原始记录无该字段；unknown=存在但无法解析。合并时 missing 允许被其他库补齐；unknown 不覆盖已解析值。

## 3. 合并优先级
doi > title > year > journal > type > authors > abstract。冲突裁决逐字段记录（规则+来源+备选值）。已知限制：仅大小写差异可能被计为冲突（NFKC未含casefold），冲突率>30%时人工仲裁。

## 4. 降级披露
失败库不静默；结果集标注 coverage_gap_sources；overall 只在全部库 ok 时为 complete。

## 5. 异常处置
见 SKILL.md 异常表。