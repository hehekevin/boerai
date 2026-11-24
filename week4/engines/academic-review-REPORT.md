# academic-review 赛道构建报告（week4）

构建目录：`/bohr-workspace/user-files/week4/build/academic-review/`
引擎：`engine/`（arkit 11 模块 + hk 共享运行时套件 + run.py + selftest.py + examples/）
每题技能：`v2/<cid>/`（自包含：SKILL.md + run.py + selftest.py + arkit + hk + examples + GITHUB_URL.txt）

## 设计模式
确定性簿记在代码、语义判断在 Agent：引擎负责定位、预扫描观察、台账验证、计数与报告组装；Agent 负责阅读与判断并落盘 JSON。**任何没有"原文摘录+可解析定位+判断依据"的发现都会被 findings.validate 驳回并留痕**；空台账（no defect found）是合法、诚实的结局，selftest 专门演示。

## 引擎模块（arkit，stdlib only，Python 3.9+）
| 模块 | 一句话用途 |
|---|---|
| locate | 文本锚定：§节¶段s句/表号定位单元，摘录原文核验（exact/fuzzy≥0.92） |
| findings | 类型化审查台账 + 反伪造验证器（无 quote+locator+justification 一律驳回留痕） |
| checklist | 六面（fact/citation/method/stats/logic/norm）12 项清单：规则、必需证据、覆盖率、未查项显式列出 |
| stats | 统计报告探测器：定位 p/CI/n/%/mean±SD/效应量，产"伴随量缺失"观察（非判决） |
| crosscheck | 引用-论断核对：本文论断与被引片段 side-by-side + 内容词重叠 + 四态建议 |
| claims | 主张候选抽取：归因（作者/转引/假设）、强度、因果-相关标记，防"转引误报为作者矛盾" |
| consistency | 跨节一致性观察：同名量不同值、摘要独现数字、章节结构缺口（双定位并列） |
| quality | 文献质量量表：维度-判断-证据-等级，无证据强制弃权，显式聚合规则+推导行 |
| respond | 审稿回复台账：子要求拆解、逐条决策、修改锚点验证、证据清单、四维一致性 |
| norms | 学术规范探测器：八类声明 presence + PII 模式命中（缺失≠违规，命中≠泄密） |
| report | 报告组装：按类型/严重度计数、清单覆盖率、待复核、驳回记录、status 建议 |

## 每题映射（SKILL name → 主力模块）
| cid | 标题 | SKILL name | 主力模块 |
|---|---|---|---|
| challenge-0999879e | 论文质量审查 | manuscript-quality-audit | checklist/findings/report + 全部预扫描 |
| challenge-16d4414d | 论文逻辑与论证审查 | argument-logic-audit | claims/crosscheck/consistency/findings |
| challenge-2815a418 | 审稿回复与论文修改 | revision-response-ledger | respond/locate/findings |
| challenge-398dc732 | 学术审查领域总课题 | academic-audit-core | 全管线（本题 facets 裁剪 checklist） |
| challenge-9e7302fd | 研究方法与统计审查 | methods-stats-review | stats/consistency/checklist/findings |
| challenge-bace1c46 | 文献研究质量评价 | paper-quality-appraisal | quality/locate/stats/norms |
| challenge-cbe96f01 | 引用与事实核验 | citation-fact-check | crosscheck/consistency/locate/findings |
| challenge-de9f0708 | 学术规范与合规检查 | norms-compliance-check | norms/crosscheck/checklist/findings |

## 自测结果
- engine/selftest.py：**12/12 checks pass**（11 模块 demo + 端到端合成案例 probe→extract→audit→validate→report→emit→result.json；含伪造发现被驳回、零发现干净结局）。
- 8 个 v2 各自 selftest：均 **12/12 checks pass**。
- 8 个 v2 各自 hk.compliance.check_skill：均 **ok=true**（22 文件、~116KB、无软链、全 UTF-8、frontmatter 合法、GITHUB_URL.txt 首行为 GitHub 链接）。

## 已知限制
- 引擎不联网：引用支持判定只能基于案例提供的被引片段/快照；取不到即 undeterminable。
- stats/consistency/norms 的正则探测器是召回工具，输出一律为"观察"，判决必须由 Agent 完成并过验证器；中文模式的覆盖以常见写法为限。
- claims 的归因/强度/因果分类基于标记词，长句与隐晦表达需 Agent 复核。
- PDF/扫描件解析依赖 hk.extract 的能力边界；无法解析部分按 partial + uncertainty 处置。
- crosscheck 的内容词重叠是词袋相似度，语义等价但措辞迥异的对子会低估，需 Agent 确认（四态中 proposal 只是建议）。

## 假设记录
- 各 v2 的 GITHUB_URL.txt 首行按任务指定写 https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Review/<cid>/v2（仓库可由协调方推送后生效）。
- 默认六面 12 项 checklist 覆盖题面"六类检查项"；各题 SKILL.md 均说明可按 case 的 facets 裁剪并落盘理由。
- 严重度三级（critical/major/minor）+ 性质四类（error/insufficient_evidence/norm_issue/suggestion）与题面"区分错误、证据不足、规范问题和建议"对齐。
