# 交付标准 · challenge-cf1995b5 实验方案生成与优化

## 核心问题定义
生成的方案必须先通过引擎验证才能宣称可执行：typed 结构（每参数/步骤/资源带依据定位，无定位被驳回）；变量有操作定义/单位/取值范围；对照注明排除的混杂；设备耗材落到型号规格并与库存/价格/预约合同精确核对；参数区间带来源；风险台账异常处置映射具体失败模式；readiness 由 verdict 计算。

## 答题过程设计
probe → extract → review（提取约束/资源候选）→ Agent 生成 plan_struct+plan.md → 验证门（planparse.validate / resources 四态+budget+schedule+booking+bounds / riskreg）→ 迭代留痕（plandiff，变更强制重跑）→ checklist+verdict → emit。

## 交付物清单（week4/Experimental Design/challenge-cf1995b5/v2/）
SKILL.md（判据对齐引用题面"教科书目录"失败清单与六要素）、run.py、selftest.py、edkit/、hk/、examples/、GITHUB_URL.txt。案例交付：plan.md+plan_struct.json、validation.json、资源核对包、risk_register、checklist、verdict、plandiff。

## 验收标准与自测结果
- `python3 selftest.py` → 7/7 checks pass；hk.compliance.check_skill ok=true
- 验证门不通过按"草稿+缺口清单"交付并 status=partial，不隐瞒
