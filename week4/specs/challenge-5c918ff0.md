# 交付标准 · challenge-5c918ff0 多数据库联合检索：科研检索：找到文献，也保留筛选依据

## 核心问题定义
判断本课题是否做对，不看接入了几个库、发出了多少次请求，而看三件事：不同库的结果能否被可靠地归并成一份不重复、字段可用的记录集；每条记录的关键字段能否追溯到来源库与原始响应；哪些库、哪些字段没有覆盖到，能否被明确说出来而不是被静默吞掉。

可选择的突破方向：  
优先考虑以下六个方向，也允许提出其他与多库联合检索相关的明确问题。

## 答题过程设计
probe（读真实 case 结构）→ extract（材料带定位落盘）→ lskit 模块处理（identity.dedupe+field_map）→ emit（result.json 含 case_id+output_contract 全字段）。语义判断由 Agent 完成并落盘 JSON；匹配/计数/差异/停止判据由引擎确定性完成。

## 交付物清单（week4/Literature Search/challenge-5c918ff0/v2/）
SKILL.md（含本题判据对齐"三件事"）、run.py、selftest.py、lskit/（10 模块）、hk/（probe/extract/result/compliance）、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 11/11 checks pass（10 模块 demo + e2e，已运行）
- 合规：21 文件 / ≤94KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
