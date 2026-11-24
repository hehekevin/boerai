"""dakit · 科研数据分析引擎包（仅标准库：csv/sqlite3/statistics/math/json/difflib）

职责边界（确定性簿记在引擎，语义判断在加载 Skill 的 Agent）：
- profile   数据画像：schema 推断、类型检测、表头单位提示、主键唯一性、跨表连接键兼容
- align     字段对齐：多来源列映射（置信度 + 未解析字段显式列出，绝不静默丢弃）
- clean     清洗账本：规则外置为 JSON 数据；每条规则记录受影响行 id、前后行数与分布影响
- stats     描述/推断统计：mean/sd/median/IQR、t 检验（不完全 β 函数精确实现）、
            卡方、相关；假设检查：偏度/峰度规则、Levene 近似、样本量与多重比较提示
- charts    图表选型：数据形态→图型规则（含推荐理由与被否决项）；坐标轴/单位一致性检查
- dbrun     SQLite 运行器：schema 自省、只读查询、行数 + 列出处、结果快照到 CSV
- report    报告回填：{{placeholder}} 只允许来自已计算的 stats JSON；校验器拒绝不可追溯占位符

所有模块含 _demo()：对已知正确答案（教科书数值）做断言。中间产物一律落盘 JSON。
"""
