---
name: screening-ranking-forge
description: 文献筛选与智能排序。多信号显式加权排序（相关性/时效/来源/研究类型），分层标签体系（核心证据/方法参考/背景资料/待排除），同研究多篇报道与预印本冲突处理，逐条优先级解释（命中规则+证据+置信度）。触发词：筛选、排序、标签、优先级、conflict。
---

# screening-ranking-forge — 文献筛选与智能排序

一句话：**权重显式可复算、标签分层有判据、冲突不掩盖、解释逐条给。**

## 核心原则（不可违反）

1. **权重显式**：relevance_terms 0.45 / recency 0.25 / venue 0.20 / study_type 0.10——写在结果里且可复算；同分并列规则显式（年份新→旧，再标题字典序）。
2. **分层标签**：core_evidence（>=0.6）/ method_reference（0.4-0.6）/ background（0.2-0.4）/ exclude_candidate（<0.2，待人工复核而非直接删除）；边界案例约定明确。
3. **相关性三档**：依据研究问题、对象、方法、人群、时间范围逐条判断直接相关/间接相关/不相关。
4. **冲突不掩盖**：同研究多篇报道→合并保留正式版；预印本→标记待正式版替换；标注分歧→升级人工复核。
5. **逐条解释**：每条排序结果说明命中哪条规则、依据哪些证据、置信度如何——支撑人工复核。
6. **脚本先行**：打分/标签/冲突/解释恒为0模型请求。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：加权打分（0请求）
```bash
python <SKILL_DIR>/scripts/ranking_engine.py --score <记录集.json> > /app/work/scored.json
```
relevance_terms 由模型按研究问题提供（1次请求），打分本身0请求。

### 阶段 2：分层标签（0请求）
```bash
python <SKILL_DIR>/scripts/ranking_engine.py --label /app/work/scored.json > /app/work/labeled.json
```

### 阶段 3：冲突处理（0请求）
```bash
python <SKILL_DIR>/scripts/ranking_engine.py --conflicts /app/work/scored.json > /app/work/conflicts.json
```

### 阶段 4：优先级解释（0请求）
```bash
python <SKILL_DIR>/scripts/ranking_engine.py --explain /app/work/scored.json > /app/work/explain.json
```

### 阶段 5：成文与交付（约1-2次模型请求）
模型复核 exclude_candidate 边界案例；组装 result.json（合并 output_contract + case_id）。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/ranking-report.md --require "排序|rank|权重|weight,标签|label|分层,冲突|conflict,解释|explain|理由" --names "score,label,conflicts,explain"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 无 relevance_terms 输入 | rel=0 全部记录，权重退化为 recency+venue——报告中显式声明退化 |
| 年份缺失 | recency 按最旧值处理并记录 |
| 分数普遍偏低 | 报告分布，提示权重或词表需调整 |
| 预算不足 | scored.json 先落盘 status=partial |

## 资源清单
- `scripts/ranking_engine.py` — score/label/conflicts/explain（确定性引擎）
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/ranking-rules.md`、`templates/result.schema.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。打分/标签/冲突/解释恒为0请求；模型仅词表提供与边界复核（≤3次）。过60%时间冻结。