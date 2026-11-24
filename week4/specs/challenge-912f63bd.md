# 交付标准 · challenge-912f63bd 科研软件插件与自动化领域总课题：科研自动化：完成操作，也保留过程轨迹

## 核心问题定义
领域总课题，选定"多来源采集 → SQLite 事务化迁移 → Datasette 交接"链路做深。special 明确：每案 3 个真实已发布来源（含归属）+ 真实初始 SQLite 目标 + 事务化采集/迁移/身份/别名/恢复/冲突操作 + 真实 Datasette 目标（HTTP 分页/过滤/CSV/HTML 由组织方本地服务承担）；Skill 侧交付 Datasette 可用 CSV 与核验记录，不触达实时外部服务或 Bohrium 科学空间。

## 答题过程设计
probe → extract → OpLedger 账本（pre/post 状态快照+终态检查）→ normalize → identity → sqlite_ops migrate/verify/export_csv（Datasette 交接）→ assert_idempotent / rollback / handoff → emit。

## 交付物清单（week4/Research Library/challenge-912f63bd/v2/）
SKILL.md（sci-automation-steward）、run.py、selftest.py、rlkit/（11 模块）、hk/、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（已运行）
- 合规：22 文件 / ~132KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
