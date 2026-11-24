---
name: systematic-screening-forge
description: 系统性文献检索与纳排筛选。把研究问题转成可执行检索协议（PICO+纳排标准表），检索结果逐条筛选并保留理由码与支撑片段，多来源去重保留合并依据，各环节计数闭合审计，人工最终确认点显式标注。触发词：系统综述、纳排筛选、检索协议、PRISMA、screening。
---

# systematic-screening-forge — 系统性文献检索与纳排筛选

一句话：**协议先行、逐条留理由码、计数闭合、人工确认点显式。**

## 核心原则（不可违反）

1. **检索协议先行**：研究问题先转成可执行检索式——数据库、字段、时间范围、语种限制、检索日期五要素齐全，并说明与纳入标准的对应关系；五要素缺一不可。
2. **逐条留理由码**：每条记录的纳入/排除判定必须带理由码（I1/I2.../E1/E2...）与摘要中的支撑片段；"只有剩余条数没有合并依据"的去重不合格。
3. **计数闭合**：每阶段输入条数=上阶段输出条数，n_in−n_out=n_excluded，判定依据引用标准编号——脚本审计强制。
4. **冲突不掩盖**：标注分歧记录分歧类型与仲裁结论，不用平均/多数直接掩盖实质性争议；预印本与正式版重复要区分处理。
5. **人工确认点显式**：哪些判断必须由研究者确认、模型输出何时只能作为待复核建议——在协议与台账中显式标注。
6. **脚本先行**：协议骨架、逐条筛选、多源去重、计数审计全部脚本完成（0模型请求），模型只做语义判定与复核。

## 运行环境约定

- 输入：`/input/case.json` 与 `/input/task.md`；材料（研究问题/记录集/已有标准表）以实际路径为准。
- 工作目录 `/app/work`，输出 `/app/output`。引擎以 `<SKILL_DIR>` 指代。

## 工作流程

### 阶段 0：盘点（约1次模型请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：检索协议与标准表（1次模型请求 + 脚本骨架）
```bash
python <SKILL_DIR>/scripts/screening_engine.py --protocol "<研究问题>" > /app/work/protocol.json
```
脚本生成 PICO 要素表、纳入/排除标准骨架（I1/I2/E1/E2/E3）、检索协议五要素模板。模型按题面研究问题补充要素词与标准细则，记录 expansions。

### 阶段 2：多源去重（0次模型请求）
```bash
python <SKILL_DIR>/scripts/screening_engine.py --dedup-multi <来源1> <来源2> ... > /app/work/dedup.json
```
每对重复保留 match_type（doi_exact/title_normalized）与 merge_rationale。

### 阶段 3：逐条筛选（0次模型请求）
```bash
python <SKILL_DIR>/scripts/screening_engine.py --screen <去重后记录集> <标准表.json> > /app/work/screen.json
```
输出逐条 decision（include/exclude/pending）+ reason_code + evidence（摘要命中片段）。

### 阶段 4：模型复核 pending 与边界案例（约3-5次模型请求）
对 pending_review 记录、部分重叠人群、仅有摘要、语言不符等边界情形做语义判定，每条写明理由码归类依据；分歧点写仲裁结论。

### 阶段 5：计数闭合审计与交付（0次模型请求）
```bash
python <SKILL_DIR>/scripts/screening_engine.py --audit /app/work/stages.json
```
stages.json 记录各阶段 {stage, n_in, n_out, n_excluded, criteria_ref}。FAIL 先修计数再交付。

组装 `/app/output/result.json`（合并 output_contract 全部字段与 case_id）：protocol、dedup 报告、逐条筛选表、审计链、human_confirm 清单（人工最终确认项）、gaps/anomalies、status。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/screening-report.md --require "协议|protocol|检索式,纳排|screen|筛选|理由码,审计|audit|计数|闭合" --names "protocol,screening,audit"
```

## 异常处置速查（详见 references/screening-rules.md §6）

| 情形 | 处置 |
|-|-|
| 无标准表输入 | 用 --protocol 骨架 + 模型按研究问题补全，标注"模型起草待确认" |
| 记录无摘要 | decision=pending_review + 理由"仅标题信息不足"，不凭标题强行判定 |
| 计数不闭合 | audit FAIL → 逐阶段对账修复后再交付 |
| 预印本vs正式版 | 去重时保留两者关联（version_of 字段），正式版优先 |
| 预算不足 | protocol/dedup/screen JSON 先落盘，复核可 partial |

## 资源清单

- `scripts/screening_engine.py` — 协议/筛选/多源去重/计数审计（确定性引擎）
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/screening-rules.md` — 纳排规则、理由码表、PRISMA 计数规范
- `templates/result.schema.json`、`templates/criteria-table.json`
- `examples/minimal-example.md` — 示例（非正式案例结果）
- `README.md`

## 预算红线

64 次模型请求 / 900 秒 / 单响应 16384 token。协议骨架/去重/逐条筛选/审计恒为 0 请求；模型仅做 pending 复核与边界判定（≤6 次）。过 60% 时间冻结：protocol/dedup/screen 先落盘 status=partial。