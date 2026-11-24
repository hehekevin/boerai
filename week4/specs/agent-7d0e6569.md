# 交付标准 · agent-7d0e6569 文献检索 Agent 与自动迭代：科研检索：找到文献，也保留筛选依据

## 核心问题定义
判断本课题是否做对，不看 Agent 跑了多少轮、调用了多少个工具，而看三件事：闭环是否真的跑起来并留下可复跑的轨迹；每一轮继续、换策略或停止是否有评估信号支撑；失败时是否回退或明确请求人工介入，而不是硬凑一个看起来完整的结果。

可选择的突破方向：  
优先考虑以下五个方向，也允许提出其他具有明确检索价值的 Agent 闭环问题。

## 答题过程设计
probe → extract → lskit 模块处理（iterloop+qplan）→ emit（result.json 含 case_id+output_contract 全字段）。语义判断由 Agent 完成并落盘 JSON；匹配/计数/差异/停止判据由引擎确定性完成。

## 交付物清单（week4/Literature Search/agent-7d0e6569/v2/）
SKILL.md、run.py、selftest.py、lskit/（10 模块）、hk/、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 11/11 checks pass（已运行）
- 合规：21 文件 / ≤94KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
