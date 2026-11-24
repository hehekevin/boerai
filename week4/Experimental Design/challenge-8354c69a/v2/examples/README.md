# 示例（合成数据，非正式案例结果）

`python3 ../selftest.py` 会运行：

- 6 个引擎模块的 `--demo`（每个 demo 自带合成数据与精确断言），覆盖两条关键诚实路径：
  - **未检查项守卫**：12 项 checklist 未填时 verdict 必为「无法完整判定」，未查项逐条列出——
    方案没写的内容绝不被默认满足；
  - **精确算术**：短缺量 500 mL、采购价 500×0.35=175 CNY、预算剩余 0.03 CNY、
    预约窗 slack = -5 天、参数越界 5 ℃，全部为 Fraction/int 精确值，float 被拒绝；
  - 高风险无缓解措施被驳回、异常处置步骤未映射失败模式被列出、版本变更强制重跑检查项。
- 一次端到端：合成 case.json + 合成方案/库存/采购目录 → probe → extract → review 预扫描 →
  verdict 守卫（incomplete）→ 模拟 Agent 逐项带证据填表 → resources 精确核对 →
  verdict 构建（有条件可行，条件逐条列出）→ emit → result.json（含 case_id 与全部
  output_contract 字段）。

所有数据均为演示接口而构造，不得作为正式测试案例结果引用。
