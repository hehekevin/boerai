---
name: writing-client-forge
description: 学术写作客户端。稿件修改的可控与可追溯：修改指令落到具体句子（措辞/结构/术语/引用四层），生成可逐条接受或拒绝的修订记录（before/after/依据/位置），引用编号与参考文献表一致性、图表编号引用一致性由脚本强制，版本间差异对比与回退，导出保持结构。触发词：稿件修改、修订追踪、版本对比、引用编号、writing client。
---

# writing-client-forge — 学术写作客户端

**指令落位到句、修订逐条可接受/拒绝、编号一致性脚本强制——改得准、可追溯、格式不塌。**

## 核心原则（不可违反）

1. **每条判断/改动可指回原文**：修改定位到句子并附 before/after，不整段推倒重写。
2. **脚本先行**：diff/编号/引用检查 0 模型请求；模型只做指令落位与成文。
3. **诚实标注**：材料不足、疑似误报、需作者裁决分列 gaps/human_confirm/uncertainties。
4. **格式不塌**：改动后标题层级、编号、图表题注、引用必须仍然自洽（脚本回查）。

## 运行环境约定

- 输入：`/input/case.json` 与 `/input/task.md`；材料以实际路径为准。
- 工作目录 `/app/work`，输出 `/app/output`。资源以 `<SKILL_DIR>` 指代。

## 工作流程

### 阶段 0：盘点（约 1 次模型请求）

```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

读 task.md：修改指令清单、目标版本、交付格式。

### 阶段 1：基线审计（0 次模型请求）

```bash
python <SKILL_DIR>/scripts/revision_tracker.py --numbering /input/materials/manuscript.md --out /app/work/numbering.json
```

引用编号连续性、引用-文献表一致、图表编号引用一致——基线问题先摸清，避免修改引入新错。

### 阶段 2：指令落位与修改（约 4–6 次模型请求）

每条修改指令落到**句子层**：`{instruction, layer: 措辞|结构|术语|引用, target: 原句摘录, action, basis}`。改稿产 `/app/output/manuscript-revised.md`：
- 措辞层：句内改写，保留术语与数字；
- 结构层：段级移动/合并（不改变事实内容）；
- 术语层：全篇统一替换（同一术语唯一译名/名）；
- 引用层：增删引用必须同步文献表。

### 阶段 3：修订记录与核验（0 次模型请求）

```bash
python <SKILL_DIR>/scripts/revision_tracker.py --diff /input/materials/manuscript.md /app/output/manuscript-revised.md --out /app/work/revisions.json
python <SKILL_DIR>/scripts/revision_tracker.py --numbering /app/output/manuscript-revised.md
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/work/revisions-summary.md --require "修订|revision|before|after,编号|numbering|引用,指令|instruction" --names "revisions,numbering,instructions"
```

--diff：逐条修订记录（段落级 + 句级细粒度），每条可独立接受/拒绝；--numbering：修改后编号仍自洽。FAIL 先修。

### 阶段 4：交付

`/app/output/result.json`（合并 output_contract + case_id）：修订记录、指令落位表、编号检查结果、gaps/anomalies、status。

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 指令与稿件内容对不上 | 不强行落位；uncertainties 记录 + 建议澄清 |
| 修改引发编号错位 | --numbering FAIL → 修编号再交 |
| 指令要求整段重写 | 拆成句级修订逐条执行，拒绝语义漂移 |
| 版本混乱 | 以 case.json 指定版本为基线，anomalies 记录其他副本 |
| 预算不足 | revisions.json 先落盘，status=partial |

## 资源清单

- `scripts/` 领域脚本与共享盘点/校验脚本；`references/`；`templates/`；`examples/`（示例）；`README.md`

## 预算红线

64 次模型请求 / 900 秒 / 单响应 16384 token。检测脚本恒为 0 请求。过 60% 时间先落盘 status=partial。
