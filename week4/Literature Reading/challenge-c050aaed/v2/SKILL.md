---
name: annotation-notes-pipeline
description: "Close the loop from reading annotations to a searchable knowledge store: extract highlights/underlines/margin/handwritten notes with verified anchors (file hash + page/block + verbatim quote), structure notes (question/method/conclusion/reuse/doubt) that must anchor to source text, link notes only with an explicit basis, and provide a search entry that returns traceable entries. Use when: a case provides annotated reading material and asks for annotation extraction, note structuring, knowledge linking and retrieval with reproducible records. NOT for: literature search, content judgement on paper quality, academic writing, or long-term archive governance."
---

# 阅读批注与知识沉淀：锚点不漂移，笔记有出处，关联有依据

聚焦方向：**批注锚点核验 + 笔记结构化 + 可解释关联**。批注离开原文件就丢失页码与上下文——本技能把每条批注、每条笔记论断绑定到逐字可核验的原文锚点；关联必须写依据，关键词重合不算数。Agent 负责语义提炼与关联判断，引擎负责锚点核验、类型保真与检索簿记。

## 何时使用
* 用例给出带高亮/划线/页边批注的阅读材料（PDF/文本/网页剪藏），要求抽取批注、结构化笔记、建立关联并支持检索。
* 判定标准：批注逐条回得到原文页与位置；笔记论断有原文支撑；沉淀条目可被真实问题检索到并按记录复跑。

**不适用**：文献检索、论文内容评价、学术写作、目录治理与长期归档制度。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（带批注的文件、批注导出、版本/别名说明）。

## 输出（写入 /app/output）
`result.json` + `annotations.json`（批注+锚点+类型+颜色）+ `notes.json`（结构化笔记）+ `links.json`（关联+依据）+ `notes_report.json`（引擎核验）+ `knowledge_base.md`（可检索沉淀库）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" blocks  --work "$WORK"
```

**第 1 步 批注盘点。** 从案例材料收集批注（或从批注导出文件解析），整理 `annotations.json`：`[{anno_id, file, file_sha256, loc: {page, block?}, kind: highlight|underline|margin|handwrite, color?, quote, comment?}]`。类型与颜色原样保留——黄色的既有含义不被抹平，四类批注不混为一类。

**第 2 步 锚点核验。**
```bash
python -m lrkit.notes validate "$WORK/annotations.json" "$WORK/blocks_by_file.json" "$WORK/anno_report.json"
```
每条 quote 必须逐字存在于所标文件所标页/段。锚点漂移（挂到相邻段落/错页）一律抓出；扫描件 OCR 置信度低的锚点在 note 标注并降 status。

**第 3 步 版本归并。** 同一文献多版本/重复下载的批注：按案例版本说明归并到同一文献 ID，注明各锚点来自哪个版本（版本串味会把批注拆散，归并依据落盘）。

**第 4 步 笔记结构化。** 每条批注/原文片段整理为 `notes.json`：`[{note_id, kind: question|method|conclusion|reuse|doubt, text, anchor, links[]}]`——笔记不是摘抄：text 是 Agent 的判断，anchor 是支撑它的原文片段，两者都必须存在。

**第 5 步 关联与核验。**
```bash
python -m lrkit.notes link  "$WORK/notes.json" "$WORK/link_candidates.json"
python -m lrkit.notes notes "$WORK/notes.json" "$WORK/annotations.json" "$WORK/blocks_by_file.json" "$WORK/notes_report.json"
```
引擎给出候选关联（共享 ≥2 个实词），Agent 确认并写 basis；无 basis 的关联被引擎拒绝。

**第 6 步 入库检索与交付。** knowledge_base.md 按主题/类型/来源组织；检索入口：
```bash
python -m lrkit.notes search "$WORK/notes.json" "<检索词>"
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status success \
  --artifact report="$WORK/knowledge_base.md" --artifact data="$WORK/notes.json"
```

## 本题判据对齐（题面"三件事" → 引擎机制）
1. **批注能否逐条回到原文的具体页与位置** → `validate_annotations`：file+页/段+逐字 quote 三环核验，漂移即 failed；文件哈希随批注落盘。
2. **笔记里的每条论断能否指到支撑它的原文片段** → `validate_notes`：无 anchor 或 anchor 核验不过的笔记不通过；批注↔笔记用 anno_id 对应。
3. **沉淀条目能否被真实问题检索到并复跑核对** → `search_notes` 返回带 anchor 的条目；全流程输入（哈希、脚本版本）落盘，复跑结果一致。
4. **类型与标签保真 / 控制过度连接** → kind 四选一枚举校验；关联必须带 basis，候选机制防止"共享一个术语就连成一片"。

## 交付物
* `annotations.json`、`notes.json`、`links.json`、`anno_report.json`/`notes_report.json`、`knowledge_base.md`。

## 证据与审计规则
* 批注 quote 逐字核验；OCR 低置信锚点显式标注，不当作已核验。
* 笔记 text 与 anchor 分工明确：判断与原文不混写。
* 关联必须写 basis（为什么这两条相关）；候选不等于关联。
* 版本归并写明依据；不确定归并的保持分列并说明。
* 人工改动追加进变更记录，保留 diff 语义（旧值→新值）。

## 异常处理
| 情况 | 处置 |
|---|---|
| 加密/损坏文件 | 该文件批注标 failed + 原因，status 降 partial |
| 无文本层扫描件 | 锚点只能到页级 + OCR 置信标注，诚实降级 |
| 批注来自旧版本 | 版本归并时注明，不 silent 挂到新版本 |
| 重复文件拆散批注 | 按哈希识别重复并归并，归并依据落盘 |
| 锚点核验失败 | 回原文重定位；找不到则标 drifted + 原因 |
| 检索召回不足/误召回 | 放宽 query 或 kind 重试，并在报告中说明 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：notes demo 演示锚点核验（含"锚点漂移被抓出"反例）、类型保真、候选关联与检索。示例批注与笔记均为编造占位。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Reading/challenge-c050aaed/v2
