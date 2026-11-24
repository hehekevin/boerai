# 交付标准 · challenge-60a8202d 引文追踪与关联文献发现：科研检索：找到文献，也保留筛选依据

## 核心问题定义
判断本课题是否做对，不看抓了多少条记录、调用了几个数据源，而看三件事：扩展出来的文献是否能顺着引用关系说清来路，每一条引用边是否有可回指的数据源依据，以及去重与身份合并之后剩下的清单是否干净到可以直接放进综述。

可选择的突破方向：  
优先考虑以下五个方向，也允许提出其他具有明确文献调研价值的追踪问题。

## 答题过程设计
probe（读真实 case 结构）→ extract（材料带定位落盘）→ lskit 模块处理（graph.expand+identity）→ emit（result.json 含 case_id+output_contract 全字段）。语义判断由 Agent 完成并落盘 JSON；匹配/计数/差异/停止判据由引擎确定性完成。

## 交付物清单（week4/Literature Search/challenge-60a8202d/v2/）
SKILL.md（含本题判据对齐"三件事"）、run.py、selftest.py、lskit/（10 模块）、hk/（probe/extract/result/compliance）、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 11/11 checks pass（10 模块 demo + e2e，已运行）
- 合规：21 文件 / ≤94KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
