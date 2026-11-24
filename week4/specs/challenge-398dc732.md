# 交付标准 · challenge-398dc732 学术审查领域总课题：论文质量审查

## 核心问题定义
按题目检查项逐条审查输入；为每个问题提供原文位置和判断依据；区分事实错误、证据不足、规范问题和建议性意见；无法确认的标待复核、不凭空补结论。组织方特别要求：实际全文替代旧短摘录、每题有具体 facets 与 typed findings、**no forced or planted defect verdicts**。

## 答题过程设计
probe（读本题 facets 与 output_contract）→ extract → audit 预扫描（观察≠结论）→ 按本题 facets 裁剪 checklist → Agent 逐面审查（缺陷入册/有意安排销 pass/材料不足标 needs_review）→ findings validate → report（零发现为合法结局）→ emit。

## 交付物清单（week4/Academic Review/challenge-398dc732/v2/）
SKILL.md（通用审查内核说明）、run.py、selftest.py、arkit/（11 模块）、hk/、examples/、GITHUB_URL.txt。案例交付：report.md/report.json、ledger.json、checklist.json、prescan_full.json。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（含零发现干净结局与伪造发现驳回）
- 合规：22 文件 / ~116KB / hk.compliance.check_skill ok=true
- 真实可运行引擎，非模板壳；不含预制答案
