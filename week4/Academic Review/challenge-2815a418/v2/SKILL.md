---
name: revision-response-ledger
description: "Reviewer-response and manuscript-revision bookkeeping: decompose each review comment into sub-requests, record per-item decisions with reasons, anchor every claimed edit to a verifiable locator in the revised manuscript, and track evidence requests. Use when: a case gives a review-comment list plus a specified manuscript version and asks for a point-by-point response letter and consistent revision mapping. NOT for: writing the paper from scratch, inventing new experimental results, or fabricating editor-facing claims."
---

# 审稿回复与论文修改：完成产物，也保留来源

面向"意见多、要求交叉、改动分散、回复信必须逐条对得上"的返修场景。引擎维护确定性台账（respond 模块）：每条意见拆成子要求，每个子要求有采纳/部分采纳/不采纳/无法补做决策与理由；每处"已修改"声明必须挂能在修订稿中验证的定位锚点；补实验/补数据/补文献类要求有证据清单与到位状态。Agent 负责回复措辞与语气（接受/澄清/礼貌反驳/申诉四档），引擎保证答得全、改得准、证得住、对得上。

## 何时使用
* 用例给出审稿意见清单 + 指定版本稿件（可能多轮），要求产出逐条回复信、修改定位表与证据清单。
* 判定标准：每条意见（含子要求）都有明确处理结论；"已修改"定位能在指定版本稿件中找到；无法补做的给替代说明；回复信、修改稿、版本三者一致。

**不适用**：代写论文、编造实验数据、替作者做学术判断。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（审稿意见、原稿、修订稿、补充数据等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 本题处理步骤（见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/response_letter.md --artifact ledger=$WORK/response_ledger.json \
    --artifact result=$WORK/consistency.json
```

**第 1 步 意见拆解。** 建台账（`arkit.respond.new_ledger(manuscript_version=...)`），每条意见 `add_comment`（编号/审稿人/类型 method|data|writing|format|ethics/严重度）；把一条意见里的多个子要求逐个 `add_sub`——"只答一半"由此暴露。

**第 2 步 逐条回应决策。** 每个子要求定 decision（adopt/partial/rebut/cannot_do/pending）+ reason + tone（accept/clarify/polite_rebuttal/appeal）；反驳必须给依据，cannot_do 必须给替代说明。

**第 3 步 修改定位。** decision 为 adopt/partial 的子要求必须挂 anchors：`{quote（修订稿原文）, locator（§/¶/页/表）}`。定位写改稿后的当前版本坐标，保证改稿后仍有效。

**第 4 步 证据补充。** 需补实验/数据/文献的子要求用 `add_evidence`（item/status provided|planned|cannot_provide|not_requested + source）；无法补做的写明原因与替代说明。

**第 5 步 一致性核对。** `python -m arkit.respond $WORK/response_ledger.json <修订稿文本> $WORK/consistency.json`：引擎逐锚点验证 quote 是否在修订稿真实出现，报告 unanswered（答得全）、bad_anchors（改得准）、open_evidence（证得住）。多轮返修换版本重跑一次即核"对得上"。然后据台账写 `response_letter.md`（逐条：意见原文→决策→修改定位→证据→语气）。

## 本题判据对齐（题面"四件事"原文）
1. **"答得全：每条意见及其包含的多个子要求是否都被识别并给出明确处理结论"** → 子要求级台账，pending 一律进入 unanswered 清单，无法笼统致谢蒙混。
2. **"改得准：回复信声称的每处修改是否真实落在正文"** → 锚点验证：quote 必须在修订稿中真实出现（exact/fuzzy），selftest 演示"声称加了表但正文没有"被抓出。
3. **"证得住：需要补实验、补数据、补文献的意见是否给出可查证的证据或说清为何无法补做"** → evidence 条目带 status+source，planned 项进入 open_evidence 清单。
4. **"对得上：回复信、修改稿与稿件版本是否三者一致"** → 台账记录 manuscript_version，一致性核对可逐版本复跑。

## 交付物
* `response_letter.md`（逐条回复信）、`response_ledger.json`（意见-子要求-决策-锚点-证据台账）、`consistency.json`（一致性核对报告）、修改定位表（含在回复信中）。

## 证据与审计规则
* "已修改"声明无锚点或锚点无法验证 → 进入 bad_anchors，不得在回复信中宣称完成。
* 事实、数字、引用只来自材料；材料不足、冲突、需人工确认的内容明确标注（uncertainty），不新增材料外事实。
* 语气选择记录进台账（四档），避免冒犯性表达、过度承诺和无原则顺从。
* 回复信中标"示例"的示意内容不得冒充正式返修结果。

## 异常处理
| 情况 | 处置 |
|---|---|
| 意见互相冲突 | 两条意见都保留，回复中说明取舍与理由，进 uncertainty |
| 意见本身有误 | decision=rebut + 礼貌反驳语气 + 依据 |
| 稿件缺章节/版本不匹配 | 记录 uncertainty，锚点按实际版本核对，status=partial |
| 无法补实验/补数据 | cannot_do + 替代说明，evidence status=cannot_provide |
| 多轮返修承诺核对 | 换版本重跑 consistency，上轮锚点失效即报 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：respond demo 演示子要求拆解、真锚点验证通过、未答子要求与伪造"已修改"被抓出；另含 10 个审查引擎模块 demo 与端到端合成案例。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Review/challenge-2815a418/v2
