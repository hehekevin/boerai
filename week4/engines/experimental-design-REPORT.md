# experimental-design 赛道构建报告（week4）

构建目录：`/bohr-workspace/user-files/week4/build/experimental-design/`
引擎：`engine/`（edkit 6 模块 + hk 共享运行时套件 + run.py + selftest.py + examples/）
每题技能：`v2/<cid>/`（自包含：SKILL.md + run.py + selftest.py + edkit + hk + examples + GITHUB_URL.txt，各 17 文件 ~107KB）

## 设计模式
确定性簿记在代码、语义判断在 Agent：引擎负责带定位的结构抽取、检查表覆盖控制、
资源/价格/时长/预约窗/参数域的**精确算术**（Fraction/int，float 一律拒绝）、风险台账验证、
版本差异与结论计算；Agent 负责阅读方案与案例材料、逐项判定并带 quote+locator 落盘。
**核心守卫（题面红线）**：checklist 初始全部 unchecked；存在未查项时 verdict 只给
"无法完整判定"并逐条列出——方案没写的内容绝不默认满足（selftest 与 verdict demo
均含此负路径）。每次资源比较携带两个操作数+单位+来源定位；短缺量/价格/越界量精确可复算。

## 引擎模块（edkit，stdlib only，Python 3.9+）
| 模块 | 一句话用途 |
|---|---|
| planparse | 方案结构抽取：章节/参数/步骤/资源为 typed JSON，每条带行定位；validate 要求逐项定位可解析，无定位条目驳回留痕 |
| checklist | 六面（设备/材料/时间/样本/伦理/安全）12 项检查表：规则+必需证据；conditional 强制可执行条件；未查项按 id 显式列出 |
| resources | 精确资源核对：materials 四态（已具备/可外协/需采购/不具备，短缺量+采购价精确）、budget、schedule、booking（ISO 日期 slack）、bounds（有限参数域，越界量精确）；float 拒绝 |
| plandiff | 版本差异：新增/删除/变更带双版本定位；任何内容变更 → 检查表强制重跑（区分"方案改了"与"审查判错"） |
| riskreg | 风险台账：likelihood×impact 分级；高风险无具体缓解/降级路径被驳回；空泛 failure_mode/mitigation 词表驳回；异常处置步骤必须映射具体失败模式 |
| verdict | 结论计算：可行/有条件可行（条件从 conditional 检查项与需采购/外协资源逐条生成）/不可行（blocking 带操作数）/无法完整判定（未查项逐条列出） |

## 每题映射（SKILL name → 主力模块）
| cid | 标题 | SKILL name | 主力模块 |
|---|---|---|---|
| challenge-2e2c5820 | 实验方案可行性评估 | plan-feasibility-review | 全管线：checklist/resources/verdict + plandiff |
| challenge-7be76e91 | 实验方案比较与选择 | plan-comparison-choice | 统一口径矩阵 + resources 精确成本 + verdict 分级 + plandiff |
| challenge-8354c69a | 实验结果解释与异常分析 | result-anomaly-analysis | planparse 定位验证 + riskreg 异常→失败模式映射 + checklist 覆盖 |
| challenge-a57a8549 | 实验方案设计领域总课题 | experiment-design-review-core | 全底座 + 子题型（生成/比较/审查/解释）路径 |
| challenge-cf1995b5 | 实验方案生成与优化 | plan-generate-validate | planparse 验证门 + resources + riskreg + plandiff 迭代留痕 |
| challenge-ec02b694 | 实验参数优化建议 | bounded-parameter-optimization | resources.bounds 可行域核验 + 成本口径 + riskreg 冲突处置 |

## 自测结果
- engine/selftest.py：**7/7 checks pass**（6 模块 demo + 端到端合成案例 probe→extract→review→守卫→填表→资源核对→verdict→emit→result.json）。
- 6 个 v2 各自 selftest：均 **7/7 checks pass**。
- 6 个 v2 各自 hk.compliance.check_skill：均 **ok=true**（各 17 文件、~107KB、无软链、全 UTF-8、frontmatter 合法、GITHUB_URL.txt 首行为 GitHub 链接）。
- demo 精确算术断言：短缺 500 mL、500×0.35=175 CNY、预算剩余 0.03 CNY、总时长 17/6 h、预约 slack=-5 天、越界 +5 ℃、float(0.1) 被拒。

## 已知限制
- planparse 的正则候选抽取是召回工具（markdown 头/多级编号头/编号步骤/"名: 值 单位"参数行），复杂排版需 Agent 按候选确认；判定结论一律由 Agent 完成并过验证器。
- 单位换算不做隐式推断：单位不匹配显式报 unit_mismatch，需案例提供换算依据。
- 引擎不联网：库存/价格/预约合同只能来自案例材料；缺行即显式报 unavailable/no entry。
- PDF/扫描件解析依赖 hk.extract 能力边界；无法解析部分按 partial + uncertainty 处置。

## 假设记录
- 各 v2 的 GITHUB_URL.txt 首行按任务指定写 https://github.com/hehekevin/boerai/tree/main/week4/Experimental%20Design/<cid>/v2（仓库可由协调方推送后生效）。
- 六面 12 项默认 checklist 对应题面"设备、材料、时间、样本、伦理和安全约束"；challenge-8354c69a（结果解释）按题面六要素（假设与变量/对照组/设备材料/时间成本/参数范围/风险和异常）用同构 schema 自建条目，coverage 与 verdict 对面元名称无关（动态统计）。
- 组织方"特殊字段"要求落实为：3 版本候选 → plandiff 成对比较且变更强制重跑；有限参数域 → resources.bounds；真实算术与强制验证 → Fraction/int 精确算术 + verdict 门控；计划情景不冒充真实报价/审批已写入各 SKILL 的证据与审计规则。
- verdict 四态（可行/有条件可行/不可行/无法完整判定）中"无法完整判定"是防"默认满足"的守卫态，与 Harbor 的 partial status 对齐。
