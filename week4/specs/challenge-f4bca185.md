# 交付标准（spec）：challenge-f4bca185 文献数据清洗与标准化

## 核心问题定义（来自题面）
把一批真实文献抽取结果端到端清洗成可统计数据表：规得齐（同指标同字段名/类型/允许值）、换得准（单位转换保留原值+公式+精度）、合得对（按可解释判定键合并，重复记录≠重复实验）、追得回（每个改动值沿规则编号回到输入行与原始文献，不敢确认的值单独列出）。同时交出变更记录与待确认清单。

## 答题过程设计
1. probe/extract；冻结 rows.json（row_id+source+原值）。
2. 数据画像（列名差异/单位写法/缺失/重复模式）→ 定 rules.json（编号+优先级+适用条件，kind ∈ rename/unit/synonym/range/required）。
3. `lrkit.clean apply` → cleaned + changelog（行级留痕）+ review（冲突/无规则单位/越界）。
4. `lrkit.clean dedup` 按判定键分组；键外有差异 → review 不自动合并。
5. Agent 裁决 review（裁决也进 changelog）。
6. emit 交付。

## 交付物清单
SKILL.md；run.py；selftest.py；engine（lrkit+hk）；examples/README.md；GITHUB_URL.txt。运行交付：cleaned.json、rules.json、changelog.json、review.json、dedup.json、report.md、result.json。

## 验收标准与自测结果
- `python selftest.py` → 15/15 checks pass；clean demo 断言换算留痕（公式+原值）、越界标记、同义归一、"同物质不同条件不自动合并进 review"。
- 合规：`hk.compliance.check_skill(v2/challenge-f4bca185)` → ok=true。
- 已知限制：规则库需按案例列名/单位实际配置（Agent 工作）；同义词表只覆盖案例内出现的写法，不内置领域词库。
