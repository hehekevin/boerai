---
name: citation-tracking-forge
description: 引文追踪与关联文献发现。前向/后向双向扩展（多层级+分支剪枝+停止判断），关联文献发现（共被引/耦合/作者/数据集信号说明依据），种子中心引用网络（奠基/桥接/热点角色），路径解释（逐跳方向+语境线索），身份合并（预印本/会议版/期刊版）。触发词：引文追踪、前向后向、引用网络、关联文献。
---

# citation-tracking-forge — 引文追踪与关联文献发现

一句话：**双向扩展有剪枝、网络有角色、路径有解释、身份有合并。**

## 核心原则（不可违反）

1. **双向扩展不无限**：沿参考文献向后找方法与数据出处，沿施引文献向前找后续改进与批评；hop>=3 剪枝+入边>8 待相关性过滤——避免只取一层后又无限扩展。
2. **关联必说明依据**：共被引/文献耦合/作者机构关联/数据集任务关联等信号找到平行工作，每条记录关联信号类型与强度。
3. **网络给可读结构**：识别奠基性节点（早期被引多）、桥接节点（连接多分支）、近期热点——不是无法解释的连边图。
4. **路径逐跳解释**："种子如何连到远端文献"给出最短/最可信引用链，逐跳标注引用方向、数据源、语境线索，区分直接引用与间接可达。
5. **身份合并**：DOI/标题/作者/年份字段不一致、预印本/会议版/期刊版/增补版归并，处理同名作者歧义。
6. **脚本先行**：扩展/网络/路径/合并恒为0模型请求。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：双向扩展（0请求）
```bash
python <SKILL_DIR>/scripts/citation_network.py --trace <种子.json> <引文链.json> > /app/work/expanded.json
```

### 阶段 2：网络结构（0请求）
```bash
python <SKILL_DIR>/scripts/citation_network.py --network /app/work/expanded.json > /app/work/network.json
```

### 阶段 3：路径解释（0请求）
```bash
python <SKILL_DIR>/scripts/citation_network.py --path /app/work/expanded.json <目标文献ID>
```

### 阶段 4：身份合并（0请求）
```bash
python <SKILL_DIR>/scripts/citation_network.py --merge <记录集.json> > /app/work/merged.json
```

### 阶段 5：语义复核与成文（约2-4次模型请求）
复核剪枝决策（被剪节点是否确实低相关）、关联发现的语义依据、路径的引用语境解读。

### 阶段 6：交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/citnet-report.md --require "追踪|trace|前向|后向|扩展,网络|network|节点|hub,路径|path|链|hop,合并|merge|身份|version" --names "trace,network,path,merge"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 种子论文无引文数据 | gaps 声明，输出种子清单 |
| 图过大（>500节点） | hop 限制降为2 + 只保留 hubs |
| 引用语境缺失 | evidence 标 unknown，不编造语境 |
| 预算不足 | expanded.json 先落盘 status=partial |

## 资源清单
- `scripts/citation_network.py` — trace/network/path/merge（确定性引擎）
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/citnet-rules.md`、`templates/result.schema.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。四子命令恒为0请求。过60%时间冻结。