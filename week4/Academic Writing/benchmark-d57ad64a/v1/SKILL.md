---
name: writing-bench-forge
description: 题目输入充分性（双评分员同判）、参考答案覆盖合法变体、评分锚点可观察、复跑可复现。
---

# writing-bench-forge

## 核心原则（不可违反）
1. **判得动**：输入材料/指令/格式要求/必需要点齐备——两名评分员不商量能判出同一结论。
2. **站得住**：参考答案覆盖合法写法变体；不可接受错误与可接受差异分开——不只认一篇范文。
3. **打得齐**：评分锚点写成可观察现象；分歧集中在少数判据上。
4. **可复现**：相同输入/条件/权限复跑结论可解释一致。
5. **复用 bench_engine**：validate-card/score/panel 三子命令（0/1/2记分+争议标记）。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 题卡校验（0请求）：`python scripts/bench_engine.py --validate-card card.json`
### 阶段2 评分（0请求）：`python scripts/bench_engine.py --score rubric.json outputs.json`
### 阶段3 面板（0请求）：`python scripts/bench_engine.py --panel results.json`
### 阶段4 成文（1请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/writing-bench-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 规则不可机械判定 | 转人工流程声明 |
| 1分争议 | 人工复核队列 |
| 复跑波动 | 记录+解释 |

## 资源清单
scripts：bench_engine.py + inspect_case + validate_result；references/rules.md；templates/result.schema.json；examples；README。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。