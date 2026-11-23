# formula-reasoning-forge — 使用与方法说明

**一句话**：MathML 确定性还原公式 + 变量表对账 + 推导拆步标假设 + 数值代入核验；无公式表示的案例如实报 partial/insufficient_evidence。

## 调用
```bash
python scripts/inspect_case.py /input/case.json
python scripts/math_audit.py --mathml <xml> --out catalog.json
python scripts/math_audit.py --vars <材料...> --out vardefs.json
python scripts/math_audit.py --crosscheck --catalog catalog.json --varfile vardefs.json
python scripts/math_audit.py --numeric "表达式"
python scripts/validate_result.py --case /input/case.json --result result.json --manuscript report.md --require "公式|formula,变量|variable,代入|numeric" --names "formulas,vars,numeric"
```

## 关键方法
1. MathML 线性化（mfrac/msub/msup/msqrt 全覆盖）+ 符号集自动抽取，结构不错位；
2. 变量三级分类（原文定义/上下文推断/常识补充），缺失不猜；
3. 推导步骤四要素（输入/操作/输出/假设）；
4. safe_eval 数值代入（白名单字符），复算不符记 conflict 不凑数。

## 边界与限制
- 适用：论文公式的结构还原、变量表、推导说明、数值复算；MathML/XML 优先，PDF 文本层降级。
- 不适用：公式图片 OCR（本体不猜）、矩阵语义级推导验证。
- 限制：矩阵/分段函数线性化为拼接形式（保结构注释）；单位不自动换算。

## 维护
版本 1.0.0（2026-11），作者 boeragent。脚本改动同步 examples；线性化约定见 references/formula-rules.md。
