---
name: academic-deck-builder
description: "Generate and iteratively edit academic slide decks from papers/materials: outline-first page planning, per-slide evidence binding, deterministic editable PPTX output with speaker notes, real rendered PNG/PDF previews, and versioned iteration with rollback. Use when: a case asks to produce or revise an editable academic presentation with a fixed template/audience/slide count and traceable content. NOT for: fabricating figures or numbers, filling slides with whole paper paragraphs, or claiming a rendered preview that was never produced."
---

# 学术 PPT 生成与编辑：大纲先行、证据挂页、真渲染预览

面向"页面生成、内容编辑、图表插入、演示稿迭代"任务。铁律两条：**交付可编辑的 PPTX 源文件**（不是图片拼的伪 PPT），**附真实渲染预览**（LibreOffice 导 PDF / matplotlib 逐页 PNG；环境不支持就如实写 unavailable）。Agent 负责内容取舍，引擎负责证据绑定、版式约束、生成与渲染验证。

## 何时使用
* 用例给出论文/材料 + 模板/页数/受众约束，要求生成或多轮修改一份学术演示稿。
* 判定标准：数字图表与原文一致；模板约束不被破坏；多轮迭代可比对可回退；导出件真实可开。

**不适用**：凭空生成数据曲线；整段粘贴论文；伪造预览图。

## 输入
`/input/case.json`（先用 probe 读真实键）、`/input/task.md`、`/input/**`（论文、图表、模板/母版、既有 deck、修改指令等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ **可编辑 deck.pptx** + **真实预览（PDF/PNG）** + 页级证据映射与版本记录（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 本题处理步骤（见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact slides=$WORK/deck.pptx --artifact png=$WORK/preview \
    --artifact provenance=$WORK/deck_check.json --artifact data=$WORK/versions.json
```

**第 1 步 约束冻结。** `goal.json`：受众、时长、页数上限、模板约束（母版/占位符/页脚规则）、可重绘/只能引用的图表清单。

**第 2 步 页级大纲。** `outline.json`：每页唯一 claim、要点（≤6 条/页，单条 ≤60 字）、备注（不复读页面）、evidence（图/表/节定位 + quote 原文）。

**第 3 步 校验。** `python "$SKILL/run.py" deck validate $WORK/outline.json $WORK/sources.json $WORK/deck_check.json --slide-limit N`：页面数字必须字面出现在本页证据；content 页缺证据、备注复读、超页数一律拒收。

**第 4 步 生成 + 真预览。** `python "$SKILL/run.py" deck build $WORK/outline.json $WORK/deck.pptx --preview $WORK/preview`：
- 可编辑性：python-pptx 可用则用之（占位符继承），不可用则纯 zip OpenXML 写出器（`build.json` 如实记录 writer 与 fallback 原因）；
- 预览：matplotlib 逐页 PNG；soffice 在则 `pptx→pdf` 实测导出（字体替换/图片丢失写入报告）；
- 机械回读：`inspect_pptx` 验证 zip 合法、slide XML 齐全、文本框确实带大纲文字。

**第 5 步 多轮迭代。** 修改指令拆成页级操作，版本落盘 `versions.json`（每轮 outline 哈希 + 改了哪页 + 原因）；改坏的版本可按 outline 快照回退重生成。

## 本题判据对齐（题面评分关注点）
1. **数字/图注/引用与原文一致，不凭印象取整** → deck validate 数字字面一致性 + evidence quote 子串校验。
2. **模板约束与导出不塌** → goal.json 冻结模板约束；build 如实记录 writer；soffice 真实导出验证。
3. **迭代可比对可回退** → versions.json 每轮快照 + 原因；旧 outline 可重生成同一版。
4. **可打开、播放、编辑并复核** → inspect_pptx 机械回读 + PNG/PDF 预览随附。

## 交付物
* `deck.pptx`（可编辑源文件）、`preview/`（逐页 PNG；有 LibreOffice 时含 PDF）、`outline.json`、`deck_check.json`、`build.json`（writer/预览可用性）、`versions.json`。

## 证据与审计规则
* 示意图不得当实验数据展示；只能引用的图在 evidence.loc 标"原图引用"。
* 任何预览不可用的环境必须在 build.json/result.json 写明，不得以文字描述冒充。
* 每轮修改留痕；交付版必须是被显式标记的版本。
* 页面文字改动后重跑 deck validate（数字绑定可能失效）。

## 异常处理
| 情况 | 处置 |
|---|---|
| 论文缺图/位图无法取数 | 只引用图号图注，uncertainty 注明不重绘 |
| 模板槽位不足 | 纯 zip 固定版式兜底，build.json 标注未继承母版 |
| 文本溢出风险 | validate 报 bullet_too_long；压缩要点而非缩字号硬塞 |
| 字体缺失/导出失败 | render_pdf 返回 failed+原因 → uncertainty，partial |
| 页数超限 | 按 goal.json 砍页并记录取舍，不静默超页 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：9 个引擎模块 demo（deck demo 断言：输出为含 [Content_Types].xml 与各 slide XML 的合法 zip、文本框携带大纲文字、PNG/PDF 预览真实生成）+ 一次端到端。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Writing/ppt-6ad93034/v2
