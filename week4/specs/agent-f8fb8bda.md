# 交付标准 · agent-f8fb8bda 深度研究 Agent：文献综述——综合证据，也说明边界

## 核心问题定义
判断本课题是否做对，看三件事：研究问题被拆成了哪些可独立检索的子问题（带依赖）、每条结论能否回链到具体文献段落、整条路径能否被他人按记录复跑。冲突结论必须比较裁决，拒绝"尚存争议"搪塞；研究空白必须建立在实际检索记录上。

## 答题过程设计
probe → extract → qplan validate（拆解：可独立检索+依赖无环）→ iterloop（逐轮 signal/decision 留痕+停止判据）→ identity（去重留痕）→ evidence validate/conflicts（quote+locator 强制、冲突裁决）→ synthesis audit（fact/inference/undetermined 三分类+子问题覆盖）→ gaps map/validate（空白接地）→ emit（result.json 含 case_id+output_contract 全字段）。语义判断由 Agent 完成并落盘 JSON；校验/计数/停止判据由引擎确定性完成。

## 交付物清单（week4/Deep Research & Literature Review/agent-f8fb8bda/v2/）
SKILL.md（name: deep-research-orchestrator，含本题判据对齐"三件事"）、run.py、selftest.py、drkit/（8 模块）、hk/（probe/extract/result/compliance）、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 9/9 checks pass（8 模块 demo + e2e，已运行）
- 合规：≤50 文件 / ≤2MB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
