"""rlkit · 资料管理/科研自动化赛道确定性引擎（research-library track）。

模块与对应题目：
  identity    记录身份/匹配/去重合并（Zotero 去重、跨来源迁移去重）
  normalize   元数据规范化与字段映射（异构来源 → 规范记录，字段出处保留）
  metarepair  基于案例提供 API 快照的元数据修复（离线、优先级、来源标注）
  tags        标签/集合操作 + 审计日志 + 幂等（Zotero 标签、库内批量调整）
  versions    文件版本链/别名重建（内容哈希 + mtime，谁替代谁）
  filelib     文件库盘点/落库计划/内容去重/归档清单
  sqlite_ops  SQLite 目标端事务化迁移/幂等 upsert/完整性校验/Datasette CSV 导出
  ledger      软件自动化操作账本（状态快照、幂等断言、回滚、终态检查）
  soffice_ops LibreOffice headless 真实执行（导入/重算/PDF 导出；不可用则诚实报告）
  htmlsnap    留存源 HTML 快照解析（citation meta 抽取、锚点定位、参考文献列表防误取）
  kb          知识库检索与证据回链（块索引、引用坐标、缺证分级）

引擎只做确定性簿记；语义判断（相关性、分类、回答）由加载 Skill 的 Agent 完成，
中间产物一律落盘为 JSON，保证可复跑、可审计。绝不伪造软件执行结果。
"""
