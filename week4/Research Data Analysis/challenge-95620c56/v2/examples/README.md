# 示例（合成数据，非正式案例结果）

`python3 ../selftest.py` 会运行：
- 7 个 dakit 引擎模块的 `--demo`（每个 demo 自带合成数据与教科书已知值断言，
  例如 Student 睡眠数据配对 t=4.0621/p=0.002833、R 文档 Welch 示例
  t=-5.4349/df=21.982/p=1.855e-05、手工核算的 χ²=6.6516/p=0.00991）；
- 一次端到端：合成 case.json + 合成 CSV（18 行，含注入的缺失/异常/重复）
  → probe → extract → tables → profile → clean（规则文件驱动，账本记录行 id）
  → stats（Welch t + Levene 方差齐性 + 偏度/峰度规则）→ charts 选型
  → report 数字回填（仅允许来自 stats.json）→ emit → result.json。

所有数据均为演示接口而构造，不得作为正式测试案例结果引用。
正式案例由平台固定提供（UCI Concrete 1030 / Iris 150 bezdek 变体 / Wine 178
快照及 SQLite 数据库），本目录不包含、也不预生成任何正式案例答案。
