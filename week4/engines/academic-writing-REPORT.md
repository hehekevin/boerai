# academic-writing 赛道构建报告（week4 / Bohrium Playground period-4）

构建目录：`/bohr-workspace/user-files/week4/build/academic-writing/`
日期：2026-11-24。全部产物离线构建、沙箱内实跑验证。

## 1. 引擎 `engine/awkit`（纯 Python 3.9+ 标准库；9 模块，全部带 `_demo()` 断言）

| 模块 | 职责（确定性簿记） |
|---|---|
| `claims` | 句级论断→来源引文绑定：quote 必须为来源（规范化空白后）子串，否则拒收；含数字句子强制绑定；每个数字必须字面出现在绑定引文中，或登记 `computed`（公式 ast 安全求值 + 公式输入数字必须来自依据句引文）；`insufficient()` 提供诚实【材料不足】路径 |
| `coverage` | 题面必需要点/章节覆盖：关键词命中或 Agent 证据（必须为草稿原文子串）；字数约束；缺项即失败，不接受口头声称 |
| `citecheck` | 数字型/作者年/键型正文引用 ↔ 参考文献表解析；编号连续性；条目必需字段（author/year/title）；未引用条目与混用形态告警 |
| `bilingual` | 术语表机械套用（含 banned 写法拦截）、EN/ZH 段数对齐、漏译检测（CJK 占比+拉丁词数）、配对段数字漂移、术语表内部冲突 |
| `formatcheck` | 标题层级不跳跃、编号连续、分节字数区间、参考文献字段顺序与作者截断（et al）、前置/后置块 |
| `revisions` | 离散编辑操作簿记：锚点必须恰好命中一次（0 次失效/>1 次不唯一均拒绝）；replace/delete/insert_after；改前/改后/依据留痕；accept/reject/回退；LCS 相似度过低标 drift_warning 防整段覆盖 |
| `structcheck` | 论点-论据映射（evidence 必须为草稿/材料原文子串）、结论无支撑检测、claim→claim 支撑图循环检测、跨节 12-gram 重复候选、强因果/全称词结论尺度标记、修辞角色齐备 |
| `deck` | 幻灯片全链路：outline 校验（每页 claim、要点上限、备注不复读、content 页强制 evidence、页面数字字面一致、页数上限）→ 可编辑 PPTX（python-pptx 优先，**纯 zipfile+XML 最小 OpenXML 写出器为保底路径**并如实记录 writer）→ `inspect_pptx` 机械回读（合法 zip、[Content_Types].xml、slide XML、文本框携带大纲文字）→ matplotlib 逐页 PNG 预览 + LibreOffice pptx→PDF 实测；不可用则如实 `unavailable` |
| `scorecard` | 评测簿记：锚点必须为可观察现象（lint 拒绝空泛锚点）、0/1/2 评分合法性（理由+证据必填）、双评 exact agreement、分歧>1 档强制裁定且**只许修订锚点不得改分**、逐题报告（分数全部可从 ratings 复算） |

`engine/hk/`：共享 harbor_kit（probe/extract/result/compliance）原样复制。
`engine/run.py`：probe/extract/emit + 9 个模块子命令分发。
`engine/selftest.py`：9 个模块 demo + 端到端（合成 case → probe → extract → claims validate + deck build（含预览）→ emit → result.json 校验）。**实跑 10/10 通过**；deck demo 中纯 zip PPTX 经本机 LibreOffice 成功转出 PDF，PNG 预览含 CJK 字形。

## 2. 各挑战 SKILL（`skills/<cid>.SKILL.md`，中文，exemplar 结构）

| cid | Skill name | 选定问题 |
|---|---|---|
| benchmark-d57ad64a | writing-benchmark-scorecard | 评分锚点=可观察现象 + 双评一致性 + 可复算报告 |
| challenge-20870c35 | talk-page-planner | 汇报页级组织：每页一主张、页级证据映射、问答准备 |
| challenge-32c0210d | thesis-longdoc-consistency | 长文档跨章节一致性 + 可追溯改稿 |
| challenge-7b09c079 | revision-ledger-editing | 修订级粒度控制 + 改后格式/引用自检 |
| challenge-8021aacb | structure-argument-audit | 论点-论据映射 + 可执行编辑动作的结构诊断 |
| challenge-96263d10 | format-spec-conformance | 模板规格抽检查项 + 转换保真比对 |
| challenge-a2c6f23b | source-fidelity-writing | 通用来源保真写作质量门 |
| ppt-6ad93034 | academic-deck-builder | 大纲先行生成 + 迭代版本簿记 + 真渲染预览 |
| ppt-710fbc72 | deck-template-conformance | 模板约束结构化 + 批量一致性 + 导出一致性 |
| ppt-9508e25f | academic-deck-pipeline | 材料到可放映文件的通用可核验链路 |
| ppt-c7b80f0d | paper-to-slides | 论文主线提取 + 页级引用定位 + 备注分离 |

四个 ppt-* SKILL 均含"可编辑 PPTX 源文件 + 真实渲染 PDF/PNG 预览（不可用则如实报告）"工作流；
challenge-8021aacb 按 special 说明以可编辑 JSON/Markdown 为交付、不强制整篇改写；
challenge-96263d10 按 special 记录 Liberation Serif 字体要求与缺失回退处置。

## 3. 验证结果（每个 v2 实跑）

| v2 | selftest | compliance（hk.compliance.check_skill） |
|---|---|---|
| 全部 11 个 cid | **10/10 pass** | **ok=true**（20 文件，≈148KB，无符号链接，全 UTF-8，frontmatter 合法，GITHUB_URL.txt 首行 https://github.com/…） |

合规检查前已清理全部 `__pycache__`。check_skill 使用系统 kit 路径
`/bohr-workspace/user-files/boerai/week4/engines/shared/harbor_kit` 导入执行。

## 4. 关键假设与决策记录

1. **python-pptx 不可用**（沙箱 `import pptx` 失败）：按预案实现纯 zipfile+XML 的最小 PPTX 写出器为保底路径，并用本机 LibreOffice 转换 PDF 实测证明产物可打开；python-pptx 路径保留在 try/except 之后，build.json 如实记录 writer 与 fallback 原因。
2. **matplotlib / LibreOffice 可用**：预览为真实产物；SKILL 与引擎均约定不可用环境写 `unavailable` 而非伪造。
3. **每 v2 内容相同引擎 + 独立 SKILL.md/spec**：与 exemplar 模式一致；20 文件/v2 远低于 50 上限。
4. **语义判断归 Agent**：引擎只做机械验证；所有"拒绝"路径（无绑定事实句、编造引文、来源外数字、空泛锚点、锚点失效、备注复读、无支撑结论、循环论证）均有 demo 断言覆盖，"放得过对"也有正向断言。
5. **GITHUB_URL 指向约定路径**（hehekevin/boerai week4/Academic Writing/<cid>/v2），未做 git 操作、未提交。
