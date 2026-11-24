# 交付标准 · challenge-bace1c46 文献研究质量评价：维度—判断—证据—等级

## 核心问题定义
题面三件事：每条判断是否对应原文可定位的证据片段；维度覆盖是否与该文献类型应有的检查点匹配；评价结果能否被第二个人按记录独立复核并给出可比结论。反模式：复述摘要、给等级不给证据位置、原文没报告的内容补齐一个"看起来合理"的判断——本成果以强制弃权（insufficient_evidence）对治。

## 答题过程设计
probe → extract → audit 预扫描（辅助证据定位）→ 按文献类型建量表（quality.new_scale）→ 逐维 judge（证据强制 quote+locator；无证据引擎强制弃权）→ grade 显式聚合规则 + derivation 推导行 → appraisal.md 评价表 → emit。

## 交付物清单（week4/Academic Review/challenge-bace1c46/v2/）
SKILL.md（含"三件事"对齐）、run.py、selftest.py、arkit/（11 模块，本题主力 quality/locate/stats/norms）、hk/、examples/、GITHUB_URL.txt。案例交付：appraisal.md、scale.json/appraisal.json、prescan_full.json。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（quality demo 演示证据锚定、无证据强制弃权、undetermined 结局）
- 合规：22 文件 / ~116KB / hk.compliance.check_skill ok=true
- 真实可运行引擎，非模板壳；不含预制答案
