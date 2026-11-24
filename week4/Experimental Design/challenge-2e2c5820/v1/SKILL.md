---
name: feasibility-check-forge
description: 实验方案可行性评估：检查项体系（设备/材料/时间/样本/伦理安全/参数范围/风险异常七项可勾选判定；依据来自SOP/规格书/审批）、条件核验（设备型号精度附件耗材vs现有清单——已具备/可外协/需采购/不具备）、时间估算（设备占用/人工/等待/检测周转可解释；样本来源保存条件伦理进度核对）。
---

# feasibility-check-forge

## 核心原则（不可违反）
1. **项体系**：设备/材料/时间/样本/伦理与安全/参数范围/风险与异常拆成可勾选可判定检查项；每项判定依据来自SOP/规格书/审批（plan_engine --checklist）。
2. **件核验**：设备型号/精度/附件/耗材规格vs现有清单——四态区分（已具备/可外协/需采购/不具备）（plan_engine --resources）。
3. **本估算**：步骤拆设备占用/人工/等待/检测周转——可解释估算；样本来源/数量/保存条件/伦理审批进度核对（plan_engine --time）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 检查项（0请求）：`python scripts/plan_engine.py --checklist proposal.json`
### 阶段2 资源核验（0请求）：`--resources proposal.json inventory.json`
### 阶段3 时间估算（0请求）：`--time estimate.json`
### 阶段4 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/feasibility-check-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 四态判定 | 不具备→明确提示 |
| 估算缺依据 | 标记待确认 |
| 伦理未批 | 阻断项提示 |

## 资源清单
scripts：plan_engine.py, novelty_matrix.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。