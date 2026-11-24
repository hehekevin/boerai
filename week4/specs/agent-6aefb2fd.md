# 交付标准 · agent-6aefb2fd 多步骤数据分析 Agent：科研数据分析：给出结果，也保留计算依据

## 核心问题定义
一条真实分析任务能否从原始表推进到可交回的报告：导入、清洗、分析、可视化、报告五段在同一环境里串通；数值、统计口径与图形算对，处理规则与实际执行一致；证据链完整到可以重跑。

## 答题过程设计
probe（读真实 case 结构）→ extract/tables（表格统一落盘）→ dakit.profile（画像+连接候选）→ dakit.align（字段映射带置信度）→ dakit.clean（规则文件+行级账本）→ dakit.stats（假设先行+精确检验）→ dakit.charts（选型+一致性校验）→ dakit.report（数字只许回填自 stats.json）→ emit（result.json 含 case_id+output_contract 全字段）。语义判断由 Agent 完成并落盘 JSON。

## 交付物清单（week4/build/research-data-analysis/v2/agent-6aefb2fd/）
SKILL.md（含本题判据对齐）、run.py、selftest.py、dakit/（7 模块）、hk/（probe/extract/result/compliance）、examples/README.md、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 8/8 checks pass（7 模块 demo + e2e，已运行；统计 demo 断言教科书值：配对 t=4.0621/p=0.002833、Welch t=-5.4349/df=21.982/p=1.855e-05、χ²=6.6516/p=0.00991）
- 合规：hk.compliance.check_skill ok=true（≤50 文件 / ≤500KB 单文件 / ≤2MB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效）
- 真实可运行引擎，非模板壳；不含预制答案
