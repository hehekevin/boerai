# 交付标准（spec）：challenge-95061011 多文档比较与整合

## 核心问题定义（来自题面）
把同一研究问题下的多篇论文落到同一套字段定义上：对得齐（逐格对照有意义）、填得准（单元格取值来自所标论文，单位/数据集/指标口径随值记录）、说得清（结论一致/冲突时归因到样本/方法/条件/指标差异，可核查）、查得回（每格回到原文具体位置，可复跑、抽样核对、增量加论文）。

## 答题过程设计
1. probe/extract/blocks（每篇论文一个 source 编号）。
2. 定 fielddict.json（七组字段：对象/数据/方法/条件/指标/结论/局限；comparability 声明）。
3. 逐篇填 matrix.json（单元格带 evidence loc+quote；取不出保 not_reported）。
4. `lrkit.matrix validate` 单元格核验（含单位与字典一致性）。
5. 登记条件 → `lrkit.matrix comparability` 两级对齐（direct/subset 子集划分）。
6. `lrkit.matrix conflict` 冲突归因候选 → Agent 确认写理由，双方原话并列；无法归因标 unresolved。
7. emit 交付。

## 交付物清单
SKILL.md；run.py；selftest.py；engine（lrkit+hk）；examples/README.md；GITHUB_URL.txt。运行交付：fielddict.json、matrix.json、comparability.json、conflicts.json、matrix_report.json、report.md、result.json。

## 验收标准与自测结果
- `python selftest.py` → 15/15 checks pass；matrix demo 断言：单元格核验通过、"单位口径不符（nm vs eV）"被抓出、lamp_w 条件不一致→subset 判定、冲突归因候选正确。
- 合规：`hk.compliance.check_skill(v2/challenge-95061011)` → ok=true。
- 已知限制：结论方向与关系强度的判读由 Agent 完成；归因候选来自条件差异的机械比对，最终归因需 Agent 回原文确认。
