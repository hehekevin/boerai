---
name: structure-logic-forge
description: 论文结构与逻辑优化。把结构问题定位到章节/段落/句子并给出可执行编辑动作（移动/合并/拆分/收窄），而不是泛泛写作建议：章节层级与篇幅确定性审计，跨段 n-gram 重复检测（脚本强制），论断-论据对应扫描（无证据支撑的论断清单），研究问题-方法-结果-结论闭环检查，结论边界不超数据。触发词：论文结构、逻辑优化、论证链、重复检测、结构调整、edit actions。
---

# structure-logic-forge — 论文结构与逻辑优化

**问题定位到句、动作落到段落、论断配论据、重复脚本抓——每条判断都能指回原文。**

## 核心原则（不可违反）

1. **每条判断指回原文**：定位到章节/段落/句子并附原句摘录，不给放之四海皆准的泛泛建议。
2. **动作可执行**：输出 MOVE/MERGE/SPLIT/NARROW/ADD-TRANSITION 级别的编辑动作与参数，不写"建议加强"式空话。
3. **脚本先行**：outline/dup/claims 抽取 0 模型请求，模型只做升级判断与成文。
4. **诚实标注**：材料不足、疑似误报、需要作者裁决的分别进 gaps/human_confirm/uncertainties。

## 运行环境约定

- 输入：`/input/case.json` 与 `/input/task.md`；材料以 case.json 实际路径为准。
- 工作目录 `/app/work`，输出 `/app/output`。资源以 `<SKILL_DIR>` 指代。

## 工作流程

### 阶段 0：盘点（约 1 次模型请求）

```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

读 task.md 确认任务形态（整篇诊断 / 指定章节 / 双语稿）与交付格式。

### 阶段 1：结构审计（0 次模型请求）

```bash
python <SKILL_DIR>/scripts/structure_audit.py --outline /input/materials/manuscript.md --out /app/work/outline.json
python <SKILL_DIR>/scripts/structure_audit.py --dup /input/materials/manuscript.md --out /app/work/dups.json
python <SKILL_DIR>/scripts/structure_audit.py --claims /input/materials/manuscript.md --out /app/work/claims.json
```

- outline：章节树 + 各节段数/篇幅（篇幅失衡定位）；
- dup：8-gram shingle 跨段重复检测（重叠比 >= 0.4 报告）——同义重复的确定性抓手；
- claims：论断句抽取（表明/证明/因此/显著…）+ 行内证据标记（[n]/图号/数值）有无 → 无证据论断清单。

### 阶段 2：诊断与动作（约 4–6 次模型请求）

对照 structure-rules.md 把机器线索升级为带定位的诊断，每条诊断给可执行编辑动作：
`{issue_type: 结构/论证/重复/边界, location: 章节+段落+原句摘录, why: 依据（原文引用）, action: MOVE/MERGE/SPLIT/NARROW/ADD-TRANSITION, params: 移到哪/与哪段合并/收窄为什么}`
- 论证链：研究问题—方法—结果—结论逐环节核对，断裂处指出缺哪一环；
- 结论边界：结论句与数据范围比对，超出 → NARROW 动作给出收窄后的表述。

### 阶段 3：核验与交付（0 次模型请求 + 1 次复核）

组装 `/app/output/edit-actions.json`（可执行动作清单）与 `/app/output/result.json`（合并 output_contract + case_id）。核验：

```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/work/edit-actions-summary.md --require "位置,章节|动作,action,MOVE, MERGE|依据,why,原文" --names "diagnosis,actions,evidence"
```

主产物 `/app/output/diagnosis-report.md`：每条诊断四件套（位置/类型/依据/动作），每条可被作者采纳、部分采纳或驳回。

## 异常处置速查（详见 references/structure-rules.md 第 6 节）

| 情形 | 处置 |
|-|-|
| 无章节结构（纯段落稿） | 按段落群诊断 + 建议增设标题（ADD-HEADING 动作） |
| dup 误报（引用重复） | 人工确认后标记 false-positive，不进 actions |
| 论断其实有远端证据 | 保留诊断但标"证据在 §X，建议加回指" |
| 材料为底稿摘录而非全文 | 诊断范围限于给定文本，gaps 注明 |
| 预算不足 | outline/dup/claims JSON 先落盘（确定性成果），诊断可 partial |

> 注意：--require 的类别分隔符是 | ，类内关键词是逗号；此行正则含逗号类别如 "位置,章节" 表示任一关键词命中即算覆盖。


## 资源清单

- `scripts/` 领域脚本与共享盘点/校验脚本
- `references/` 领域规则与异常处置
- `templates/` result 契约等
- `examples/minimal-example.md`（示例数据，非正式案例结果）
- `README.md`

## 预算红线

64 次模型请求 / 900 秒 / 单响应 16384 token。抽取/检测脚本恒为 0 请求。过 60% 时间立即冻结：脚本产出 JSON 先落盘，status=partial。
