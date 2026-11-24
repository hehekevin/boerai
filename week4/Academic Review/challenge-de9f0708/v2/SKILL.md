---
name: norms-compliance-check
description: "Academic norms and compliance checking: declaration presence detectors (ethics/consent/COI/data availability/funding/license), PII-pattern scan, citation and reuse observations, itemized findings with basis citations, and strict false-positive control. Use when: a case asks to check integrity, citation norms, privacy, copyright/licensing, ethics declarations or target-venue requirements against provided materials. NOT for: legal or IRB opinions, plagiarism adjudication, reviewing without the actual materials, or flagging style differences as misconduct."
---

# 学术规范与合规检查：报得出具体条目，也压得住误报

面向"投稿/结题/答辩前按学术规范过一遍"的场景。引擎做确定性簿记：norms 扫描八类声明（伦理审批/知情同意/利益冲突/数据可用性/基金/作者贡献/动物伦理/许可授权）的在与不在，以及邮箱/电话/证件号类 PII 模式命中——**缺失只是"所供文本中未找到"的观察，不是违规判决；模式命中只是"值得人工看一眼"，不是泄密证明**。Agent 结合材料与题目给定依据（规范条款/期刊要求）做判定，findings 验证器保证每条问题可回原文核对。

## 何时使用
* 用例给出稿件/材料（可能附目标期刊指南、条款文本），要求逐条合规检查：每条问题含原文定位、判定依据、严重度和可执行修改建议。
* 判定标准：报出的问题真实成立并能指回原文具体位置；每条判定有可核对依据；报告可在同一份材料上复跑出基本一致结论。**漏报真实风险与误报不存在的问题同样扣分**。

**不适用**：法务或伦理委员会正式意见、论文代写代投、数据重分析、实验方案设计。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（稿件、目标期刊指南/条款、图片来源说明等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" audit   --work "$WORK" --source <稿件文本>
# —— 本题处理步骤（见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/report.md --artifact ledger=$WORK/ledger.json \
    --artifact result=$WORK/report.json
```

**第 1 步 合规面扫描。** 预扫描已含 `norms.scan`：八类声明 presence + 定位、PII 三类模式命中、missing_declarations 清单。全部只是观察。

**第 2 步 依据绑定。** 题目/材料给出目标期刊指南或条款文本时，把要求拆成可核对条目（写入 checklist 或自建清单，注明指南版本与日期），逐条映射到稿件；材料没给的条款**不得编造**（组织方红线：不得编造条款、期刊要求或文献元数据）。

**第 3 步 逐面判定。** 六面可选：学术诚信（数据/图像复用、重复发表、署名、利益冲突、致谢与基金一致性）、引用规范（被引条目与正文论断对应，用 `arkit.crosscheck`）、隐私与数据合规（PII 命中逐条人工核，提出脱敏建议）、版权与许可（第三方图表/代码来源标注与许可）、伦理审查（知情同意/批件编号/动物伦理）、投稿要求（指南条目映射、缺失项/超限项）。每条确认问题入册：quote+locator+justification+**依据出处**（note 字段写明条款/指南来源）。

**第 4 步 验证与报告。** `python -m arkit.findings validate $WORK/ledger.json <稿件文本>`；checklist 销项（声明可能在材料之外 → 标 needs_review 而非违规）；`python -m arkit.report ...`。

## 本题判据对齐（题面"三件事"原文）
1. **"报出的问题是否真的成立并能指回原文的具体位置"** → 验证器核对摘录真实存在；风格差异、学科惯例不得判为违规（观察≠判决的模块设计 + Agent 确认环节）。
2. **"每条判定是否有可核对的依据，例如规范条款、目标期刊的投稿要求或数据授权的范围"** → 台账 note 记录依据出处；指南条目逐条映射并注明版本日期；材料未提供的依据标 needs_review。
3. **"报告能否让他人在同一份材料上复跑出基本一致的结论"** → 扫描结果、台账、清单、报告全部 JSON 落盘；输入 sha256 进 sources。
4. **"漏报一个真实风险与误报一个不存在的问题同样扣分"** → norms 八类声明+PII 扫描保证召回面；findings 验证器+驳回留痕压制误报。

## 交付物
* `report.md`/`report.json`（合规问题清单+依据+严重度+建议）、`ledger.json`、`prescan_full.json`（声明与 PII 观察）、`checklist.json`。

## 证据与审计规则
* 声明缺失 = "所供文本中未找到"，可能存在于材料之外 → 默认 needs_review，仅在题目要求范围内判 issue。
* PII 模式命中必须人工逐条确认上下文（如示例邮箱 vs 真实个人信息），确认前不得报"隐私泄露"。
* 不得编造条款、期刊要求或文献元数据；依据只能引自题目与案例材料。
* 每条问题的修改建议必须可执行（补哪句声明、脱敏哪处、替换哪张图）。

## 异常处理
| 情况 | 处置 |
|---|---|
| 材料缺页/无法解析 | 记 uncertainty，审可读部分，status=partial |
| 引用信息不全 | 对应检查标 needs_review，不臆断 |
| 依据条款获取不到 | 标 needs_review 并写明所需依据 |
| 材料涉及受限数据 | 只报观察与位置，不扩散内容本身 |
| 目标期刊指南缺失 | 投稿要求面标 needs_review，按通用规范检查其余面 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：norms demo 演示声明在/不在观察与 PII 命中；findings demo 演示无依据发现被驳回；端到端合成案例走完整流程。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Review/challenge-de9f0708/v2
