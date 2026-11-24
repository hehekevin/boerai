---
name: recent-lit-tracker-forge
description: 最新文献发现与追踪。水位快照增量查询（只面向新增区间，不全量重扫），稳定去重键（doi/arxiv/标题归一化），固定时间窗防漂移（跨窗边界/补抓/回溯），幂等重试（重跑不产生二次推送），全量版本记录（可复算可追溯）。触发词：增量、水位、追踪、时间窗、幂等。
---

# recent-lit-tracker-forge — 最新文献发现与追踪

一句话：**水位定增量、快照定基线、窗口防漂移、重试保幂等、版本可复算。**

## 核心原则（不可违反）

1. **水位快照**：明确"上次看到哪里"——baseline 快照冻结保存；每次检索只面向新增区间，避免全量重扫和结果重复。
2. **去重键稳定**：doi > arxiv_id > 标题归一化（NFKC→去标点→压空白→小写）；处理大小写标点差异、DOI与arXiv并存、同文多源收录。
3. **时间窗固定**：左闭右开、时区固定、跨窗边界规则显式；补抓标记 backfill=true，回溯仅对明确指定窗口。
4. **重试幂等**：fetch/query/dedup 类事件可安全重跑（相同键集+推送层按去重键抑制二次）；push/notify 非幂等需人工确认。
5. **版本记录全量**：订阅配置、窗口、抓取时间、结果计数、去重键全量保留——任意一次增量可复算。
6. **三类变更分类**：new（新发现）/ updated（版本更新）/ removed（撤稿消失需人工核实）分别报告。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：增量对比（0请求）
```bash
python <SKILL_DIR>/scripts/increment_tracker.py --baseline <基线快照.json> <当前快照.json> > /app/work/increment.json
```

### 阶段 2：去重键检查（0请求）
```bash
python <SKILL_DIR>/scripts/increment_tracker.py --dedupkeys <当前快照.json> > /app/work/keys.json
```
碰撞记录（同键多记录）→ 人工仲裁队列。

### 阶段 3：时间窗规则（0请求）
```bash
python <SKILL_DIR>/scripts/increment_tracker.py --window 2026-11-18 2026-11-25 UTC+8
```

### 阶段 4：重试审计（0请求）
```bash
python <SKILL_DIR>/scripts/increment_tracker.py --retrylog <事件日志.json> > /app/work/retry.json
```

### 阶段 5：成文与交付（约2-3次模型请求 + 0请求）
模型按三类变更撰写追踪简报（区分新发现/版本更新/撤稿更正）；组装 result.json（合并 output_contract + case_id）。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/tracker-report.md --require "增量|increment|水位|watermark,去重|dedup|键|key,时间窗|window|边界,重试|retry|幂等" --names "increment,keys,window,retry"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 基线快照缺失 | 本次输出作为首个基线（全量=增量），gaps 声明 |
| 去重键碰撞 | 人工仲裁队列，不自动合并 |
| 来源改版字段缺失 | anomalies 记录，缺失字段不动 |
| 预算不足 | increment.json 先落盘 status=partial |

## 资源清单
- `scripts/increment_tracker.py` — 增量对比/去重键/时间窗/重试（确定性引擎）
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/tracker-rules.md`、`templates/result.schema.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。四子命令恒为0请求。过60%时间冻结。