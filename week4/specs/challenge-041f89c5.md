# 交付标准（spec）：challenge-041f89c5 科研选题与创新性评估

## 核心问题定义（来自题面）
把研究设想推进到可决策的评估结论，四件交付齐全且一致：研究问题被拆成可检验的表述（对象/变量/基线/预期结论/可证伪条件）；创新点与最近的工作逐条划清边界（区分方法/数据/场景迁移/结论修正，判定是否已被覆盖）；可行性结论的每个前提有来源或被明确标为假设（带失败风险）。检索范围诚实："检索不到"≠"尚无人研究"；冲突证据登记取舍。

## 答题过程设计
1. probe/extract/blocks。
2. problem.json 五项拆解 → `lrkit.novelty problem`（缺一即 testable=false）。
3. 已有工作比较矩阵 comparison.md（任务/方法/数据/评价/结论），标 closest work。
4. novelty.json 逐条判定（kind+boundary+evidence）→ `lrkit.novelty novelty`（distinct 须逐字差异证据；covered 不得仍称创新）。
5. 冲突证据 `lrkit.claims conflicts` 登记。
6. feasibility.json 前提清单 → `lrkit.novelty feasibility`（裸前提拒绝；假设须带风险）；结论只给条件式表述。
7. emit 交付。

## 交付物清单
SKILL.md；run.py；selftest.py；engine（lrkit+hk）；examples/README.md；GITHUB_URL.txt。运行交付：problem.json、comparison.md、novelty.json、feasibility.json、novelty_report.json、report.md、result.json。

## 验收标准与自测结果
- `python selftest.py` → 15/15 checks pass；novelty demo 断言：五项不全判不可检验、distinct 证据核验、"裸前提（无来源未标假设）"被抓出。
- 合规：`hk.compliance.check_skill(v2/challenge-041f89c5)` → ok=true。
- 已知限制：创新性语义判定由 Agent 完成；检索覆盖以案例提供材料为界，不做联网扩展检索。
