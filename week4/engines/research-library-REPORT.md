# research-library 赛道构建报告（8 题）

构建根：`/bohr-workspace/user-files/week4/build/research-library/`
日期：2026-11-24 · Python 3.12（引擎兼容 3.9+，仅标准库）· 本机 LibreOffice 24.2.7.2 可用于真实执行验证

## 引擎（engine/rlkit，11 模块 + 共享 hk/）

| 模块 | 用途 |
|---|---|
| identity.py | 文献/条目身份与去重合并（doi_exact > title_exact > 作者年模糊≥0.90；别名支持；DOI 冲突疑似对不合并进 suspects；合并规则/分数/字段冲突全审计）。自 lskit.identity 适配。 |
| normalize.py | 异构来源（RIS/Zotero JSON/CSV）→ 规范记录的字段映射与规范化（作者 Family, Given、年份抽取、DOI 归一），逐字段出处 `_provenance`，不可映射字段进 `extra` 并单列。 |
| metarepair.py | 基于案例提供 API 快照的离线元数据修复：DOI>标题匹配快照；fill_missing（默认，不覆盖已有值）/ prefer_snap；每次填充带来源标注，冲突留痕，无快照=unrepaired 不编字段。 |
| tags.py | 标签/集合操作 + 审计日志：幂等（重复=already）、未知条目 refused（防标签错落相邻条目）、inverse_ops+rollback 精确恢复初态（demo 断言）。 |
| versions.py | 文件版本关系：同哈希=副本/别名；同词干不同哈希=版本序列按 mtime 建 supersede 链；同名不同内容冲突保留不覆盖；管理性版本注记与内容证据互验，不符即标记。 |
| filelib.py | 目录盘点（sha256/skips 留痕）、内容哈希去重、落库计划（模板驱动、目标冲突加哈希后缀改名、永不覆盖）、归档交接清单。 |
| sqlite_ops.py | SQLite 目标端事务化迁移：单事务批次、失败整体回滚；身份键幂等 upsert（重跑 unchanged）；policy=keep 冲突保留；verify 精确差异（missing/mismatched）；Datasette CSV 导出。 |
| ledger.py | 软件自动化操作账本：步骤 pre/post 目录哈希快照、终态检查（产物存在且非空）、失败记录+rollback 到前置状态、assert_idempotent 二次运行零差异断言。 |
| soffice_ops.py | LibreOffice headless 真实执行：import_dataset / recalculate（专用 profile 强制 load 重算 OOXML/ODFRecalcMode=0）/ export_pdf（%PDF 魔数校验）/ verify_computed（重算后 CSV 网格供数值断言）；不可用→诚实 unavailable；demo 实测缓存值 0 被真实重算为 5。 |
| htmlsnap.py | 留存源 HTML 快照解析：citation/DC/og meta 抽取+字段出处；参考文献列表结构性排除并显式警告（防"把文献列表当当前论文"）；元素 id/文本指纹锚点定位（行号+上下文）。 |
| kb.py | 知识库检索与证据回链：块索引（文件+locator+sha256）、BM25 式打分、引用机械核验（quote 必须真实出现在定位块否则作废）、缺证分级（no/weak/conflicting + 缺什么）。 |
| hk/（共享） | probe（读真实输入结构+哈希）、extract（PDF/CSV/XLSX/DOCX/JSON/TXT 带定位抽取）、result（result.json 组装：case_id+output_contract 全字段）、compliance（交付自查）。 |

`run.py`：probe/extract/emit 统一入口 + rlkit 模块 CLI 透传。`selftest.py`：11 模块 demo + 1 次端到端（合成 case → probe → extract → rlkit.identity 命令 → emit → result.json 校验）。

## 每题 SKILL 与自测

