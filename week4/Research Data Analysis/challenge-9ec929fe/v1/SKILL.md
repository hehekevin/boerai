---
name: codegen-forge
description: 科研代码生成与执行：代码生成（数据字典+任务→清洗统计可视化代码；字段对齐/口径显式/缺失异常策略可解释——不堆砌）、环境配置（依赖声明/版本锁定/包冲突/隔离；跨机器可装可跑；降级替代）、执行调试（真实数据跑通；路径/编码/类型/内存/超时；命令行日志退出状态留痕）。
---

# codegen-forge

## 核心原则（不可违反）
1. **码生成**：数据字典+任务描述→清洗/统计/可视化代码；字段对齐/口径显式/缺失异常策略可解释。
2. **境配置**：依赖声明/版本锁定/包冲突/环境隔离；同一代码跨机器可安装可启动；降级替代说明。
3. **行调试**：真实数据跑通；路径/编码/类型/内存/超时处理；每次执行命令行/日志/退出状态留痕（sw_agent --iocheck）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 代码生成（1-2请求）：按数据字典生成（口径显式）
### 阶段2 环境声明（0请求）：requirements+版本锁定模板
### 阶段3 执行审计（0请求）：`python scripts/sw_agent.py --iocheck io.json`
### 阶段4 成文（1请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/codegen-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 字段缺失 | 显式处理策略不默认 |
| 依赖冲突 | 版本锁定+替代方案 |
| 超时 | 分块/采样降级 |

## 资源清单
scripts：sw_agent.py, clean_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。