---
name: presentation-planner-forge
description: 汇报目标转可检查项（受众/页数/时长/结论强度）、主骨架叙事顺序（非目录搬运）、每页唯一主张+证据强度、答问准备（机制/数据/对照/局限）。
---

# presentation-planner-forge

## 核心原则（不可违反）
1. **目标可检查**：把"这次汇报要达成什么"转成可检查目标（评委认可新颖性/合作者理解进度风险），据此定页数、时长与结论强度。
2. **叙事顺序**：问题-方法-结果-结论主骨架上取舍铺垫（起承转合），不是按论文目录逐节搬运。
3. **要点信息**：每页唯一主张+支撑证据+图形表达；长段落压缩成一句可讲的结论；标注该结论的证据强度。
4. **答问准备**：预判机制/数据/对照/局限四类追问，准备可引用页面、备用页、口径一致的回答要点。
5. **脚本先行**：goals/order/slides/qa 恒为0模型请求。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 目标转可检查（0请求）：`python scripts/presentation_planner.py --goals goals.json`
### 阶段2 叙事顺序（0请求+1请求页内容规划）：`python scripts/presentation_planner.py --order outline.json`
### 阶段3 页级主张（0请求）：`python scripts/presentation_planner.py --slides outline.json`
### 阶段4 答问准备（0请求）：`python scripts/presentation_planner.py --qa outline.json`
### 阶段5 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/presentation-planner-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 目标模糊 | 模型按题面上下文明确受众与强度 |
| 页数超限 | 主结论优先，细节降备用页 |
| 证据强度不足 | 标'中等（需补证据）'不冒充强 |

## 资源清单
scripts：presentation_planner.py + inspect_case + validate_result；references/rules.md；templates/result.schema.json；examples；README。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。