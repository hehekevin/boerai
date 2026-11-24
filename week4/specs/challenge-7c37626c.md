# 交付标准（spec）：challenge-7c37626c 公式解析与数学推理

## 核心问题定义（来自题面）
围绕真实论文公式交付可用结构化表达：认得准（结构/上下标/括号层级/希腊字母/单位不错位不丢项）、讲得清（每个符号有可指回原文的定义，区分原文定义/上下文推断/常识补充）、推得顺（推导拆成可检查步骤，标假设/近似/边界条件与跨公式依赖）、算得回（可计算公式代入复算，符号/单位/数量级错误被同一流程发现）。

## 答题过程设计
1. probe/extract/blocks。
2. Agent 转写 LaTeX（含编号+loc）→ `lrkit.formula check` 结构体检（先修结构错误）。
3. `lrkit.formula vtable`：符号候选抽取→逐符号定义（paper 须逐字证据；common_sense 强制 flagged_assumption）。
4. derivation.md 分步推导（每步假设/近似/依赖）。
5. numeric_steps.json → `lrkit.formula numeric`（AST 白名单安全求值，中间值留痕，expect 不符报比值与排查提示）。
6. emit 交付。

## 交付物清单
SKILL.md；run.py；selftest.py；engine（lrkit+hk）；examples/README.md；GITHUB_URL.txt。运行交付：formulas.json、variable_table.json、derivation.md、numeric_steps.json、numeric_report.json、report.md、result.json。

## 验收标准与自测结果
- `python selftest.py` → 15/15 checks pass；formula demo 断言：结构体检抓不配对括号、符号抽取不受 \frac 干扰、缺定义/常识未标注被抓出、数量级错误（比值=1000）被抓出。
- 合规：`hk.compliance.check_skill(v2/challenge-7c37626c)` → ok=true。
- 已知限制：公式识读（尤其图像）由 Agent 完成；安全求值只支持白名单算术/数学函数，不做符号积分等 CAS 操作。
