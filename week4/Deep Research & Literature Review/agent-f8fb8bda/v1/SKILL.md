---
name: deep-research-agent-forge
description: 深度研究Agent：问题拆解成可分配子问题清单、检索规划（顺序/来源/停止/并行）、工具编排（检索/抓取/解析/抽取/计算留痕+失败重试+中间产物复用）。
---

# deep-research-agent-forge

## 核心原则（不可违反）
1. **题拆解**：研究对象/机制/方法/时间/比较/证据要求→结构化可分配子问题清单（question_decompose --decompose）。
2. **索规划**：子问题检索顺序/来源范围/停止条件；前置vs并行；减少重复检索与无边际收益追加（iter_loop --stop）。
3. **具调用**：检索/抓取/解析/抽取/计算编排——每步输入参数/返回结果/失败重试留痕；中间产物可被下一步复用（sw_agent --plan）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 拆解（0请求）：`python scripts/question_decompose.py --decompose "<问题>"`
### 阶段2 检索规划与迭代（0请求）：`python scripts/iter_loop.py --ledger/--stop`
### 阶段3 工具编排（0请求）：`python scripts/sw_agent.py --plan steps.json`
### 阶段4 成文（2-3请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/deep-research-agent-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 工具失败 | 重试留痕+降级 |
| 子问题无法检索 | gaps 声明 |
| 边际收益趋零 | 停止判据触发 |

## 资源清单
scripts：question_decompose.py, iter_loop.py, sw_agent.py, search_audit.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。