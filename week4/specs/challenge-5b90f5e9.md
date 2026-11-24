# 交付标准 · challenge-5b90f5e9 系统性文献检索与纳排筛选：科研检索：找到文献，也保留筛选依据

## 核心问题定义
判断本课题是否做对，不看筛了多少条记录、写了多少提示词，而看三件事：纳入/排除标准是否被逐条落到可判定的判据上；每条记录的判断是否有理由码和依据片段；整条流程的计数与日志能否支撑一次独立复核。

可选择的突破方向：  
优先考虑以下六个方向，也允许提出其他具有明确方法学价值的筛选问题。

## 答题过程设计
probe（读真实 case 结构）→ extract（材料带定位落盘）→ lskit 模块处理（screen.validate/conflicts+identity）→ emit（result.json 含 case_id+output_contract 全字段）。语义判断由 Agent 完成并落盘 JSON；匹配/计数/差异/停止判据由引擎确定性完成。

## 交付物清单（week4/Literature Search/challenge-5b90f5e9/v2/）
SKILL.md（含本题判据对齐"三件事"）、run.py、selftest.py、lskit/（10 模块）、hk/（probe/extract/result/compliance）、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 11/11 checks pass（10 模块 demo + e2e，已运行）
- 合规：21 文件 / ≤94KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
