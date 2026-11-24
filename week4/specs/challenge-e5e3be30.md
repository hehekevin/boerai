# 交付标准（spec）：challenge-e5e3be30 文献证据溯源与事实核验

## 核心问题定义（来自题面）
把待核验科研论断落到可判定证据上：拆得开（事实/比较/因果/范围子判断不遗漏不重复）、找得到（最小充分证据精确到段落/句子）、判得准（四级支持度，尤其区分"主题相关"与"真正支持"）、说得清（冲突、样本与范围限制、无法确定部分明确写出）。"论断→证据片段→原文定位→支持度判定→判定理由"链可被独立复核。

## 答题过程设计
1. probe/extract/blocks。
2. `lrkit.locate split` 机械拆分 → Agent 确认子判断类型与粒度。
3. 逐子判断 locate search → 最小充分证据（≤240 字符逐字引文）。
4. 写 claims.json（verdict+rationale+evidence）→ `lrkit.claims validate`（父论断状态由子判断聚合，手填不符即失败）。
5. 冲突用 `lrkit.claims conflicts` 登记双方原话。
6. emit 交付。

## 交付物清单
SKILL.md；run.py；selftest.py；engine（lrkit+hk）；examples/README.md；GITHUB_URL.txt。运行交付：claims.json、verify_report.json、conflicts.json、report.md、result.json。

## 验收标准与自测结果
- `python selftest.py` → 15/15 checks pass；claims demo 断言"范围论断被反例推翻→contradicted""伪引文被抓出""not_found 带证据被拒绝"。
- 合规：`hk.compliance.check_skill(v2/challenge-e5e3be30)` → ok=true。
- 已知限制：支持度判定本身由 Agent 语义完成，引擎只强制证据存在与链条完整；跨页证据需分段引用。
