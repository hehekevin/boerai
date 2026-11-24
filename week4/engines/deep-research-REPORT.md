# Deep Research & Literature Review 赛道构建报告（week4, v2）

构建根目录：`/bohr-workspace/user-files/week4/build/deep-research/`
日期：2026-11-24 · Python 3.12（仅标准库）· 全程离线 · 未触碰 git/未提交

## 1. 引擎 drkit（engine/，真实可运行，非模板壳）

`engine/` 含 `drkit/`（8 模块）、`hk/`（harbor_kit 拷贝：probe/extract/result/compliance）、
`run.py`（统一入口 probe/extract/emit + drkit 模块透传）、`selftest.py`、`examples/README.md`。

| 模块 | 来源 | 职责 |
|---|---|---|
| identity | 拷贝自 lskit | 文献记录身份判定与去重（DOI/标题/作者+年模糊），合并规则与字段冲突留痕 |
| qplan | 拷贝自 lskit | 问题拆解校验：子问题可独立检索（searchable_terms 强制）、依赖无环、按证据充分性定停止 |
| iterloop | 拷贝自 lskit | 检索迭代账本：逐轮 signal/decision 强制、边际收益停止判据、回滚 |
| screen | 拷贝自 lskit | PRISMA 式筛选记录：逐条决定+理由码+证据片段、计数可重算、双人分歧待裁决 |
| evidence | 本赛道新建 | 证据矩阵：claim↔原文摘录↔定位；无 quote+locator 的断言拒绝；冲突对裁决必须比较双方证据，"尚存争议"搪塞拒绝；同子问题异极性冲突候选自动提示 |
| synthesis | 本赛道新建 | 综合审计：每句结论分类 fact/inference/undetermined（材料事实/合理推断/无法确定）；悬空引用/伪造 claim_id 拒绝；每个子问题必须被覆盖或显式标缺口，静默遗漏失败 |
| gaps | 本赛道新建 | 空白接地：检索覆盖图（covered/thin/unsearched）；searched_* 空白必须引用真实执行过的 query_id；未检索范围必须标 speculation；与记录矛盾的"无证据"拒绝 |
| trendstat | 本赛道新建 | 趋势统计：年度分布（缺年份列名不删）、主题-年度计数、拐点信号（信号≠结论）；趋势断言必须回指真实统计行，幻影年份/幻影主题拒绝 |

每个模块均有 `_demo()`（含正例+负例断言）与 CLI（`python -m drkit.<mod>` 或 `run.py <mod>`）。

## 2. 每题 SKILL（skills/ + v2/<cid>/SKILL.md）

| cid | SKILL name | 定位 |
|---|---|---|
| agent-f8fb8bda | deep-research-orchestrator | 深度研究全链路：拆解→规划→工具留痕→证据综合，判据对齐题面"三件事" |
| challenge-073af7d3 | research-trend-audit | 趋势/演化/代表作/空白四类产物，判据对齐题面"四件事" |
| challenge-27d794ce | bounded-lit-review | 领域总课题通用管线，对齐题面四步要求与输出三件套 |
| challenge-51977f9b | systematic-review-trail | 系统综述：检索式 intent、版本化纳排、两轮筛选留痕、质量评价 |
| challenge-e97137c9 | review-draft-evidence-link | 综述生成：筛选先于写作、主题从文献长出、逐句回链草稿 |

结构均按 exemplar：英文 frontmatter（Use when…/NOT for…）、何时使用、输入、输出、
工作流（精确命令）、本题判据对齐（引用题面原文判据）、交付物、证据与审计规则、
异常处理表、最小示例、公开作品 URL（`.../Deep%20Research%20%26%20Literature%20Review/<cid>/v2`，& 已转义为 %26）。

## 3. 验证结果（全部实跑）

| v2 | selftest | compliance（hk.compliance.check_skill） |
|---|---|---|
| agent-f8fb8bda | 9/9 pass | ok=true（19 文件 / 111,836 B / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL 有效） |
| challenge-073af7d3 | 9/9 pass | ok=true（19 文件 / 111,794 B） |
| challenge-27d794ce | 9/9 pass | ok=true（19 文件 / 110,805 B） |
| challenge-51977f9b | 9/9 pass | ok=true（19 文件 / 111,348 B） |
| challenge-e97137c9 | 9/9 pass | ok=true（19 文件 / 111,440 B） |

selftest = 8 模块 demo + 1 次端到端（合成 case → probe → extract → qplan/evidence/synthesis
模块命令 → emit → result.json 校验 case_id 与 output_contract 全字段）。
compliance 用 `python3 -B` 跑（防止导入再生 __pycache__）；提交树内无 .pyc。

## 4. 决策与假设

1. **v2 五题共用同一 drkit**：题面要求"选择一个明确问题形成最小成果"，但同一赛道的
   拆解/回链/边界需求一致；每题 SKILL 规定使用哪些模块与落盘文件，差异化在工作流与
   判据对齐，而非代码分叉。每题 v2 自带完整拷贝，可独立安装运行。
2. **Agent/引擎分工**：引擎只做确定性校验与簿记；quote 与原文的一致性、主题归并、
   冲突裁决内容由加载 Skill 的 Agent 完成并落盘——与 exemplar 的"LLM 语义经 agent、
   簿记经代码"原则一致。
3. **诚实行为内建**：undetermined、speculation 空白、zero-gain 检索均为合法且被校验的
   输出路径；引擎拒绝的是"无依据断言/搪塞/静默遗漏"，不是"承认不知道"。
4. **未做**：真实数据库接入（赛题材料驱动、离线约束）；quote 与原文逐字比对的引擎级
   强制（需全文索引，留给 Agent 核对义务，已在 SKILL 审计规则中写明）。
5. 限制复核：19 文件 ≤ 50；单文件最大 < 500KB；总量 ≈112KB ≤ 2MB；无软链；全 UTF-8。