| cid | SKILL name | selftest | 合规 |
|---|---|---|---|
| agent-d1ab67e5 | software-ops-ledger | 12/12 | ok（22 文件/132823B） |
| challenge-00e37955 | research-library-steward | 12/12 | ok（22/131693） |
| challenge-2bfd9194 | file-landing-versioning | 12/12 | ok（22/131900） |
| challenge-5047f57f | page-citation-capture | 12/12 | ok（22/132049） |
| challenge-71c94fb7 | source-to-sqlite-migration | 12/12 | ok（22/132293） |
| challenge-80dd5ddc | kb-grounded-qa | 12/12 | ok（22/131798） |
| challenge-912f63bd | sci-automation-steward | 12/12 | ok（22/131601） |
| zotero-ai-a207356c | zotero-library-ops | 12/12 | ok（22/133103） |

每个 v2/ 含：SKILL.md（中文，exemplar 结构：何时使用/输入/输出/工作流/本题判据对齐/交付物/证据与审计规则/异常处理表/最小示例/公开作品 URL）、run.py、selftest.py、rlkit/、hk/、examples/、GITHUB_URL.txt（首行指向 `.../week4/Research%20Library/<cid>/v2`）。

## 定制要点（对照 brief 的 special 与判据）
- **agent-d1ab67e5**：真实 LibreOffice 链（导入→强制重算→数值核对→PDF 魔数），账本幂等/回滚/终态断言；soffice 缺失时 demo 断言诚实 unavailable 路径，绝不伪造。
- **challenge-00e37955 / 2bfd9194 / 80dd5ddc**：真实文件库盘点、内容哈希判重复与版本、管理性注记互验、skips/conflicts 留痕（"不把未完成写成完成"）；80dd5ddc 加 kb 引用机械核验与缺证分级。
- **challenge-5047f57f**：离线快照边界（scope_note 区分快照与在线）、参考文献列表防误取、可复核锚点（sha256+行号）。
- **challenge-71c94fb7 / 912f63bd**：真实初始 SQLite 副本上的事务化迁移、幂等重跑、verify 精确差异、Datasette CSV 交接；只触达组织方本地/案例提供来源。
- **zotero-ai-a207356c**：库文件前后快照与恢复、fill_missing 不覆盖正确字段、只读策略（C03）写操作 refused、库内回答只依据库内条目且引用机械核验、图像型专利 out-of-scope。

## 假设与决策记录
1. 评测环境可能没有 soffice：所有软件执行经 `Soffice.status()` 门控，缺失时交付诚实 unavailable + 受限说明，selftest 在两种环境下都通过（本机实测有 LibreOffice 24.2，真实链路断言通过）。
2. 原始输入一律只读：所有写入（SQLite、落库计划、库操作）发生在 /app/work 副本，溯源链完整。
3. 重算采用 LO 官方配置项（OOXML/ODFRecalcMode=0 的独立 profile），不修改用户配置；用"缓存值故意错误→重算后必须等于真实值"作为真重算断言。
4. 语义判断（相关性、归属、作答）按 Hard Lesson 留给 Agent；引擎只做确定性簿记，全部中间产物 JSON 落盘。
5. GITHUB_URL.txt 指向的仓库路径为约定占位（hehekevin/boerai/week4/Research Library/<cid>/v2），与各题 SKILL.md 末尾"公开作品"一致；git 操作不在本任务范围内。
6. challenge-912f63bd 为领域总课题，按 brief"只需选择一个明确问题"选定采集→SQLite→Datasette 链路做深；challenge-00e37955 为资料管理总课题，采用全栈（盘点/版本/元数据/标签/检索）组合。

## 已知限制
- Datasette 的 HTTP 分页/过滤/HTML 展示属组织方本地服务侧，Skill 交付其所需的 CSV 与核验记录，不模拟 HTTP 服务。
- Chromium/Playwright/MV3 运行环境由组织方提供，Skill 在留存快照上完成确定性部分。
- 大文件（>60MB）只列清单不哈希（skips 显式标注），避免评测超时。
