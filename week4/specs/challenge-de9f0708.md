# 交付标准 · challenge-de9f0708 学术规范与合规检查：发现问题，也给出证据

## 核心问题定义
题面三件事：报出的问题是否真的成立并能指回原文的具体位置；每条判定是否有可核对的依据（规范条款、目标期刊投稿要求、数据授权范围）；报告能否让他人在同一份材料上复跑出基本一致的结论。漏报真实风险与误报不存在的问题同样扣分；红线：不得编造条款、期刊要求或文献元数据；不得把风格差异误判为违规。

## 答题过程设计
probe → extract → audit 预扫描（norms：八类声明 presence + PII 模式命中，均为观察）→ 依据绑定（题目/材料给定指南拆成可核对条目，注明版本日期）→ 六面逐条判定（诚信/引用/隐私/版权/伦理/投稿要求）→ 台账入册（note 记依据出处）→ validate → report → emit。

## 交付物清单（week4/Academic Review/challenge-de9f0708/v2/）
SKILL.md（含"三件事"对齐）、run.py、selftest.py、arkit/（11 模块，本题主力 norms/crosscheck/checklist/findings/report）、hk/、examples/、GITHUB_URL.txt。案例交付：report.md/report.json、ledger.json、prescan_full.json、checklist.json。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（norms demo 演示声明观察与 PII 命中；缺失≠违规）
- 合规：22 文件 / ~116KB / hk.compliance.check_skill ok=true
- 真实可运行引擎，非模板壳；不含预制答案
