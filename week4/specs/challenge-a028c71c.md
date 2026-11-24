# 交付标准（spec）：challenge-a028c71c 文献阅读领域总课题

## 核心问题定义（来自题面）
面向整个文献阅读领域的通用任务：读取固定科研材料并完成指定的解析、翻译、问答、提取、核验或知识结构化，关键结果回到原文证据（页码、段落、字段或图表定位）；对未报告、无法判断和材料冲突明确说明；交付结构化结果（输入标识、主结果、证据/来源定位、运行状态和不确定性）。

## 答题过程设计
1. probe/extract/blocks 建立统一证据底座。
2. route.json：识别任务类型（问答/提取/核验/翻译/公式/比较）并记录理由。
3. 按路由表执行对应子流程与引擎校验（qa/fields/claims/terms/formula/matrix，复用同一套 locate 核验）。
4. 组合任务按序执行各自校验。
5. emit 交付（report.md 综合报告 + 子流程主交付物）。

## 交付物清单
SKILL.md；run.py；selftest.py；engine（lrkit 14 模块 + hk 4 模块）；examples/README.md；GITHUB_URL.txt。运行交付：route.json、子流程交付物与校验报告、report.md、result.json。

## 验收标准与自测结果
- `python selftest.py` → 15/15 checks pass（14 模块 demo + 端到端合成案例）。
- 合规：`hk.compliance.check_skill(v2/challenge-a028c71c)` → ok=true。
- 已知限制：通用技能的深度不及各专项技能（专题目录见同 track 其他 challenge）；任务类型识别由 Agent 判断，route.json 留审计线索。
