# 交付标准（spec）：challenge-105b70ee 文献结论与数据提取

## 核心问题定义（来自题面）
按统一字段表把真实论文的研究结论、实验条件、关键指标和数据点抽成结构化结果；正文/表格/图注/补充材料视为同一字段表的不同来源；字段值与原文字面一致（数值、单位、误差、统计量、条件限定不改写）；区分作者明确结论/限制条件/推测性表述；缺项区分"原文未报告"与"抽取失败"；每个字段指回页码/段落/表格行列/图注，字段定义与抽取口径随结果提交。

## 答题过程设计
1. probe/extract/blocks 建立统一 loc 底座（含表格行列 loc 约定 table.T1.r3）。
2. 定 fielddict.json（name/type/unit/required）。
3. 逐字段 locate search 定位 → Agent 取值（值+单位+条件+layer 分层）→ 缺项分类 not_reported/failed。
4. `lrkit.fields validate`：逐字证据、数值字面一致、单位一致、required 的 not_reported 须附查证说明。
5. emit 交付。

## 交付物清单
SKILL.md；run.py；selftest.py；engine（lrkit+hk）；examples/README.md；GITHUB_URL.txt。运行交付：fields.json、fielddict.json、fields_report.json、report.md、result.json。

## 验收标准与自测结果
- `python selftest.py` → 15/15 checks pass；fields demo 断言"数值被改写（152→215）""伪引文（loc 不存在）"均被抓出。
- 合规：`hk.compliance.check_skill(v2/challenge-105b70ee)` → ok=true。
- 已知限制：扫描件无文本层时对应来源字段只能 failed；复合单位换算不在本技能内（属清洗题），原值保留。
