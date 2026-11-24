# 交付标准 · challenge-a2909a72 学术文献检索：科研检索：找到文献，也保留筛选依据

## 核心问题定义
本课题聚焦开放学术数据库上的检索、关键词组合、候选召回与排序，不负责单篇论文阅读、全文解析、写作润色或资料库整理。

## 答题过程设计
probe（读真实 case 结构）→ extract（材料带定位落盘）→ lskit 模块处理（qplan+iterloop+identity）→ emit（result.json 含 case_id+output_contract 全字段）。语义判断由 Agent 完成并落盘 JSON；匹配/计数/差异/停止判据由引擎确定性完成。

## 交付物清单（week4/Literature Search/challenge-a2909a72/v2/）
SKILL.md（含本题判据对齐"三件事"）、run.py、selftest.py、lskit/（10 模块）、hk/（probe/extract/result/compliance）、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 11/11 checks pass（10 模块 demo + e2e，已运行）
- 合规：21 文件 / ≤94KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
