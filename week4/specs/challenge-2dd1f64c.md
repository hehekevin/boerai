# 交付标准 · challenge-2dd1f64c 文献筛选与智能排序：科研检索：找到文献，也保留筛选依据

## 核心问题定义
判断本课题是否做对，不看排了多少篇、用了多少特征，而看三件事：给出的相关性判断是否与可复核的标注标准一致，关键文献是否被放到用户真正会看的位置，以及每一条保留、待定、排除的决定能否被他人复核。

可选择的突破方向：  
优先考虑以下五个方向，也允许提出其他具有明确科研价值的筛选与排序问题。

## 答题过程设计
probe（读真实 case 结构）→ extract（材料带定位落盘）→ lskit 模块处理（screen.rank+validate）→ emit（result.json 含 case_id+output_contract 全字段）。语义判断由 Agent 完成并落盘 JSON；匹配/计数/差异/停止判据由引擎确定性完成。

## 交付物清单（week4/Literature Search/challenge-2dd1f64c/v2/）
SKILL.md（含本题判据对齐"三件事"）、run.py、selftest.py、lskit/（10 模块）、hk/（probe/extract/result/compliance）、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 11/11 checks pass（10 模块 demo + e2e，已运行）
- 合规：21 文件 / ≤94KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
