# 交付标准 · challenge-ec02b694 实验参数优化建议

## 核心问题定义
域优先的参数建议：可行域（上下限/步进/互斥）从设备手册/材料规格/安全阈值/历史实验抽取并全部带定位；建议值经 bounds 精确核验（越界量精确、双余量并列、无域参数显式列出）；候选点集成本/时间精确核算；搜索策略写清初始点/补点规则/停止判据；约束冲突给降级路径而非越界推荐。

## 答题过程设计
probe → extract → review → domains.json（来源定位）→ resources bounds 核验建议值 → check_schedule/check_budget/check_booking 成本口径 → strategy.json（收敛判据）→ riskreg（无可行解/冲突/数据缺失/设备报错/指标矛盾）→ verdict 门控 → emit。

## 交付物清单（week4/Experimental Design/challenge-ec02b694/v2/）
SKILL.md（判据对齐引用题面"三件事"：可行域内/权衡口径/链路可复跑）、run.py、selftest.py、edkit/、hk/、examples/、GITHUB_URL.txt。案例交付：optimization_report.md、domains.json、recommendation.json（含 bounds 核验）、strategy.json、成本包、risk_register、verdict.json。

## 验收标准与自测结果
- `python3 selftest.py` → 7/7 checks pass；hk.compliance.check_skill ok=true
- 越界值只能作为冲突点进风险表，不得作为建议输出
