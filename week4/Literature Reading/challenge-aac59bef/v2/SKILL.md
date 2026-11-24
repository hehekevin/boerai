---
name: web-paper-translation-alignment
description: "Turn a web paper page into clean main text + segment-aligned Chinese translation + source manifest: rule-based main-text extraction with paywall/nav-page signals, per-segment alignment bookkeeping, terminology-table consistency enforcement, and fetch provenance (URL, fetched_at, content hash). Use when: a case provides page snapshots or live pages and requires faithful per-paragraph translation that can be traced back to the original page position. NOT for: novelty assessment, review writing, publication-grade polishing, or bypassing paywalls/logins."
---

# 网页文献阅读与翻译：干净正文、逐段对齐、术语一致、来源可回

聚焦方向：**正文识别 + 术语一致性 + 来源保留**。浏览器/抓取动作由 Agent 按任务说明完成；引擎负责落盘后的确定性部分：正文切分与"抓错页"信号、段落对齐簿记、术语表强制一致、抓取轨迹清单——译文逐段对得上原文、每段回得到原始页面位置。

## 何时使用
* 用例给定网页论文（快照 HTML 或实时页面），要求抓正文、逐段翻译并保留来源。
* 判定标准：抓的是正文而非摘要页/导航页；译文忠实不漏不补；术语全文一致；可回溯。

**不适用**：论文创新性评价、领域综述、实验复现、出版级润色、绕过登录/付费墙。

## 输入
`/input/case.json`、`/input/task.md`、`/input/**`（页面 HTML 快照、术语表、翻译任务说明）。实时页面由 Agent 用浏览器工具抓取后落盘到 $WORK 再处理；引擎不联网。

## 输出（写入 /app/output）
`result.json` + `main_text.json`（正文段落+信号）+ `glossary.json`（术语表）+ `alignment.json`（逐段对齐+译文）+ `fetch_manifest.json`（URL/时间/哈希轨迹）+ `translation.md`（成品译文）+ `terms_report.json`。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
```

**第 1 步 抓取落盘。** 按任务说明访问页面，把最终渲染的 HTML 存 `$WORK/page_*.html`，记录 URL 与抓取时间。登录/付费墙/动态加载失败 → 停止并在 uncertainty 说明，不得拿摘要页充数。

**第 2 步 正文切分。**
```bash
python -m lrkit.webtext extract "$WORK/page_1.html" "$WORK/main_text.json" "https://<原文URL>"
```
引擎去掉导航/广告/参考文献/相关推荐，保留章节标题与段落顺序，并给"无段落/密度低"信号——**有信号即视为抓错页**，回到第 1 步换抓取方式，不得硬翻。

**第 3 步 建术语表。** 从任务材料与正文整理 `glossary.json`：`[{source, target, note?}]`；一词多译必须注明适用条件：
```bash
python -m lrkit.terms glossary "$WORK/glossary.json"
```

**第 4 步 逐段翻译。** 按 segment 逐段翻译（Agent 语义工作），写 `alignment.json`：`[{seg_id, source_loc, source_text, translation, terms_applied[]}]`。漏译段标 `omitted:true` + reason；公式、上下标、数字、单位、作者与期刊信息原样保留，不补写原文没有的内容。

**第 5 步 对齐与术语核验。**
```bash
python -m lrkit.terms align "$WORK/glossary.json" "$WORK/alignment.json" "$WORK/source_locs.json" "$WORK/align_report.json"
python -m lrkit.terms terms  "$WORK/glossary.json" "$WORK/alignment.json" "$WORK/terms_report.json"
```
align 校验：每段源文出现且只出现一次、译文数字不超出源段数字（防补写）；terms 校验：源段出现术语表词时译文必须使用术语表译法。

**第 6 步 抓取清单与交付。**
```bash
python -m lrkit.webtext manifest "$WORK/pages.json" "$WORK/fetch_manifest.json"
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status success \
  --artifact document="$WORK/translation.md" --artifact data="$WORK/alignment.json"
```

## 本题判据对齐（题面"三件事" → 引擎机制）
1. **抓下来的正文是否就是论文正文** → `webtext.extract` 的导航/广告/参考文献剔除 + "摘要页/目录页/付费墙页"信号；有信号不许进入翻译。
2. **译文是否逐段对得上原文** → `terms.check_alignment`：源段全覆盖、不重复、漏译必须标 omitted+reason；译文数字必须来自源段（补写即失败）。
3. **读者能否凭交付物回到原始页面核对** → `fetch_manifest.json` 登记 URL+抓取时间+内容哈希（HTTP 快照与实时页面分开登记版本）；alignment 中每段带 source_loc 锚点。
4. **术语一致性** → `terms.check_terms` 全文扫描：术语表词出现处译法不一致即列出 seg_id 与期望译法。

## 交付物
* `translation.md`（逐段对照译文）、`main_text.json`、`alignment.json`、`glossary.json`、`fetch_manifest.json`、`terms_report.json`/`align_report.json`。

## 证据与审计规则
* 译文忠实原文：不漏译（omitted 必须给原因）、不补写（数字防幻觉由引擎强制）、术语一致。
* 公式与上下标按原文结构保留（LaTeX 或 Unicode），拆散视为缺陷。
* HTTP 快照与实时页面是不同版本，fetch_manifest 分开登记。
* 抓取中断/超时/改版：记录到 fetch_manifest signals 与 uncertainty，说明已拿到/缺失的部分。
* 段落锚点 = main_text.json 的 seg_id/顺序号，人工抽查逐段可对。

## 异常处理
| 情况 | 处置 |
|---|---|
| 付费墙/登录失效 | 停止，uncertainty 说明权限边界，不抓摘要页冒充 |
| 页面改版/动态加载失败 | fetch_manifest 记信号；重试一次仍失败则 status=partial |
| 正文密度信号（疑似抓错页） | 回到抓取步骤换方式；禁止直接翻译 |
| 翻译中断 | 已译段落保留，未译段标 omitted+reason，status=partial |
| 段落错位（译文对不上源段） | align 校验失败 → 重排 alignment，不得带错交付 |
| 术语冲突（一词多译） | glossary 加 note 注明语境；引擎放行但不消除冲突记录 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：webtext demo 演示正文切分（剔除导航/广告/参考文献、识别纯导航页），terms demo 演示术语一致与数字防补写。示例 HTML 与术语均为编造占位。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Literature%20Reading/challenge-aac59bef/v2
