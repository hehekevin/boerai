# 交付标准 · challenge-8354c69a 实验结果解释与异常分析

## 核心问题定义
把结果解释做成带回溯的台账：趋势/异常/原因/复核/后续五类结论，每条强制 quote+locator+threshold；异常须给偏离口径与程度；原因候选按证据强度排序并分列支持/排除证据；复核步骤必须是可执行动作；不编造湿实验测量、原因或重复数；源数据单位/方法/阈值歧义原样保留。

## 答题过程设计
probe → extract（工作簿/日志带 sheet+行定位落盘）→ review → Agent 填 ledger（planparse.validate 驳回无定位结论）→ 六要素 checklist 覆盖（未查项显式列出）→ riskreg 映射异常→具体失败模式（空泛词表驳回）→ verdict 门控 → emit。

## 交付物清单（week4/Experimental Design/challenge-8354c69a/v2/）
SKILL.md（判据对齐引用题面"无法回溯数据行/阈值/复算就不能作为实验结论"原文）、run.py、selftest.py、edkit/、hk/、examples/、GITHUB_URL.txt。案例交付：interpretation_report.md、ledger.json、checklist.json、risk_register+risk_validation、conclusion_gate.json。

## 验收标准与自测结果
- `python3 selftest.py` → 7/7 checks pass；hk.compliance.check_skill ok=true
- 引擎只做簿记与门控；趋势/异常语义判断由 Agent 完成并带证据落盘
