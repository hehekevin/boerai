---
name: sw-agent-forge
description: 科研软件操作Agent：状态步骤序列（前置条件+完成判据+状态快照）、任务到参数映射（单位换算/默认值陷阱/配置版本/可回指）、权限边界（不足即提示替代不重试）、导入导出验证（重开+复算）。
---

# sw-agent-forge

## 核心原则（不可违反）
1. **态管理**：导入/设置/运行/导出/检查组织成有前置条件+完成判据的步骤序列；每步开始/结束记录软件状态。
2. **正确性**：任务要求→软件参数映射；单位换算留公式、默认值陷阱显式、配置版本差异记录、参数可回指可核对（sw_agent --params）。
3. **号边界**：许可证/账号/写权限/插件授权前置检查；不足→明确提示+可行替代，**不反复重试**（sw_agent --gates）。
4. **与导出**：输入正确读取/中间结果正确挂接/导出格式字段符合下游；导出文件可重新打开和复算（sw_agent --iocheck）。
5. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 步骤规划（0请求）：`python scripts/sw_agent.py --plan steps.json`
### 阶段2 参数映射（0请求）：`python scripts/sw_agent.py --params task.json params.json`
### 阶段3 权限门（0请求）：`python scripts/sw_agent.py --gates env.json`
### 阶段4 导入导出验证（0请求）：`python scripts/sw_agent.py --iocheck io.json`
### 阶段5 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/sw-agent-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 权限不足 | 提示+替代，不重试 |
| 参数单位不符 | 换算公式留痕 |
| 导出无法重开 | FAIL 定位导出步骤 |

## 资源清单
scripts：sw_agent.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。