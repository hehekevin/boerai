# 总课题规则（general-rules.md）

## 1. 子场景路由
| case.json 任务特征 | 路由 | 引擎子命令 |
|-|-|-|
| 提到参考集/覆盖率/遗漏 | 覆盖率审计 | search_audit --coverage --classify |
| 提到纳入/排除/标准/筛选 | 纳排筛选 | screening_engine --screen --audit |
| 提到迭代/轮次/停止 | 迭代补检 | iter_loop --ledger --stop |
| 提到去重/多库/合并 | 联合检索 | search_audit --dedup |
| 混合/不明确 | 全链路 | 按顺序全部执行 |

## 2. 通用纪律
- 每条结果带来源（库/查询式/记录idx）
- 每条判定带依据码
- 遗漏/冲突/缺失元数据/权限逐条说明
- 全部确定性操作0模型请求

## 3. 异常处置
见 SKILL.md 异常表。