# 交付标准 · challenge-9ec929fe 科研代码生成与执行：科研数据分析：给出结果，也保留计算依据

## 核心问题定义
不看生成多少行代码，而看三件事：代码能否在给定数据和环境下真正跑通，数值与图表能否同数据字典、统计口径和金标准对上，过程与失败原因能否被他人复核。最大敌人是"跑通了但算错了"的静默错误。

## 答题过程设计
第 0 步 `selftest.py` 环境自检（引擎零依赖、金标准断言，8/8 不过即停工报告）→ probe/extract/tables → Agent 生成"编排+规则文件"（rules.json/stats_spec.json/shape.json，字段名必须先存在于 profile/数据字典）→ 逐步执行留 run.log（命令+退出码+错误现场）→ 强制结果验证（行数三方一致、静默错误清单、report.validate 数字同源）→ emit。

## 交付物清单（week4/build/research-data-analysis/v2/challenge-9ec929fe/）
SKILL.md、run.py、selftest.py、dakit/（7 模块）、hk/、examples/README.md、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 8/8 checks pass（e2e 注入缺失/异常/重复并机检全链能抓到）
- 合规：hk.compliance.check_skill ok=true
- 真实可运行引擎，非模板壳；不含预制答案
