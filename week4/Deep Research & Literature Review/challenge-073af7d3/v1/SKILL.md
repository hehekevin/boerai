---
name: trend-analysis-forge
description: 研究前沿与趋势分析：时间趋势（产出量/主题占比/增长速率；离散波动vs真实拐点；数据口径影响声明）、主题演化（出现/合并/分裂/衰退；术语漂移/同名异义；阶段划分依据）、代表性工作（入选口径+覆盖范围；避免纯被引排序漏长尾首创）。
---

# trend-analysis-forge

## 核心原则（不可违反）
1. **间趋势**：按年份/时间窗统计产出量、主题占比、增长速率；区分离散波动与真实拐点；数据口径（在线/见刊/预印本）对结论的影响声明（increment_tracker 时间窗+stats_viz descriptive）。
2. **题演化**：主题词/子领域出现/合并/分裂/衰退；术语漂移与同名异义识别；阶段划分及其依据（crosslang 术语矩阵+citation_network 网络）。
3. **性工作**：各阶段代表性文献入选口径与覆盖范围声明；不只总被引排序——长尾方法首创不遗漏（ranking_engine 显式权重）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 时间统计（0请求）：`python scripts/stats_viz_engine.py --descriptive`
### 阶段2 主题演化（0请求）：`python scripts/crosslang_search.py --termmatrix` + citation_network --network
### 阶段3 代表性工作（0请求）：`python scripts/ranking_engine.py --score/--label`
### 阶段4 成文（2-3请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/trend-analysis-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 口径混杂 | 分口径统计+影响声明 |
| 术语漂移 | 别名归并+漂移标注 |
| 拐点误判 | 波动vs拐点判定依据声明 |

## 资源清单
scripts：stats_viz_engine.py, crosslang_search.py, citation_network.py, ranking_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。