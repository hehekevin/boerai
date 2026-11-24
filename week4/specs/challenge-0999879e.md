# 交付标准 · challenge-0999879e 论文质量审查：发现问题，也给出证据

## 核心问题定义
把"这篇稿子哪里有问题"变成一组可执行、可核对、可交办的条目：结构固定的问题清单（类型/性质/严重度/摘录/定位/依据/建议），覆盖事实核验、引用支持、方法设计、统计报告、论证链、学术规范六类检查项；误报可控（学科惯例、有意取舍不得判为缺陷）；零发现是合法结论（组织方：no forced or planted defect verdicts）。

## 答题过程设计
probe（读真实 case 结构）→ extract（材料带定位落盘）→ audit 确定性预扫描（stats/consistency/norms 只产观察）→ Agent 逐面审查入台账 → findings validate（无 quote+locator+justification 或摘录不在原文者驳回留痕）→ checklist 六面销项 → report 组装 → emit（result.json 含 case_id+output_contract 全字段）。

## 交付物清单（week4/Academic Review/challenge-0999879e/v2/）
SKILL.md（含本题判据对齐）、run.py、selftest.py、arkit/（11 模块）、hk/（probe/extract/result/compliance）、examples/、GITHUB_URL.txt。案例交付：report.md/report.json、ledger.json、checklist.json、prescan_full.json。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（11 模块 demo + e2e，已运行）
- 合规：22 文件 / ~116KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（hk.compliance.check_skill ok=true）
- 真实可运行引擎；含伪造发现被驳回与零发现干净结局两条诚实路径；不含预制答案
