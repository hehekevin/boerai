# 交付标准 · challenge-a0e888fa 科研数据清洗与处理：科研数据分析：给出结果，也保留计算依据

## 核心问题定义
题面"三件事"：每个字段的处理是否有明确规则和依据，清洗后的数据能否直接支撑下游统计，整个过程能否按记录复跑并逐字段核对。修订版案例为已发表聚合表转录件+显式注入存储/编码故障：只做规则化处置与标记，不填补来源缺失/无效值，不做总体统计推断；无承诺的 quality-gold 运行时文件。

## 答题过程设计
probe → extract/tables → profile（字段级问题清单：类型/缺失率/单位/候选主键/mixed 列警告）→ 按数据字典与工单写 rules.json（missing 哨兵显式声明、outlier IQR/z 栅栏、duplicate 真实主键归一化判重）→ dakit.clean（账本：affected_row_ids+before/after 行数+分布影响+fill_value/criterion）→ cleaned.csv 另存 → 字段级质量报告数字全部从账本回填（validate strict 机检手改）→ emit。

## 交付物清单（week4/build/research-data-analysis/v2/challenge-a0e888fa/）
SKILL.md、run.py、selftest.py、dakit/（7 模块，clean/profile 为核心）、hk/、examples/README.md、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 8/8 checks pass（clean demo 断言三条规则的行 id、前后行数与 fill_median 口径）
- 合规：hk.compliance.check_skill ok=true
- 真实可运行引擎，非模板壳；不含预制答案
