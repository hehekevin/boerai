---
name: compliance-check-forge
description: 学术规范与合规检查：学术诚信（图像复用/重复发表/署名/利益冲突/基金一致——判断依据非仅提示）、引用规范（文献真实存在/元数据一致/论断对应；引而不证/张冠李戴/格式不统一）、数据合规（可识别个人信息/受限数据/伦理审批依据；脱敏改写建议）。
---

# compliance-check-forge

## 核心原则（不可违反）
1. **术诚信**：数据与图像复用/重复发表/不当署名/利益冲突缺失/致谢基金不一致——给出判断依据（review_engine --integrity）。
2. **用规范**：被引文献真实存在/元数据与原文一致/论断与文献一一对应；识别引而不证/张冠李戴/格式不统一（claim_evidence --checkref + review_engine --cites）。
3. **据合规**：可识别个人信息/受限数据/未公开数据识别；授权或伦理审批依据判断；脱敏与改写建议（review_engine --datacompliance）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 诚信（0请求）：`python scripts/review_engine.py --integrity`
### 阶段2 引用规范（0请求）：`python scripts/review_engine.py --cites doc.json refs.json` + claim_evidence --checkref
### 阶段3 数据合规（0请求）：`python scripts/review_engine.py --datacompliance`
### 阶段4 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/compliance-check-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 引文缺失 | cited_but_no_ref 清单 |
| PII发现 | 脱敏建议+位置 |
| 依据不明 | 判断依据声明 |

## 资源清单
scripts：review_engine.py, claim_evidence.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。