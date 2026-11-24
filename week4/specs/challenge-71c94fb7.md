# 交付标准 · challenge-71c94fb7 科研资料收集与迁移：科研自动化：完成操作，也保留过程轨迹

## 核心问题定义
真正把采集、字段映射、去重、迁移、完整性校验的链路跑通形成闭环；字段取值与来源一致、映射对得上、去重不漏判不误合并、目标端记录与源端语义一致；输入快照、字段映射表、去重清单、写入日志与差异报告能支撑他人独立复跑。special 明确：每案 3 个真实已发布来源（含归属）+ 真实初始 SQLite 目标 + 事务化采集/迁移/身份/别名/恢复/冲突操作；组织方本地服务，非实时外部服务。

## 答题过程设计
probe → extract → normalize（字段映射+出处+不可映射单列）→ identity（doi_exact>title_exact>作者年模糊；DOI 冲突疑似对不合并进 suspects）→ 复制初始 SQLite 到 work → sqlite_ops migrate（事务、幂等、回滚）→ verify（missing/mismatched 精确差异）→ export_csv → emit。

## 交付物清单（week4/Research Library/challenge-71c94fb7/v2/）
SKILL.md（source-to-sqlite-migration）、run.py、selftest.py、rlkit/（11 模块）、hk/、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（sqlite demo 含幂等重跑 unchanged 与 policy=keep 冲突保留断言）（已运行）
- 合规：22 文件 / ~132KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
