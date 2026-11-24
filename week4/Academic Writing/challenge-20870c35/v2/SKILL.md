---
name: talk-page-planner
description: "Organize fixed paper/materials into a presentable academic talk: audience-aware page plan with one claim per slide, per-page evidence mapping back to source figures/tables/sections, speaker notes separated from slide text, editable PPTX plus real rendered previews. Use when: a case asks to structure a paper into slides for a given audience/time/slide count with traceable evidence. NOT for: reading the paper to draw scientific conclusions from scratch, producing graphics/data visualizations, or polishing prose style."
---

# 学术汇报内容组织：每页一个主张，每条主张挂证据

面向"把固定论文/研究材料组织成结构清楚、证据可追溯、可编辑、符合模板要求的汇报产物"。Agent 负责取舍与叙事判断，引擎负责页级证据绑定、备注分离检查、PPTX 生成与渲染验证——每页的论断必须能指回源材料的具体位置。

## 何时使用
* 用例给出论文/材料 + 听众 + 时长 + 页数上限 + 模板约束，要求产出可讲、可编辑的汇报文件。
* 判定标准：页面论断能在源材料找到对应位置；叙事顺序服务于听众与时长；取舍过程可被复核。

**不适用**：论文精读结论生成、科研绘图素材生产、文字润色。

## 输入
`/input/case.json`（先用 probe 读真实键）、`/input/task.md`、`/input/**`（论文 PDF/文本、图表、模板文件、既有 deck 等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ 可编辑演示文件（.pptx）、页级证据映射、渲染预览与导出记录（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"   # 论文/图表抽成带定位的文本块
# —— 本题处理步骤（见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact slides=$WORK/deck.pptx --artifact provenance=$WORK/deck_check.json \
    --artifact report=$WORK/build_report.json
```

**第 1 步 定目标与听众。** 把"这次汇报要达成什么"写成 `goal.json`：听众、时长、页数上限、结论强度；据此确定叙事骨架（问题—方法—结果—结论）与取舍比例。

**第 2 步 抽主线。** 从抽取文本整理 `sources.json`（带 loc 定位）；用 `structcheck` 抽论断-证据链，确认每个结论挂了支撑，避免把摘要逐段搬页。

**第 3 步 页级大纲。** 写 `outline.json`：每页唯一 claim、≤6 条要点、讲解备注（不得复读页面）、evidence（source_id + loc + quote 原文）。

**第 4 步 校验。** `python "$SKILL/run.py" deck validate $WORK/outline.json $WORK/sources.json $WORK/deck_check.json --slide-limit N`：页面数字必须字面出现在本页证据引文中；缺证据的 content 页直接拒收。

**第 5 步 生成与渲染。** `python "$SKILL/run.py" deck build $WORK/outline.json $WORK/deck.pptx --preview $WORK/preview`：优先生成可编辑 PPTX（python-pptx 不可用则纯 zip 写出器，build_report 如实记录），并产 PNG 版式预览；有 LibreOffice 则导 PDF 实测渲染，字体替换/导出问题写入 uncertainty。

**第 6 步 问答准备。** 预判机制/数据/对照/局限追问，在 `qa.json` 按"问题→引用页→备用页→口径要点"落盘。

## 本题判据对齐（题面"三件事"）
1. **每个论断能在源材料找到对应位置** → deck validate 强制每页 evidence.quote 为来源子串，页面数字字面一致。
2. **叙事顺序服务听众与时长** → goal.json 先定听众/时长/页数，slide_limit 机械执行，role 字段记录每页叙事角色。
3. **取舍过程可被他人复核** → outline/struct/deck_check/qa 全量落盘，build_report 记录生成路径与渲染结果。

## 交付物
* `deck.pptx`（可编辑）、`outline.json`、`deck_check.json`、`preview/`（PNG 逐页 + PDF 若可用）、`qa.json`、`build_report.json`。

## 证据与审计规则
* 页面数字必须字面出现在本页 evidence；推导数字走 claims 的 computed 登记。
* 备注缺失或与页面重复 → 校验失败，必须重写。
* 图表只能引用源材料定位（loc）；不得凭空生成曲线占位。
* 渲染不可用的环境如实报告 preview=unavailable，不得伪造预览图。

## 异常处理
| 情况 | 处置 |
|---|---|
| 论文缺图/图为位图无法取数 | evidence 只引用图号与图注文字，uncertainty 注明不可重绘 |
| 页数超限 | deck validate 报 slide_limit_exceeded；按 goal.json 砍页并记录取舍 |
| 模板占位符不足 | 用纯 zip 写出器的固定版式兜底，build_report 标注未继承母版 |
| 字体缺失/导出失败 | render_pdf 返回 failed+原因 → uncertainty，status 降 partial |
| 材料支撑不起某页主张 | 删页或改写为【材料不足】标注，不硬写 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：9 个引擎模块 demo（deck demo 断言 zip 合法性、slide XML 文字回读、PNG/PDF 预览）+ 一次端到端（合成 case → probe → extract → claims/deck → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Writing/challenge-20870c35/v2
