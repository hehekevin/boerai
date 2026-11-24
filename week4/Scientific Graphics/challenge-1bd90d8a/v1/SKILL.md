---
name: chart-gen-edit-forge
description: 科研数据图表生成与编辑：图表生成（表格/统计/记录→柱/折/散/箱/热/多面板；数据到图元映射）、样式调整（期刊模板字号线宽配色图例布局留白——可复用样式配置非一次性手工）、图注校验（轴标签单位/刻度/图例系列/误差线显著性/样本量——缺失错配遮挡识别）。
---

# chart-gen-edit-forge

## 核心原则（不可违反）
1. **表生成**：表格/统计结果/实验记录→按图型要求生成柱状/折线/散点/箱线/热图/多面板；数据到图元映射正确（stats_viz --chartpick）。
2. **式调整**：按目标期刊/模板/团队规范调整字号/线宽/配色/图例位置/面板布局/留白——可复用样式配置而非一次性手工（styles.json）。
3. **注校验**：轴标签单位/刻度范围/图例系列对应/误差线与显著性含义/样本量与图注一致——缺失/错配/遮挡识别（stats_viz --caption）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 选型（0请求）：`python scripts/stats_viz_engine.py --chartpick`
### 阶段2 样式配置（0请求）：styles.json 可复用
### 阶段3 图注校验（0请求）：`python scripts/stats_viz_engine.py --caption`
### 阶段4 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/chart-gen-edit-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 遮挡 | 元素避让建议 |
| 多面板 | 统一样式配置 |
| 图注缺失 | missing 清单 |

## 资源清单
scripts：stats_viz_engine.py, clean_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。