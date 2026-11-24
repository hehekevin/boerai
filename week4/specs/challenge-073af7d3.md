# 交付标准 · challenge-073af7d3 研究前沿与趋势分析：文献综述——综合证据，也说明边界

## 核心问题定义
判断本课题是否做对，看四件事：趋势是否由可核对的年度分布支撑；演化是否说清"什么时候、因为什么变化"；代表作是否覆盖各阶段且口径可说明；空白是否有排除证据而不是检索遗漏。

## 答题过程设计
probe → extract → 冻结 records.json（缺年份列名不删）→ identity 去重 → trendstat yearly/topics/signals（年度分布、主题-年度、拐点信号）→ 代表作多口径选取落盘 → trendstat audit（趋势断言必须回指真实统计行，幻影年份拒绝）→ evidence/synthesis（关键判断回链+结论分级）→ gaps validate（空白回指检索记录）→ emit。

## 交付物清单（week4/Deep Research & Literature Review/challenge-073af7d3/v2/）
SKILL.md（name: research-trend-audit，含本题判据对齐"四件事"）、run.py、selftest.py、drkit/（8 模块，trendstat 为本题核心）、hk/、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 9/9 checks pass（8 模块 demo + e2e，已运行）
- 合规：≤50 文件 / ≤2MB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
