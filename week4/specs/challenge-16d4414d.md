# 交付标准 · challenge-16d4414d 论文逻辑与论证审查：发现问题，也给出证据

## 核心问题定义
题面三件事：报出的问题是否真实存在、能否回到原文的某一句话；定位是否精确到评审可以直接核对，而不是只给章节名；修改建议是否可执行（补什么证据、改哪一句、把哪个结论强度降下来）。重点防误读：有意设置的对照、明确标注的假设、转述他人观点不得报成作者自相矛盾。

## 答题过程设计
probe → extract → audit 预扫描 → claims 主张抽取（归因：作者/转引/假设；强度；因果标记）→ crosscheck 论断与被引片段并列（四态建议）→ consistency 跨节衔接观察 → 台账入册（severity_basis 必填）→ findings validate → checklist → report → emit。

## 交付物清单（week4/Academic Review/challenge-16d4414d/v2/）
SKILL.md（含"三件事"对齐）、run.py、selftest.py、arkit/（11 模块，本题主力 claims/crosscheck/consistency/findings/report）、hk/、examples/、GITHUB_URL.txt。案例交付：report.md/report.json、ledger.json、claims.json、crosscheck.json、consistency.json。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（claims demo 演示三归因防误报；findings demo 演示伪造摘录驳回）
- 合规：22 文件 / ~116KB / hk.compliance.check_skill ok=true
- 真实可运行引擎，非模板壳；不含预制答案
