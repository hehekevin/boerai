# 异常与降级处置（edge-cases.md）

| 情形 | 处置 |
|-|-|
| 无 MathML/XML/公式表示（缺失分支） | 核对可核对项（明确指标、条件）；缺失对象的推导/复算 → status=partial + insufficient_evidence=true；**不得反推公式、不得把未知填 0** |
| XML 解析失败 | anomalies 记录 ParseError；降级用 PDF 文本层抽公式，每条标 `source=pdf-text` |
| 公式为图片 | 保留编号与上下文引用；本体不猜；gaps 记录页码 |
| 符号歧义/重载 | 逐处单列 + human_confirm |
| 代入无解或复算不符 | conflicts 记录（声称值 vs 复算值 vs 来源）；不凑数 |
| case.json 缺失/损坏 | task.md 取要求；anomalies 记录；status=partial |
| 预算不足 | 冻结：公式目录 + 变量表先落盘；推导/代入可 partial |

降级输出仍须满足：result.json 含 case_id+status+原因；公式目录与变量表无论进度都完整交付；缺失分支显式写 insufficient_evidence。
