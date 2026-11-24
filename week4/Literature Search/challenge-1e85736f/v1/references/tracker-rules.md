# 增量追踪规则（tracker-rules.md）

## 1. 水位与快照
baseline 冻结保存；current 快照即下次 baseline。任意增量可由 (baseline, current) 复算。

## 2. 去重键优先级
doi > arxiv_id > title_normalized。碰撞（同键多记录）→ 人工仲裁，不自动合并。

## 3. 时间窗规则
左闭右开 [from, to)；时区统一转换；补抓 backfill=true；回溯仅限明确指定窗口。漂移检查：与上次窗口比对重叠/间隙。

## 4. 幂等重试
fetch/query/dedup 幂等可重试；push/notify 非幂等需人工。重跑键集相同+推送层去重抑制二次推送。

## 5. 三类变更
new/updated/removed。removed（消失/撤稿）需人工核实原因。

## 6. 异常处置
见 SKILL.md 异常表。