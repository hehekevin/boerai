---
name: paper-to-slides
description: "Convert a paper into a presentable academic deck: extract the contribution storyline (not paragraph order), map every slide to specific figures/tables/sections with original numbering and units, generate notes that add value beyond slide text, and deliver an editable PPTX verified by real rendered previews. Use when: a case asks to turn a specific paper into slides within a template/slide-count limit. NOT for: copying abstract/paragraphs into text boxes, presenting schematic figures as experimental data, or notes that merely repeat the slide."
---

# 论文转学术 PPT：主线一致、页页可溯、打开能讲

面向"论文 → 可讲、可核验、可编辑 PPT"的转换任务。转换是结构重写不是切块：引擎强制每页挂论文定位、数字单位不改写、备注不复读；交付可编辑 PPTX 与真实渲染预览，他人按记录可复跑同一版式。

## 何时使用
* 用例给出一篇论文（+ 模板/页数上限/软件版本），要求产出主线成立、页序可讲的演示稿。
* 判定标准：主线与论文自身贡献一致；每页内容回溯到具体图/表/节/页码；成品在指定环境正常打开、播放、编辑。

**不适用**：论文精读结论生成、科研绘图美化、文字润色。

## 输入
`/input/case.json`（先用 probe 读真实键）、`/input/task.md`、`/input/**`（论文 PDF/文本、图表文件、模板、页数与场合约束等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ 可编辑 deck.pptx + 页级金标准（证据映射）+ 渲染预览（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"   # 论文抽成带页码定位的文本块
# —— 本题处理步骤（见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact slides=$WORK/deck.pptx --artifact png=$WORK/preview \
    --artifact provenance=$WORK/deck_check.json --artifact report=$WORK/build.json
```

**第 1 步 主线提取。** 从抽取文本整理 `sources.json`（loc 到节/页）；`structcheck` 抽"问题—做法—关键证据—结论"链，区分主结论与支撑细节，防止按段落顺序搬运。

**第 2 步 页结构与信息分层。** `outline.json`：每页一个 claim；长段落改写成可讲短语（≤6 条/页，单条 ≤60 字）；每页 role 标注叙事角色。

**第 3 步 图表引用与证据保留。** 每页 evidence 带：论文图/表/公式编号、单位、图注条件、loc 与 quote 原文；明确"重绘"与"只能引用原图"两清单，示意图绝不当实验数据。

**第 4 步 讲解备注。** 备注写过渡、强调点与被问时的补充证据，禁止复读页面文字（validate 机械拦截）。

**第 5 步 校验 + 生成 + 预览。** `deck validate --slide-limit N` → `deck build` → matplotlib PNG + soffice PDF（在则导）；`inspect_pptx` 回读确认文本框携带大纲文字、zip 合法。模板占位符不足时兜底版式并如实标注。

## 本题判据对齐（题面"三件事"）
1. **主线与论文贡献一致，非段落搬运** → structcheck 论证链先行，role 字段记录每页叙事角色。
2. **每页回溯到论文图/表/节/页码** → deck validate：evidence quote 子串 + 数字/单位字面一致。
3. **指定模板/软件下可打开播放编辑，可复跑** → 可编辑 PPTX + inspect 回读 + 真实 PDF/PNG 预览 + build.json 记录生成路径。

## 交付物
* `deck.pptx`、`outline.json`（页级金标准）、`deck_check.json`、`preview/`（PNG + PDF 若可用）、`struct.json`、`build.json`。

## 证据与审计规则
* 数值与单位在搬运中不得改写；validate 逐页数字字面比对。
* 图表张冠李戴为零容忍：图号必须与 evidence.loc 一致，引用不存在图号即失败。
* 备注必须提供页面外信息（过渡/强调/备答），复读即打回。
* 换机/导出风险以真实渲染记录为准，不接受"应该没问题"。

## 异常处理
| 情况 | 处置 |
|---|---|
| 图表无法提取/公式为图片 | 引用编号+图注文字占位，uncertainty 注明 |
| PDF 加密/抽取失败 | extract 记录原因，status=failed 或 partial |
| 模板占位符不足 | 兜底版式 + build.json 标注，不静默覆盖模板 |
| 页数超限 | 按主线重要性砍页，记录取舍 |
| 字体缺失 | 预览如实呈现回退效果，partial |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：9 个引擎模块 demo（deck demo 断言合法 zip、slide XML 文本回读、真实预览）+ 一次端到端。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Writing/ppt-c7b80f0d/v2
