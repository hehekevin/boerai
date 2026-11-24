---
name: academic-deck-pipeline
description: "End-to-end academic presentation pipeline: extract the storyline from fixed materials, plan pages with per-slide evidence mapping and separated speaker notes, build an editable PPTX deterministically, and attach real rendered PDF/PNG previews with build provenance. Use when: a case anywhere in the academic-PPT area asks to turn papers/data/logic into a clear, checkable, presentable deck. NOT for: information-dump slides without a storyline, unverifiable claims about rendering, or decks that cannot be edited after delivery."
---

# 学术 PPT 领域总课题：组织页面，也保留证据映射

面向学术 PPT 全领域通用任务。统一链路：材料抽取 → 主线提取 → 页级大纲（证据挂页）→ 校验 → 可编辑 PPTX → 真实渲染预览 → 结构化结果。确定性簿记在引擎，取舍与表达在 Agent；每一步落盘，他人可复跑。

## 何时使用
* 用例要求把论文、数据和研究逻辑转化为清晰演示结构（页数/受众/模板约束可选）。
* 判定标准：重点突出不堆叠；图表与结论一致；模板适配与导出可核验；拿到文件即可放映。

**不适用**：无来源的内容堆砌；跳过预览直接宣称"版式没问题"。

## 输入
`/input/case.json`（先用 probe 读真实键）、`/input/task.md`、`/input/**`（论文/数据/图表/模板/既有 deck 等，按题面实际为准）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段）+ 可编辑演示文件 + 页级证据映射 + 渲染与版本记录（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# —— 通用六步（按题面裁剪，见下）——
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact slides=$WORK/deck.pptx --artifact png=$WORK/preview \
    --artifact provenance=$WORK/deck_check.json --artifact report=$WORK/build.json
```

**第 1 步 主线提取。** 用 `structcheck` 从材料抽论断-证据链，确认结论有支撑；形成叙事骨架（问题—方法—结果—结论），主结论与支撑细节分层。

**第 2 步 页级规划。** `outline.json`：每页唯一 claim + 要点 + 备注（不复读）+ evidence（loc+quote）；页数/受众约束写入并在 validate 机械执行。

**第 3 步 校验。** `deck validate`：证据子串、数字字面一致、要点上限、备注分离、页数上限——任何一项不过不进入生成。

**第 4 步 生成可编辑 PPTX。** `deck build`：python-pptx 优先、纯 zip 写出器兜底（build.json 如实记录 writer）；`inspect_pptx` 机械回读验证 zip 合法、slide XML 齐全、文本框带大纲文字。

**第 5 步 真实渲染预览。** matplotlib 逐页 PNG；soffice 在则导 PDF 实测；不可用环境如实写 unavailable——**可编辑源文件与真实预览必须同时交付**。

**第 6 步 版本与边界。** `versions.json` 记录每轮改动；材料缺口用【材料不足】占位页并写 uncertainty，status 相应降级。

## 本题判据对齐（题面通用评分点）
1. **完成核心任务并交付可用成果** → 可编辑 PPTX + 预览 + 证据映射三件套齐备。
2. **事实/数据/引用准确** → deck validate 数字与证据强制绑定；claims 同一套规则管页面文字。
3. **覆盖关键要素** → 主线/页结构/图表引用/讲解逻辑/模板约束/导出渲染六类逐项有产物。
4. **可追溯** → probe 输入哈希 + outline/deck_check/build/versions 全量留痕。

## 交付物
* `deck.pptx`、`preview/`（PNG + PDF 若可用）、`outline.json`、`deck_check.json`、`build.json`、`struct.json`、`versions.json`。

## 证据与审计规则
* 页面论断必须挂源材料定位；数字字面一致，推导数字走 computed 登记。
* 备注与页面文字分离生成；重复即校验失败。
* 预览只信真实渲染产物；环境不支持时如实报告而非描述性替代。
* 多轮修改全部进 versions.json，交付版显式标记。

## 异常处理
| 情况 | 处置 |
|---|---|
| 材料撑不起某页 | 删页或【材料不足】占位 + uncertainty |
| 模板约束与内容冲突 | 列冲突项，记录取舍，优先保证据完整性 |
| 页数超限 | 按受众/时长砍页并记录 |
| 字体缺失/导出失败 | 如实记录，交付源文件，partial |
| 公式/图为图片无法提取 | 引用编号与图注文字，注明不可重绘 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：9 个引擎模块 demo + 一次端到端（合成 case → probe → extract → claims/deck → emit → result.json，含 PPTX 构建与预览）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Academic%20Writing/ppt-9508e25f/v2
