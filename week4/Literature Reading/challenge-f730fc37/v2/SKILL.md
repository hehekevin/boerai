---
name: reading-session-ledger
description: "Reading-client MVP data layer: run the full loop open-locate-select&ask-annotate-export in one place, with every action recorded as a sequenced session entry whose anchors (selection, answer evidence, annotations) are verified verbatim against the document, and exported as a hand-over reading record with file hashes and version info. Use when: a case asks to perform reading tasks on a document (locate passages, ask questions on a selection, save annotations/conclusions, export the record) with reviewable operation paths. NOT for: GUI pixel rendering, OCR of scanned pages, or editing the source document."
---

# 阅读客户端：打开—定位—提问—批注—导出，一处闭环、锚点可核

聚焦方向：**选区问答 + 批注沉淀 + 阅读记录导出**的数据层 MVP。交互界面不是本赛题的可评分核心；本技能把阅读客户端的最小闭环做成可复核的会话簿记：每个动作一条 seq 记录，选区/答案/批注的锚点逐字核验，导出文件含全部锚点与版本信息——对话结束，记录还在。

## 何时使用
* 用例要求在文献上完成阅读任务：定位段落、基于选中文本提问、保存批注或结论、导出可交接记录。
* 判定标准：答案基于当前页面与选中文本、定位落到真实原文位置、批注锚点准确、操作路径可复核。

**不适用**：GUI 渲染效果评比、扫描件像素 OCR、修改源文件。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（文献文件、阅读任务工单：定位目标、问题、批注要求）。

## 输出（写入 /app/output）
`result.json` + `session.json`（顺序化阅读会话）+ `session_report.json`（闭环与锚点核验）+ `reading_record.json`（导出记录：锚点+哈希+版本）+ `annotations.json`（批注集合）+ `report.md`。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" blocks  --work "$WORK"
```

**第 1 步 打开（open）。** 记录文件、sha256、页数/块数到 session 第 1 条。物理页与印刷页不一致时，loc 统一用 extract 的 p.N（物理页），在报告中注明映射。

**第 2 步 定位（locate）。** 按工单要求定位：
```bash
python -m lrkit.reader locate "$WORK/blocks.json" keyword "<关键词>"
python -m lrkit.reader locate "$WORK/blocks.json" page p.3
```
跨栏排版已由 extract 的线性化文本处理；扫描件无文本层 → 记录信号并说明只能到页级。

**第 3 步 选区问答（ask）。** 以选中文本所在段落为上下文：session 记录 selection（loc+逐字 quote）、question、answer、evidence（loc+quote）。答案必须基于选中内容与文档，缺依据时写明而不是编造。

**第 4 步 批注保存（annotate）。** 批注/结论落成 `annotations.json` 并挂 session 记录：`{anno_id, loc, quote, kind, comment}`——批注与原文位置绑定，不与结论分离。

**第 5 步 闭环核验。**
```bash
python -m lrkit.reader validate "$WORK/session.json" "$WORK/blocks.json" "$WORK/session_report.json"
```
引擎检查：open 存在、seq 单调、每个 ask/annotate 的锚点逐字可核、ask 有答案文本且证据可核。

**第 6 步 导出（export）与交付。**
```bash
python -m lrkit.reader export "$WORK/session.json" "$WORK/reading_record.json"
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status success \
  --artifact data="$WORK/reading_record.json" --artifact report="$WORK/report.md"
```

## 本题判据对齐（题面"四个问题" → 引擎机制）
1. **串得起来** → open/locate/ask/annotate/export 五种动作在同一份 session.json 中按 seq 闭环；缺 open 或顺序破坏即核验失败——不存在"在多个工具间搬运"的空白段。
2. **对得上原文** → 选区 quote 与答案 evidence 逐字核验（`validate_session`）；答案无依据必须写明，引擎拒绝锚点错位的记录。
3. **留得下来** → 批注入 `annotations.json`、结论入 session、导出入 `reading_record.json`（含文件哈希与版本），回看按 loc+quote 复核。
4. **讲得清楚** → session 全量落盘 + session_report.json 校验结论；他人可按 seq 重放操作路径。

## 交付物
* `session.json`、`reading_record.json`、`annotations.json`、`session_report.json`、`report.md`（操作路径与锚点说明）。

## 证据与审计规则
* 每个 ask 的 selection 与 evidence 必须逐字存在于文档；锚点错位（如 0.87 写成 0.78）即失败。
* 批注与结论绑定保存；只保存文字不保存锚点视为未完成。
* 导出记录含文件 sha256 与材料版本，跨会话可核对。
* 物理页/印刷页差异、扫描件无文本层等降级情况写入报告与 uncertainty。
* 重复打开同一文件：以哈希识别为同一会话素材，不重复建档。

## 异常处理
| 情况 | 处置 |
|---|---|
| 扫描件无文本层 | locate 只能到页级，记录信号，status 降 partial |
| 加密/超大文件 | open 失败如实记录，uncertainty 说明 |
| 选区跨页 | 拆成两条 selection 分别核验并注明跨页 |
| 问答缺少依据 | answer 写明"材料未报告"，evidence 为空 + 说明 |
| 批注写入失败 | session 记录失败原因，可单独重试该 seq |
| 重复运行 | 幂等：同哈希文件+同 seq 记录，重放结果一致 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：reader demo 演示完整会话（open→locate→ask→annotate→export）与"锚点错位被抓出"反例。示例文档与数值均为编造占位。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Reading/challenge-f730fc37/v2
