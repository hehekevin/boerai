---
name: page-citation-capture
description: "Capture citation records and re-verifiable anchors from retained scientific-source HTML snapshots: citation-meta extraction with per-field provenance, reference-list contamination guards, element-id/text-fingerprint anchors, dedupe into a library file. Use when: a case provides source HTML snapshots and asks for citation collection and page localization with a reviewable trail. NOT for: live browsing, cross-origin iframes, login flows, or harvesting reference-list entries as the current paper."
---

# 学术浏览器插件：完成操作，也保留过程轨迹

面向"从组织方留存的科研来源 HTML 快照中抽取当前论文的规范引用字段与可复现定位锚点"任务。本技能在**离线快照**上工作（与在线出版商页面严格区分，每条记录都标注来源边界）：`htmlsnap` 解析 citation/DC/og 元数据并逐字段留出处，`identity`/`normalize` 做规范记录与去重，`kb` 支撑证据回链。**经典失效模式——把参考文献列表/相关推荐当作当前论文——由引擎结构性防住：只取当前页 meta 标签，页面含文献列表时输出显式警告。**

## 何时使用
* 用例提供源 HTML 快照（出版商详情页/预印本页），要求收集引用条目、定位章节/图表、写入本地文献库文件。
* 判定标准（题面原文）：任务是否在真实页面上跑通并交出可用的产物；产物里的字段和位置能否与原文逐项对上；整个过程能否被别人按记录复跑并解释失败原因。

**不适用**：在线浏览与登录、跨域 iframe 抓取、页面改版后的选择器猜测、把快照当成实时页面。

## 输入
`/input/case.json`（结构不固定，先用 probe 读真实键）、`/input/task.md`、`/input/**`（材料：HTML 快照、字段要求、目标库文件等）。

## 输出（写入 /app/output）
`result.json`（含 `case_id` 与全部 `output_contract` 字段、status、sources、uncertainty、changes）+ 本题交付物（见"交付物"）。

## 工作流

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}"; export WORK=/app/work; export OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
python "$SKILL/run.py" htmlsnap parse /input/<快照>.html > $WORK/snap_<n>.json
python "$SKILL/run.py" htmlsnap anchor /input/<快照>.html "<章节id或图表号或文本指纹>"
# normalize / identity 去重入库（见下）
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status <success|partial> \
    --artifact report=$WORK/capture_report.md --artifact data=$WORK/library.json
```

**第 1 步 确认快照边界。** probe 确认快照文件与 sha256；每条抽取记录带 `scope_note`（离线快照解析，无实时访问）与快照哈希，与任何在线来源区分。

**第 2 步 字段抽取。** `htmlsnap parse`：从 `citation_*`/DC/og meta 与 `<title>` 取当前论文字段，`provenance` 记录每字段来自哪个标签；缺标题/缺 DOI 输出显式 warning；检测到 reference-list 结构时输出 `reference_list_present` 警告且绝不把其条目混入当前论文记录。

**第 3 步 定位锚点。** `htmlsnap anchor`：按元素 id（章节/图表）或文本指纹在快照中定位，返回行号与上下文——第三方按（文件 sha256 + 行号 + 指纹）可独立复核。

**第 4 步 规范化与去重入库。** `normalize` 映射到规范记录（作者转 Family, Given、年份抽取、DOI 归一）；`identity` 按 DOI/标题/作者年规则去重合并，合并规则与冲突逐条留审计，写入 `library.json`。

**第 5 步 汇总。** `capture_report.md`：每页快照的字段表（值+出处标签）、锚点表（目标+行号+核验状态）、去重审计、warning 清单；无法判断的字段进 uncertainty。

## 本题判据对齐（题面原文的"三件事"）
1. **"在真实页面上跑通并交出可用的产物"** → 产物为可入库的 `library.json`（规范字段+去重审计）与可回到原文的锚点表。
2. **"字段和位置能否与原文逐项对上"** → 每字段带 meta 出处标签，每锚点带 sha256+行号+上下文，`anchor` 可重复执行复核。
3. **"能否被别人按记录复跑并解释失败原因"** → 快照哈希冻结输入；缺字段=显式 warning 而非编值；失败原因（缺标题/缺 DOI/锚点缺失）逐条入账。

## 交付物
* `snap_<n>.json`（每页快照：record+provenance+warnings）、`anchors.json`、`library.json`（去重后规范库）、`capture_report.md`、`result.json`

## 证据与审计规则
* 字段只能来自当前页 meta/title 证据；材料没有就留空 + warning + uncertainty，不猜。
* 参考文献列表、相关推荐、侧栏内容一律不入当前论文记录（引擎结构性排除 + 警告计数）。
* DOI 归一后入库；`dc.identifier` 非 DOI 形式时跳过并在 provenance 缺失中体现。
* 快照与实时页面的边界写入每条记录的 scope_note；不输出"已在线验证"这类无法支撑的话。

## 异常处理
| 情况 | 处置 |
|---|---|
| 快照缺 citation meta | 回退 `<title>`；仍缺则 warning + uncertainty，status=partial |
| 页面含参考文献列表 | 显式 warning；仅 meta 字段入库 |
| 锚点不存在 | `found:false` + reason；不输出无法复核的定位 |
| DOI 格式非法/非 DOI 标识 | 跳过该值并记录，禁止伪造 DOI |
| 多条目合并字段冲突 | identity field_conflicts 留痕，保留先值 |
| 快照哈希与任务单不符 | uncertainty 记录，提示可能被替换 |

## 最小示例（合成数据，非正式案例结果）
`python "$SKILL/selftest.py"`：11 个引擎模块 demo（htmlsnap demo 内含"参考文献列表防误取"断言）+ 一次端到端（合成 case → probe → extract → 模块命令 → emit → result.json）。示例仅为接口演示。

## 公开作品
https://github.com/hehekevin/boerai/tree/main/week4/Research%20Library/challenge-5047f57f/v2
