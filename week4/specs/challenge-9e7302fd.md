# 交付标准 · challenge-9e7302fd 研究方法与统计审查：发现问题，也给出证据

## 核心问题定义
题面三件事：每条意见能否落回稿件原文的具体位置；严重度是否与缺陷性质匹配，而不是一律写成"重大缺陷"；复核人能否按记录独立重跑，得到同一份审查单。产出是能交给作者逐条回复的审查单（定位/缺陷类型/严重度/依据/修改建议），覆盖研究设计、变量定义、统计方法、样本量、结果报告五面。

## 答题过程设计
probe → extract → audit 预扫描 → stats 数值主张定位与伴随量观察（p 无 CI/数值无 n/"significant"无统计量，只产观察）→ 五面逐项审查（区分 error 与 insufficient_evidence）→ consistency 图表-正文数字核对 → 台账入册（severity_basis 必填）→ validate → report → emit。

## 交付物清单（week4/Academic Review/challenge-9e7302fd/v2/）
SKILL.md（含"三件事"对齐）、run.py、selftest.py、arkit/（11 模块，本题主力 stats/consistency/checklist/findings/report）、hk/、examples/、GITHUB_URL.txt。案例交付：report.md/report.json、ledger.json、stats.json、checklist.json。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（stats demo 演示三类统计报告观察）
- 合规：22 文件 / ~116KB / hk.compliance.check_skill ok=true
- 真实可运行引擎，非模板壳；不含预制答案
