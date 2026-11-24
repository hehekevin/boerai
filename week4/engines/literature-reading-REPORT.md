# 文献阅读赛道（literature-reading）构建报告

构建时间：2026-11-24。构建根：`/bohr-workspace/user-files/week4/build/literature-reading/`。

## 1. 构建内容

- `engine/` — 纯标准库 Python 3.9+ 引擎 `lrkit`（14 模块，每个带 `_demo()` 断言自证）+ 共享运行时 `hk`（probe/extract/result/compliance，从 week4 shared harbor_kit 复制）+ `run.py` 调度器（probe/extract/blocks/emit + 模块 CLI 透传）+ `selftest.py`（14 demo + 1 端到端合成案例）。
- `run.py` / `selftest.py`（根级）— 转发到 engine/ 的便捷入口。
- `examples/README.md` — 声明所有示例为合成数据，非正式案例结果。
- `skills/<cid>.SKILL.md` — 13 份逐题定制的中文 SKILL（frontmatter 为英文 description，含 Use when/NOT for）。
- `specs/<cid>.md` — 13 份交付标准（核心问题定义/答题过程设计/交付物清单/验收标准与自测结果）。
- `v2/<cid>/` — 13 套自包含技能包：SKILL.md + run.py + selftest.py + lrkit/ + hk/ + examples/README.md + GITHUB_URL.txt（首行 GitHub 链接）。每套 25 个文件、约 162KB。

## 2. 引擎模块（lrkit，14 个）

| 模块 | 一句话用途 |
|---|---|
| locate | 证据定位与引文逐字核验（search/verify/split/coverage），所有子流程共用的证据底座 |
| qa | 逐题问答簿记：漏题检查、状态四值、reported/inferred、数字防幻觉 |
| fields | 字段表抽取核验：值-证据绑定、数值字面一致、stated/limited/speculative 分层、not_reported≠failed |
| claims | 论断拆解与四级支持度（support/partial/contradict/not_found）+ 聚合状态 + 冲突双方原话登记 |
| terms | 术语表一致性、逐段对齐簿记、译文数字防补写 |
| clean | 清洗规则库（编号+优先级）：rename/unit/synonym/range/required，行级 changelog 追溯，重复检测区分重复记录与重复实验 |
| fileorg | 文件盘点、命名模板（缺字段降级 unknown）、版本识别、conflict 不覆盖、幂等可回滚 apply |
| notes | 批注锚点逐字核验、类型保真、笔记-原文绑定、关联 basis 强制、检索入口 |
| reader | 阅读会话闭环簿记：open/locate/ask/annotate/export，锚点核验，导出含哈希与版本 |
| bench | 题卡完整性、0/1/2 评分校验（rationale+run_id）、按题型×运行聚合、复跑波动登记、失败归因生成专项题 |
| matrix | 多文档比较：单元格逐字核验+单位口径、direct/subset 可比性、冲突归因候选 |
| novelty | 选题评估：可检验问题五项拆解、创新点逐条划界（covered/distinct/unclear）、可行性前提（来源或假设+风险） |
| webtext | 网页正文切分（剔除导航/广告/参考文献）+ 抓错页信号 + 抓取轨迹清单（离线规则，不联网） |
| formula | LaTeX 结构体检、符号抽取、变量表来源三级（paper/context/common_sense）、AST 白名单安全代入核验 |

## 3. 逐题 SKILL 名称与模块映射

| cid | SKILL name | 聚焦方向 | 主要模块 |
|---|---|---|---|
| challenge-15c85674 | evidence-anchored-paper-qa | 逐题回答+依据+拒答 | locate, qa |
| challenge-105b70ee | evidence-anchored-field-extraction | 字段级证据定位+结论分层 | fields, locate |
| challenge-e5e3be30 | claim-evidence-verification | 论断-段落匹配+四级支持度 | claims, locate |
| challenge-aac59bef | web-paper-translation-alignment | 正文识别+术语一致+来源保留 | webtext, terms, locate |
| challenge-f4bca185 | traceable-data-cleaning | 规则库+行级变更追溯 | clean, locate |
| challenge-666fefb0 | auditable-file-organization | 去重/版本区分+幂等批量整理 | fileorg |
| challenge-c050aaed | annotation-notes-pipeline | 批注锚点+笔记结构化+可解释关联 | notes, locate |
| challenge-f730fc37 | reading-session-ledger | 选区问答+批注沉淀+记录导出 | reader, locate, notes |
| benchmark-a1d81ca4 | reading-bench-runner | 评分表+结果面板+失败归因 | bench, locate |
| challenge-95061011 | multi-paper-comparison-matrix | 共同字段+两级对齐+冲突归因 | matrix, fields, locate |
| challenge-041f89c5 | topic-novelty-assessment | 创新点识别+可行性判断 | novelty, claims, locate |
| challenge-7c37626c | formula-parsing-verification | 变量解释+数值核验 | formula, locate |
| challenge-a028c71c | general-evidence-reading | 通用证据锚定阅读（任务路由） | locate, qa, fields, claims, terms, formula, matrix |

## 4. 自测结果

- engine/selftest.py：**15/15 checks pass**（14 模块 demo + 端到端合成案例 probe→extract→blocks→qa 校验→emit→result.json）。
- 每个 v2 内独立执行 selftest.py：**13/13 套均为 "15/15 checks pass"**（在各自目录内运行，跨目录无污染）。
- 合规（hk.compliance.check_skill，导入自 week4 shared harbor_kit）：**13/13 套 ok=true**（files=25 ≤50、约 162KB ≤2MB、无超 500KB 文件、无符号链接、全 UTF-8、frontmatter 合法、GITHUB_URL.txt 首行为 GitHub 链接）。
- 注意：运行 selftest 会产生 `__pycache__`，交付前已清除；评测平台安装后若重新运行自检同样会生成，不影响合规检查前的提交状态。

## 5. 已知限制与假设

1. **语义判断归属 Agent**：支持度判定、分类、翻译、判分等语义工作由加载技能的 Agent 完成；引擎只强制结构与证据（这与"确定性簿记+LLM 语义判断"的既定模式一致）。
2. **demo 数据全部合成**：模块 demo 与端到端用例中的论文、数值、题卡、文件库均为编造占位，examples/README.md 已声明，不冒充正式案例结果。
3. **离线运行**：引擎不联网；网页题的实时抓取由 Agent 按任务说明用浏览器工具完成，引擎只处理落盘 HTML。
4. **PDF 文本层**：依赖 hk.extract（pdftotext/pypdf/pymupdf 可选回退）；扫描件无文本层时各技能按异常表降级（failed/partial），不做像素 OCR。
5. **挑战 challenge-a028c71c（总课题）**按通用入口实现（任务路由到子流程），深度不及各专项技能，已在该 spec 中说明。
6. **GitHub 链接**按任务给定模板写入（week4/Literature%20Reading/<cid>/v2）；未执行 git 操作、未提交任何内容。
7. 每个 SKILL 选择了题面允许的一个明确突破方向（见上表"聚焦方向"列），未试图覆盖课题全部子方向。
