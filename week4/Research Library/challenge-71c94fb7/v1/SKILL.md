---
name: collection-migrate-forge
description: 科研资料收集与迁移：多源稳定采集（分页/滚动/登录态失效/下载中断）、字段映射表（同义命名/单位归一/多源合并/缺失标注）、迁移前后完整性校验（记录数/字段数/关键值/附件清单差异报告：预期vs缺陷）。
---

# collection-migrate-forge

## 核心原则（不可违反）
1. **料采集**：浏览器/数据库检索结果/本地下载目录/文献管理软件/内部系统稳定取回记录与附件；分页/滚动加载/登录态失效/下载中断处理（increment_tracker 幂等重试逻辑）。
2. **段映射**：来源→目标字段映射表；同义命名/单位与格式归一/多来源字段合并；缺失与不可映射项标注（multidb_engine FIELD_MAP + clean_engine）。
3. **性校验**：迁移前后比对记录数/字段数/关键字段取值/附件清单；差异报告分"预期差异"与"缺陷"——说明判定依据（sw_agent --iocheck 完整性逻辑）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 采集（0请求+失败重试审计）：`python scripts/increment_tracker.py --retrylog events.json`
### 阶段2 字段映射（0请求）：`python scripts/multidb_engine.py --merge`
### 阶段3 完整性校验（0请求）：`python scripts/sw_agent.py --iocheck io.json` + 前后计数对账
### 阶段4 差异报告（1请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/collection-migrate-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 登录态失效 | 提示重登+已获数据保留 |
| 下载中断 | 幂等重试（不产生二次） |
| 不可映射字段 | 清单标注 |
| 差异归因 | 预期/缺陷分开说明 |

## 资源清单
scripts：multidb_engine.py, clean_engine.py, increment_tracker.py, sw_agent.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。