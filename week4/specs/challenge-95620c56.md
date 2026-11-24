# 交付标准 · challenge-95620c56 科研数据分析领域总课题：科研数据分析：给出结果，也保留计算依据

## 核心问题定义
总课题通用链：对固定案例（UCI Concrete 1030 / Iris 150 bezdek 变体 / Wine 178 快照与 SQLite 库）完成清洗、统计、可视化、代码执行、多步骤分析或数据库查询，交付可复核结果与规则。核心任务完成、计算准确、覆盖关键字段与证据、可追溯可重跑。

## 答题过程设计
probe → extract/tables → profile → align → clean（规则文件+账本）→ stats（假设先行）→ charts → report 回填 →（数据库案例加 dbrun introspect/query/snapshot）→ emit。同一条流水线处理三个固定案例，不预制答案。

## 交付物清单（week4/build/research-data-analysis/v2/challenge-95620c56/）
SKILL.md、run.py、selftest.py、dakit/（7 模块）、hk/、examples/README.md、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 8/8 checks pass（7 模块 demo + e2e）
- 合规：hk.compliance.check_skill ok=true
- 真实可运行引擎，非模板壳；不含预制答案
