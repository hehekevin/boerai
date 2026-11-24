# 交付标准 · challenge-5c56458d 科研数据库查询与分析：科研数据分析：给出结果，也保留计算依据

## 核心问题定义
题面"三件事"：查询能否在授权的数据快照上直接执行、结果能否与金标准或独立复算对上、字段含义与关联路径能否被他人按记录复核。不看 SQL 行数，看可执行、可复算、可复核。

## 答题过程设计
probe → extract → dakit.dbrun introspect（PRAGMA 实读 schema，只读 mode=ro，不建空库）→ 字段解释与连接路径（profile.join_candidates 值重叠验证 + 数据字典对照）→ dbrun query（SQL 原文+行数+列出处+JOIN 行数膨胀检查+错误现场保留）→ snapshot_csv（CSV+sha256+行数一致性自检=可复算对照物）→ dakit.stats/report 下游 → emit。

## 交付物清单（week4/build/research-data-analysis/v2/challenge-5c56458d/）
SKILL.md、run.py、selftest.py、dakit/（7 模块，dbrun 为核心）、hk/、examples/README.md、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 8/8 checks pass（dbrun demo 现场建 2 表玩具库：自省、聚合查询、膨胀检查、快照一致性、写拒绝、缺库报错全部断言）
- 合规：hk.compliance.check_skill ok=true
- 真实可运行引擎，非模板壳；不含预制答案
