# 交付标准（spec）：challenge-666fefb0 文献与资料自动分类

## 核心问题定义（来自题面）
对混杂文件库做真整理（不停在建议清单）：每份文件的归属与标签可用原文/元数据核对（缺失字段如实标注，不凭空补作者/年份/DOI）；命名、去重、移动操作留可回滚记录（同名不同版本不覆盖不删除）；换批同类文件重跑结果一致（幂等）。覆盖文件类型、元数据字段、目录层级、重复文件、版本差异、权限与来源六类要素。

## 答题过程设计
1. probe 盘点 → inventory.json（路径+sha256+类型）；Agent 逐文件核实元数据（缺失→unknown）。
2. Agent 语义分类 → categories.json（含归属依据）；版本信号 `fileorg.guess_version` 候选+确认 → versions.json。
3. `lrkit.fileorg plan` → move/skip/conflict 计划（命名模板，缺字段降级 unknown；同名不同内容→conflict 不覆盖）。
4. 审阅后 `lrkit.fileorg apply`（复制式执行，源永不丢失，ops_log 含 undo）。
5. 重跑 apply 验证幂等（全部 already_done）。
6. emit 交付 library_manifest.md（前后对照）。

## 交付物清单
SKILL.md；run.py；selftest.py；engine（lrkit+hk）；examples/README.md；GITHUB_URL.txt。运行交付：inventory.json、categories.json、plan.json、ops_log.json、versions.json、library_manifest.md、result.json。

## 验收标准与自测结果
- `python selftest.py` → 15/15 checks pass；fileorg demo 在真实临时目录断言：计划计数（2 move/1 skip）、unknown 降级、apply 成功、重跑幂等、preprint 版本识别。
- 合规：`hk.compliance.check_skill(v2/challenge-666fefb0)` → ok=true。
- 已知限制：分类与元数据核实由 Agent 完成（引擎保簿记）；加密 PDF 只能依赖案例提供的元数据线索。
