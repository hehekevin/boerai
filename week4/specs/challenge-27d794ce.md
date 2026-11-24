# 交付标准 · challenge-27d794ce 深度研究与文献综述领域总课题

## 核心问题定义
领域总课题：围绕固定研究问题组织文献证据，完成深度研究、综述、系统筛选、趋势分析或选题评估。要求研究边界清晰、引用证据充足可回链、结论可追溯、无法确定部分如实标注。输出三件套：研究产物、证据矩阵、不确定性。

## 答题过程设计
probe → extract → 按任务类型串联八个环节：qplan（拆解）→ iterloop（检索留痕）→ identity（去重）→ screen（筛选，筛选类任务）→ evidence（证据矩阵，必有）→ synthesis（结论分级，必有）→ gaps（空白接地）→ trendstat（趋势类任务）→ emit。每个环节有引擎校验器，中间产物全部落盘可复跑。

## 交付物清单（week4/Deep Research & Literature Review/challenge-27d794ce/v2/）
SKILL.md（name: bounded-lit-review，对齐题面四步要求）、run.py、selftest.py、drkit/（8 模块）、hk/、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 9/9 checks pass（8 模块 demo + e2e，已运行）
- 合规：≤50 文件 / ≤2MB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
