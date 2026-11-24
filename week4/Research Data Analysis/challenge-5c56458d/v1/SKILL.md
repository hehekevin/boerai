---
name: db-query-forge
description: 科研数据库查询与分析：连接（参数/权限/库表发现/快照版本；读写边界）、查询生成（可执行/时间范围/筛选/排序分页；报错定位修复）、结果抽取（稳定导出结构化；类型/单位/编码/缺失/重复）。
---

# db-query-forge

## 核心原则（不可违反）
1. **库连接**：连接参数/权限范围/库表发现/数据快照版本；哪些可读写哪些只读显式（sw_agent --gates）。
2. **询语句**：问题→可执行查询；时间范围/筛选/排序/分页；报错定位与修复（question_decompose 拆解+sw_agent --params）。
3. **果抽取**：稳定导出结构化；字段类型/单位/编码/缺失/重复处理（clean_engine --normalize + multidb_engine --merge）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 权限与连接（0请求）：`python scripts/sw_agent.py --gates`
### 阶段2 查询规划（0请求）：`python scripts/question_decompose.py --decompose`
### 阶段3 结果标准化（0请求）：`python scripts/clean_engine.py --normalize`
### 阶段4 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/db-query-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 只读限制 | 明确读写边界 |
| 查询报错 | 定位+修复记录 |
| 导出编码 | UTF-8容错 |

## 资源清单
scripts：sw_agent.py, question_decompose.py, clean_engine.py, multidb_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。