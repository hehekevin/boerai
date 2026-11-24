# 交付标准 · challenge-e7598a44 科研问题驱动检索：科研检索：找到文献，也保留筛选依据

## 核心问题定义
判断本课题是否做对，不看检索了多少次、覆盖了多少数据库，而看三件事：问题被拆成了哪些可检索的子问题、每个子问题是否找到了足以支撑回答的证据、以及检索过程能否解释和复现。

可选择的突破方向：  
优先考虑以下五个方向，也允许提出其他具有明确科研价值的检索问题。

## 答题过程设计
probe → extract → lskit 模块处理（qplan+iterloop）→ emit（result.json 含 case_id+output_contract 全字段）。语义判断由 Agent 完成并落盘 JSON；匹配/计数/差异/停止判据由引擎确定性完成。

## 交付物清单（week4/Literature Search/challenge-e7598a44/v2/）
SKILL.md、run.py、selftest.py、lskit/（10 模块）、hk/、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 11/11 checks pass（已运行）
- 合规：21 文件 / ≤94KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
