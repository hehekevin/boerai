---
name: paper2ppt-forge
description: 叙事骨架提取（问题/做法/证据/结论，主结论与支撑区分）、信息分层（每页主张+要点数+短语改写+密度控制）、证据保留（图/表/公式来源+编号单位图注防张冠李戴）、讲解备注（不重复页面文字）。
---

# paper2ppt-forge

## 核心原则（不可违反）
1. **主线提取**：识别问题/核心做法/关键证据/结论形成页序可讲的骨架；区分主结论与支撑细节。
2. **信息分层**：每页承载的主张/要点数/层级；长段落改写为可讲述短语；单页密度受控。
3. **证据保留**：每页定位论文图表/公式/数据来源；保留编号/单位/图注/条件——防张冠李戴。
4. **备注**：与页面对应但不重复页面文字——过渡/强调点/被问时补充证据。
5. **脚本先行**：outline/density/figures/notes 恒为0模型请求。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 骨架（0请求）：`python scripts/ppt_engine.py --outline paper.json`
### 阶段2 分层（0请求）：`python scripts/ppt_engine.py --density outline.json`
### 阶段3 图表槽位（0请求）：`python scripts/ppt_engine.py --figures paper.json`
### 阶段4 备注（0请求）：`python scripts/ppt_engine.py --notes outline.json`
### 阶段5 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/paper2ppt-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 无图表数据 | 只引用原图（redraw_allowed=false） |
| 页数超限 | 主结论优先细节降级 |
| 图注缺失 | missing 标记不编造 |

## 资源清单
scripts：ppt_engine.py + inspect_case + validate_result；references/rules.md；templates/result.schema.json；examples；README。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。