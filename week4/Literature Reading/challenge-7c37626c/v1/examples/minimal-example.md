# 最小调用示例（示例数据，非正式案例结果）

## 输入（示意）

`input/artifacts/source-formulas.xml`（MathML 子集）：
```xml
<formulas>
  <math id="F001"><mrow><mi>y</mi><mo>=</mo><mfrac><mi>a</mi><mi>b</mi></mfrac><msub><mi>x</mi><mi>i</mi></msub></mrow></math>
</formulas>
```

`input/materials/paper.txt`：
```
where a is the intercept of the calibration curve and b denotes the slope.
xi represents the i-th sample concentration (mg/mL).
```

## 调用

```bash
python scripts/math_audit.py --mathml input/artifacts/source-formulas.xml --out /app/work/catalog.json
python scripts/math_audit.py --vars input/materials/*.txt --out /app/work/vardefs.json
python scripts/math_audit.py --crosscheck --catalog /app/work/catalog.json --varfile /app/work/vardefs.json
python scripts/math_audit.py --numeric "(3.18-1.42)/1.42*100"
```

## 示意输出

catalog.json（节选）：
```json
{"n_formulas": 1, "formulas": [{"id": "F001", "order": 1, "linear": "y = (a)/(b) x_{i}", "symbols": ["a","b","x","y"]}]}
```

crosscheck：
```json
{"symbols_missing_definition": [], "definitions_not_in_formulas": ["i"], "n_formula_symbols": 4, "n_defined": 3}
```
（i 为下标索引，属常识补充——入变量表 class=常识补充；crosscheck 的 unused 提示仅作参考。）

numeric：
```json
{"expr": "(3.18-1.42)/1.42*100", "value": 123.94366197183098, "error": null}
```
