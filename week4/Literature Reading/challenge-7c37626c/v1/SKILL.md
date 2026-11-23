---
name: formula-reasoning-forge
description: 公式解析与数学推理。从论文/MathML/XML 中确定性还原公式结构（分式、上下标、希腊字母、编号），建立带来源定位的变量表，把推导拆成可检查步骤并标注假设与边界条件，可计算公式做数值代入核验（符号/单位/数量级），材料无公式表示时如实报告 partial/insufficient_evidence。触发词：公式解析、LaTeX、MathML、变量表、推导、数值代入、符号一致性、formula。
---

# formula-reasoning-forge — 公式解析与数学推理

一句话：**MathML 先行、符号必对账、推导拆步标假设、能算必代入——算不出和没有的都如实说。**

## 核心原则（不可违反）

1. **认得准**：公式结构从 MathML/XML 确定性线性化（脚本），分式/上下标/括号层级不错位；纯文本材料中的公式逐字符保留，不"顺手美化"。
2. **讲得清**：变量表中每个符号必须能指回原文定义位置（file:line）；材料里找不到定义 → 进 gaps + human_confirm，**不按常识猜**。区分三类：`原文定义` / `上下文推断` / `常识补充`，推断与补充必须标注。
3. **推得顺**：关键推导拆成编号步骤，每步标明所用假设、近似、边界条件；跨公式引用（"由式(3)"）写成依赖关系。
4. **算得回**：可计算公式做数值代入（脚本 safe_eval），比对声称结果；符号错误/数量级错误 → conflict 清单。
5. **诚实缺失分支**：材料没有公式表示（如快照缺 MathML/逐条预测/可复算数据）时，**不得反推公式或把未知填 0**——核对明确指标与条件，缺失对象的推导/复算报告 `partial` 或 `insufficient_evidence`。

## 运行环境约定

- 输入：`/input/case.json` 与 `/input/task.md`；材料含 `artifacts/publisher-source.xml`（出版商 XML 原样副本）与 `artifacts/source-formulas.xml`（公式节点子集，保留 MathML 与来源 ID）时优先使用；实际文件为准，不凭标签假设。
- 工作目录 `/app/work`，输出 `/app/output`。
- 资源以 `<SKILL_DIR>` 指代；找不到时 `find / -maxdepth 4 -name "math_audit.py" 2>/dev/null`。

## 工作流程（五阶段）

### 阶段 0：盘点（约 1 次模型请求）

```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

确认 case_id、output_contract、材料清单；**重点找 XML/MathML 类文件**。判断本案例属于哪类：有公式表示（走完整流程）/ 无公式表示（走缺失分支）。

### 阶段 1：公式目录（0 次模型请求）

```bash
python <SKILL_DIR>/scripts/math_audit.py --mathml <artifacts/source-formulas.xml> --out /app/work/catalog.json
```

产出公式目录：`[{id, order, linear, symbols[]}]`——MathML 线性化（mfrac→(a)/(b)、msub→x_{i}、msup→x^{2}），符号集自动抽取。XML 缺失时：从 PDF/文本层抽取行间公式（等号/编号 (N) 行），标注 `source=pdf-text` 且置信度降级。

### 阶段 2：变量表（0 次模型请求 + 1–2 次模型请求）

```bash
python <SKILL_DIR>/scripts/math_audit.py --vars <材料...> --out /app/work/vardefs.json
python <SKILL_DIR>/scripts/math_audit.py --crosscheck --catalog /app/work/catalog.json --varfile /app/work/vardefs.json
```

正则抽取变量定义句（x is / where x= / x 为 / x 表示）→ 交叉核对：公式中出现但无定义的符号 → 逐个清单（模型仅在此时介入：在原文中语义确认或判为缺失）。输出变量表：`[{symbol, meaning, source, class: 原文定义|上下文推断|常识补充, unit?, range?}]`。

### 阶段 3：推导与代入（约 3–5 次模型请求）

- **推导分步**：对目标公式写编号步骤：每步 = 输入（前步/式(N)）+ 操作（代数变形/代入/近似）+ 输出 + 假设与边界条件。
- **数值代入**：对可计算公式，
  ```bash
  python <SKILL_DIR>/scripts/math_audit.py --numeric "(3.18-1.42)/1.42*100"
  ```
  中间值逐条记录；与原文声称值比对 → 一致 / conflict（符号/单位/数量级，写明差异与可能原因）。单位不一致只标记不换算。

### 阶段 4：交付与自检（0 次模型请求 + 1 次复核）

组装 `/app/output/result.json`（合并 output_contract 全部字段与 case_id）：公式目录（线性化 + 来源 ID）、变量表、推导步骤、代入核验记录、gaps（无定义符号）/ conflicts（复算不符）/ anomalies；C02 类缺失案例 status=partial + `insufficient_evidence: true` 并写明缺什么。核验：

```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/formula-report.md --require "公式|formula|mathml|linear,变量|variable|符号|symbol,代入|numeric|复算" --names "formulas,vars,numeric"
```

主产物 `/app/output/formula-report.md`：每条公式 → LaTeX/线性化 + 变量表 + 推导步骤 + 代入结果，全部带来源锚点。

## 异常处置速查（详见 references/edge-cases.md）

| 情形 | 处置 |
|-|-|
| 无 MathML/XML（C02 类） | 核对可核对项；缺失对象报 partial/insufficient_evidence；**不反推公式不填 0** |
| XML 解析失败 | anomalies 记录；改从 PDF 文本层抽公式，置信度标注降低 |
| 公式图片化 | 编号与上下文保留，本体不猜，gaps 记录 |
| 符号严重歧义（同符号多义） | 每处出现单独列条 + human_confirm |
| 代入无解/复算不符 | 不强行凑数；conflicts 记录差异与可能原因 |
| 单位缺失 | 变量表 unit 留空 + gaps |

## 资源清单

- `scripts/math_audit.py` — MathML 解析/线性化、符号抽取、变量定义扫描、交叉核对、安全代入
- `scripts/inspect_case.py`、`scripts/validate_result.py` — 盘点与交付契约校验
- `references/formula-rules.md` — 线性化约定、变量三级分类、推导步骤格式
- `references/edge-cases.md` — 异常与缺失分支处置
- `templates/result.schema.json`、`templates/var-table.md`、`templates/derivation-steps.md`
- `examples/minimal-example.md` — 最小调用示例（示例数据，非正式案例结果）
- `README.md` — 使用说明与维护信息

## 预算红线

64 次模型请求 / 900 秒 / 单响应 16384 token。MathML/变量扫描/交叉核对/代入恒为 0 请求；模型仅用于定义语义确认与推导成文（≤6 次）。过 60% 时间立即冻结：目录+变量表先行落盘（可复用价值最高），推导与代入可 partial。
