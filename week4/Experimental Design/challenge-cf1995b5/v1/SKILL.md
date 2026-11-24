---
name: plan-gen-forge
description: 实验方案生成与优化：假设与变量（目标→可检验假设；操作定义/测量/单位/取值范围；自变量因变量混杂）、对照组（空白/阳性/阴性/剂量梯度；每对照排除哪类混杂；避免单组对照或不匹配）、设备材料（步骤绑定型号量程耗材试剂；可替代与不可替代标注）。
---

# plan-gen-forge

## 核心原则（不可违反）
1. **与变量**：研究目标拆可检验假设；变量操作定义/测量方式/单位/取值范围；自变量/因变量/混杂因素明确（plan_engine --variables）。
2. **对照组**：空白/阳性/阴性/剂量梯度设计；每个对照排除哪一类混杂说明；避免只有一组对照或对照与目标不匹配（plan_engine --controls）。
3. **备材料**：步骤绑定具体设备型号/量程/耗材规格/试剂信息；可替代项与不可替代项标注（plan_engine --resources）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 假设变量（0请求+1请求细化）：`python scripts/plan_engine.py --variables goal.json`
### 阶段2 对照设计（0请求）：`--controls design.json`
### 阶段3 设备材料（0请求）：`--resources proposal.json inventory.json`
### 阶段4 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/plan-gen-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 假设不可检验 | falsifiable 检查 |
| 对照不足 | 缺失对照+排除混杂说明 |
| 不可替代项缺失 | 阻断提示 |

## 资源清单
scripts：plan_engine.py, novelty_matrix.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。