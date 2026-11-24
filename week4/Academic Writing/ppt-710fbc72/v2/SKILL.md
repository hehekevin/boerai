---
name: deck-template-conformance
description: "Fit academic content into a fixed slide template: parse master/layout/placeholder constraints into a checkable spec, keep every slide inside slot and typography rules, enforce deck-wide consistency (footer, numbering, font ladder), and verify the editable PPTX against real rendered PDF/PNG page by page. Use when: a case asks to apply a given template/master to deck content with batch consistency and export checks. NOT for: silently overriding master styles, shrinking fonts to unreadable sizes to force fit, or reporting template conformance without rendered evidence."
---

# 学术 PPT 模板与格式适配：真实套用、槽位内排版、整册一致、逐页可核对

面向模板套用/版式约束/字体颜色/图表适配/批量一致性任务，"导出渲染"作为横切关注点。引擎把模板约束抽成检查项，逐页机械核对；交付**可编辑 PPTX**与**真实渲染预览**（PDF/PNG），pptx 与导出件的一致性有记录可查。

## 何时使用
* 用例给出内容大纲/既有 deck + 指定模板（母版/版式/占位符/字体/页脚规则），要求整册套用并交付导出件。
* 判定标准：母版与版式继承真实发生；页内内容与源材料对得上；整册版式与导出结果可按记录复跑逐页核对。

**不适用**：覆盖母版样式假装套用；把字号压到不可读硬塞；只修封面和前三页。

## 输入
`/input/case.json`（先用 probe 读真实键）、`/input/task.md`、`/input/**`（模板 pptx/说明、论文材料、既有 deck、字体要求等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ 可编辑 deck.pptx + 逐页偏差记录 + 渲染预览与导出一致性报告（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 本题处理步骤（见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact slides=$WORK/deck.pptx --artifact png=$WORK/preview \
    --artifact report=$WORK/conformance.json --artifact provenance=$WORK/deck_check.json
```

**第 1 步 模板解析。** 从模板与规定整理 `tpl_spec.json`：版式清单与占位符、字号阶梯（标题/正文/图注）、配色与强调色、页脚页码规则、单页要点与字数上限——每条注明来源；解析不了的约束写入 uncertainty，不凭经验猜。

**第 2 步 内容装槽。** `outline.json` 按 tpl_spec 的槽位组织：标题进 claim，要点进 bullets（遵守条数/字数上限），图注与编号随 evidence.loc 保留。

**第 3 步 校验 + 生成。** `deck validate`（条数/字数/证据/页数）→ `deck build` 生成可编辑 PPTX；python-pptx 可用时占位符继承模板，否则纯 zip 写出器兜底并在 build.json 标注未继承母版的具体项。

**第 4 步 批量一致性巡检。** 逐页核对：标题位置、字号阶梯、页脚页码、留白规则一致（从 outline+build 记录机械比对）；整册输出 `conformance.json` 逐项 pass/fail。

**第 5 步 导出一致性。** soffice 导 PDF（在则导，不在则如实报告），逐页 PNG 预览与 pptx 文本回读对照：字体替换、图片丢失、备注错位全部记录到 conformance.json；任何"已符合"必须指到具体检查项。

## 本题判据对齐（题面"三件事"）
1. **模板被真实套用（继承关系可查）** → build.json 记录 writer 与母版继承情况；未继承项明示不掩饰。
2. **页内内容与源论文/图表对得上** → deck validate 证据 quote 子串 + 数字字面一致。
3. **版式与导出可按记录复跑逐页核对** → conformance.json 逐项 + 逐页 PNG/PDF + inspect_pptx 文本回读。

## 交付物
* `deck.pptx`（可编辑）、`tpl_spec.json`、`conformance.json`（批量一致性逐项）、`preview/`（PNG 逐页 + PDF 若可用）、`deck_check.json`、`build.json`。

## 证据与审计规则
* "已套用模板"必须能指出母版/版式/占位符级证据；否则写"固定版式兜底"。
* 字号/间距阶梯来自 tpl_spec，不允许为塞内容破坏阶梯。
* 图表等比缩放或裁切策略写入 outline 的 figure 字段；位图不假装矢量。
* 导出件与 pptx 的每处渲染差异都要落记录；无差异也要留验证日志。

## 异常处理
| 情况 | 处置 |
|---|---|
| 模板缺版式/占位符 | 兜底版式 + build.json 标注缺哪些槽位 |
| 文本框溢出 | 压缩要点/拆页；禁止缩字号硬塞，改动留痕 |
| 字体缺失 | 记录回退字体，预览中如实呈现，partial |
| 图表源文件失效 | 引用图号图注占位 + uncertainty，不伪造图 |
| 导出失败 | 记录 stderr，交付可编辑源文件，partial |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：9 个引擎模块 demo（deck demo 断言合法 zip、slide XML 文本回读、真实预览生成）+ 一次端到端。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Writing/ppt-710fbc72/v2
