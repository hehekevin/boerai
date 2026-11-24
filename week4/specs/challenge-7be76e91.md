# 交付标准 · challenge-7be76e91 实验方案比较与选择

## 核心问题定义
多候选方案横向比较：先冻结统一可比字段（criteria.json，含机时/耗材/人力/时间窗/参数窗/风险/证据），逐方案同构审查填同一矩阵；成本时间用精确算术（含机时费与人力口径）；可行性分级分开"理论上可行"与"本实验室现在可做"；choice.json 给入选依据与每个落选方案的具体舍弃理由（引用其 blocking/条件/成本差）。

## 答题过程设计
probe → extract → 每方案 review+checklist+resources+verdict（同一套命令同一口径）→ plandiff 版本差异（变更强制重跑）→ comparison_matrix（每格数值+单位+定位）→ choice.json → emit。

## 交付物清单（week4/Experimental Design/challenge-7be76e91/v2/）
SKILL.md（判据对齐引用题面典型失败清单与"可辩护的选择+具体的舍弃理由"）、run.py、selftest.py、edkit/（6 模块）、hk/、examples/、GITHUB_URL.txt。案例交付：comparison_report.md、comparison_matrix.json、choice.json、每方案 checklist/verdict/materials_check、plandiff.json。

## 验收标准与自测结果
- `python3 selftest.py` → 7/7 checks pass；hk.compliance.check_skill ok=true
- 全部方案均不可行时如实输出 none_viable，不硬选；缺字段写"未提供"不补造
