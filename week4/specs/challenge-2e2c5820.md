# 交付标准 · challenge-2e2c5820 实验方案可行性评估

## 核心问题定义
把"这份方案能不能开工"变成可复跑的确定性审查：六面（设备/材料/时间/样本/伦理/安全）12 项检查表逐项带证据判定；资源核对对组织方提供的库存/价格/预约合同做精确算术（数量、价格、时长、预约窗，Fraction/int）；结论由 verdict 计算——可行/有条件可行（条件逐条列出）/不可行/无法完整判定（未查项显式列出）。"方案没写"绝不默认"方案满足"。

## 答题过程设计
probe（读真实 case 结构）→ extract（材料带定位落盘）→ review 预扫描（planparse 候选+全 unchecked checklist+空风险台账）→ Agent 逐项带 quote+locator 判定 → resources 精确核对（materials 四态/budget/schedule/booking/bounds）→ riskreg 验证（高风险无缓解驳回、异常步骤映射失败模式）→ plandiff 版本比较（3 候选版本，变更强制重跑）→ verdict 计算 → emit（result.json 含 case_id+output_contract 全字段）。

## 交付物清单（week4/Experimental Design/challenge-2e2c5820/v2/）
SKILL.md（含本题判据对齐，引用题面"三件事"与"方案没写误当满足"原文）、run.py、selftest.py、edkit/（6 模块）、hk/（probe/extract/result/compliance）、examples/、GITHUB_URL.txt。案例交付：review_report.md、verdict.json、checklist.json、materials_check.json+证据包、risk_register.json、plan_struct.json（各版本）+plandiff.json。

## 验收标准与自测结果
- `python3 selftest.py` → 7/7 checks pass（6 模块 demo + e2e；含未检查项→incomplete 守卫、精确算术断言）
- 合规：hk.compliance.check_skill ok=true（≤50 文件 / ≤2MB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效）
- 真实可运行引擎；无预制答案
