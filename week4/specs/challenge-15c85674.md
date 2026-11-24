# 交付标准（spec）：challenge-15c85674 文献智能问答

## 核心问题定义（来自题面）
读取带段落编号的英文论文与中文问题清单，逐题回答并让读者回到原文核对：结论来自哪里、适用于什么条件、哪些信息论文没有报告。输出契约明确：`answers[]`（question_id/answer/conditions/status）、`claims[]`（kind=reported|inferred、evidence 含段落编号+短引文）、`unanswered_parts[]`、`coverage`；状态四值 answered/partial/insufficient_evidence/input_error；"有依据地说明材料未报告也是有效回答"。

## 答题过程设计
1. probe/extract/blocks：锁定 case_id、paper_id、material_version，建立段落定位底座（保持材料原段落编号）。
2. 逐题：`lrkit.locate search` 定位候选段落 → Agent 读懂后写 answers.json（结论+条件+claims+引文）。
3. `lrkit.qa` 校验：漏题检查、状态合法性、引文逐字核验、数字防幻觉；failed 必须修正。
4. `lrkit.locate coverage` 输出已读/未读段落清单。
5. emit 交付 result.json + answers.json + qa_report.json + coverage.json。

## 交付物清单
SKILL.md；run.py；selftest.py；engine（lrkit 14 模块 + hk 4 模块）；examples/README.md；GITHUB_URL.txt。运行交付：answers.json、qa_report.json、coverage.json、report.md、result.json。

## 验收标准与自测结果
- 引擎层：`python selftest.py` → 15/15 checks pass（14 模块 demo + 端到端合成案例，含 qa 校验 PASS）。
- 关键反例已验证：编造数字、伪造引文、漏题均被引擎抓出（qa demo 断言）。
- 合规：`hk.compliance.check_skill(v2/challenge-15c85674)` → ok=true。
- 已知限制：段落编号缺失时以 block.N 兜底；数学公式仅以文本形式核验，不做 LaTeX 渲染核对。
