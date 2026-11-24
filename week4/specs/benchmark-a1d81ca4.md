# 交付标准（spec）：benchmark-a1d81ca4 文献阅读 Benchmark 与评测工具

## 核心问题定义（来自题面）
建设可运行、可复用、可版本化的题集与评测工具（聚焦评分表+结果面板+失败归因一个方向）：判得动（题卡任务/材料/参考答案/评分规则齐备）、跑得一致（固定权限与预算下复跑分数稳定，波动被记录和解释）、查得回（每个分数顺题目 ID 追到原始输出、运行配置和评分记录）、改得动（失败归到具体题型，转化为下一版专项题，只重算受影响分数）。建议按 0/1/2 分记录逐题得分并保留判分依据与争议说明。

## 答题过程设计
1. probe/extract；整理 itemset.json（含快照哈希）→ `lrkit.bench validate-itemset`（缺件题判"判不动"并阻止）。
2. 固定 run 配置（权限/提示/预算/快照哈希）→ runs/<run_id>/ 存原始输出。
3. Agent 按 rubric 锚点评 0/1/2 → `lrkit.bench validate-scores`（强制 rationale+run_id；争议写 dispute）。
4. `lrkit.bench aggregate` → 按题型×运行的 dashboard（n/总分/均分/分布）。
5. 同配置复跑 → `lrkit.bench consistency`（波动逐题登记，禁止只报平均分）。
6. `lrkit.bench failures` → 失败归因 qtype + 下一版专项题种子。
7. emit 交付。

## 交付物清单
SKILL.md；run.py；selftest.py；engine（lrkit+hk）；examples/README.md；GITHUB_URL.txt。运行交付：itemset.json、scores.json、dashboard.json、consistency.json、failures.json、runs/、report.md、result.json。

## 验收标准与自测结果
- `python selftest.py` → 15/15 checks pass；bench demo 断言：未知 item 评分被拒、聚合正确（总分 5、extraction 题型 n=2）、复跑波动（Q2: 1 vs 2）被抓出、失败归因生成 drill 题种子。
- 合规：`hk.compliance.check_skill(v2/benchmark-a1d81ca4)` → ok=true。
- 已知限制：判分语义由 Agent/人工完成（引擎保结构）；双评分人仲裁流程以 dispute 字段承载，未做独立双盲流程。
