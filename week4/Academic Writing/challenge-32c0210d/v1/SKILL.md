---
name: thesis-longdoc-forge
description: 章节规划对齐提纲与字数分配、跨章节术语/符号/编号/图表引用/结论一致（改动影响定位）、局部修改最小化、论断引用改动可追溯。
---

# thesis-longdoc-forge

## 核心原则（不可违反）
1. **立得住**：章节规划与提纲、论证链条、字数分配对应——不是堆通顺文字。
2. **连得上**：跨章节术语/定义/符号/编号/图表引用/前后结论一致；改动一处后受影响段落可被找出（影响面分析）。
3. **改得动**：局部修改只动需要动的地方，保留原意与既有表述；作者能看懂改了什么为什么。
4. **查得清**：每个论断/引用/改动追溯到原文/文献/版本记录，他人可独立复核。
5. **脚本先行**：structure_audit（第3周验证资产）+ revision_tracker 复用；crossdoc 一致性校验新引擎逻辑内置于 structure_audit 流程。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 结构审计（0请求）：`python scripts/structure_audit.py --audit 章节树`（复用第3周资产）
### 阶段2 修订追踪（0请求）：`python scripts/revision_tracker.py --diff 修改记录`
### 阶段3 一致性影响面（0请求）：`python scripts/structure_audit.py --impact 改动项`
### 阶段4 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/thesis-longdoc-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 章节字数失衡 | 分配表+偏差报告 |
| 术语不一致 | 一致性清单+受影响段落定位 |
| 大范围重写请求 | 拆成可接受/拒绝的最小编辑单元 |

## 资源清单
scripts：zeros-probe-placeholder + inspect_case + validate_result；references/rules.md；templates/result.schema.json；examples；README。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。