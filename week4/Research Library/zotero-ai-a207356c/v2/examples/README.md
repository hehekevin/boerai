# 示例（合成数据，非正式案例结果）

`python3 ../selftest.py` 会运行：

- 10 个引擎模块的 `_demo()`（每个 demo 自带合成数据与断言）：
  - `identity` 记录去重合并（DOI 精确 / 标题 / 作者年模糊规则，含冲突审计）；
  - `normalize` 异构来源字段映射与规范化（RIS/Zotero JSON → 规范记录）；
  - `metarepair` 基于冻结 API 快照的元数据修复（fill_missing / prefer_snap）；
  - `tags` 标签/集合操作 + 审计 + 幂等 + 回滚恢复初态；
  - `versions` 版本链/别名/同名冲突重建；
  - `filelib` 目录盘点、内容哈希去重、落库计划、归档清单；
  - `sqlite_ops` SQLite 事务化迁移、幂等重跑、verify 比对、CSV 导出；
  - `ledger` 操作账本：状态快照、终态检查、失败回滚、幂等断言；
  - `soffice_ops` 真实 LibreOffice：导入 fods→ods、强制重算（缓存值 0 → 真实值 5，
    若未真正重算则断言失败）、PDF 导出（校验 %PDF 魔数）、不可用路径诚实报告；
  - `kb` 知识库块索引、检索、引用核验（引用文本必须真实出现在定位块中）、缺证分级。
- 一次端到端：合成 case.json + 记录文件 → probe → extract → `rlkit.identity` 去重 →
  emit → result.json（含 case_id 与 output_contract 全字段）。

也可单跑某模块 demo：`python3 -m rlkit.soffice_ops --demo`。

所有数据均为演示接口而构造，不得作为正式测试案例结果引用。
