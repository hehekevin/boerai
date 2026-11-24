---
name: reader-client-forge
description: 阅读客户端。单界面全流程（打开/定位/选中提问/保存/回看）、选区问答锚定原文、状态持久化可导出、操作路径+锚点+原始输出可复核复现。触发词见核心原则。
---

# reader-client-forge — 阅读客户端

## 核心原则（不可违反）

1. **得起来**：打开文献、定位、选中提问、保存结果、回看在同一处完成——sessionlog 六步审计，跨工具搬运=FAIL。
2. **上原文**：答案基于当前页面与选中文本；锚点（页码/段落/片段）一键回跳；引文与上下文逐字匹配校验。
3. **得下来**：批注/问答结论/阅读位置保存、回看、导出——随对话消失=失败。
4. **得清楚**：操作路径、原文锚点、每次运行原始输出可被他人复核复现。
5. **定位容错**：PDF物理页与印刷页不一致、跨栏排版、扫描件无文本层——处理方式显式声明。
6. **脚本先行**：sessionlog/anchor/persistence/repro 恒为0模型请求。

## 运行环境约定

- 输入 `/input/case.json` 与 `/input/task.md`；材料以实际路径为准。工作目录 `/app/work`，输出 `/app/output`。引擎以 `<SKILL_DIR>` 指代。

## 工作流程

### 阶段0 盘点（1请求）：`python scripts/inspect_case.py /input/case.json`
### 阶段1 流程审计（0请求）：`python scripts/reader_workflow.py --sessionlog events.json`
### 阶段2 锚点校验（0请求）：`python scripts/reader_workflow.py --anchor answers.json`
### 阶段3 持久化审计（0请求）：`python scripts/reader_workflow.py --persistence session.json`
### 阶段4 复现审计（0请求）：`python scripts/reader_workflow.py --repro session.json`
### 阶段5 成文（1请求）：客户端工作流说明

### 交付阶段（0请求）

组装 `/app/output/result.json`（合并 output_contract 全部字段与 case_id）。核验：

```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/reader-client-forge.md --require "原则关键词,流程关键词,异常关键词" --names "p1,p2,p3"
```

主产物 `/app/output/reader-client-forge.md`：每条结论带锚点。

## 异常处置速查（详见 references/rules.md）

| 情形 | 处置 |
|-|-|
| 流程缺步 | missing_steps 列出+FAIL |
| 答案无锚点 | unanchored——补锚点或标推断 |
| 扫描件无文本层 | 声明OCR限制，不编造文本 |
| 导出格式未声明 | 列为缺口 |

## 资源清单

- `scripts/`：reader_workflow.py；inspect_case.py、validate_result.py
- `references/rules.md`、`templates/result.schema.json`、`examples/minimal-example.md`、`README.md`

## 预算红线

64 次模型请求 / 900 秒 / 单响应 16384 token。确定性子命令恒为 0 请求；模型仅语义裁决与成文。过 60% 时间冻结：JSON 先落盘，status=partial。