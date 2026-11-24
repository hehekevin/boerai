# 示例（合成数据，非正式案例结果）

`python3 ../selftest.py` 会运行：

- 8 个引擎模块的 `_demo()`（每个 demo 自带合成数据与断言，含负例：无回链断言、
  "尚存争议"式搪塞裁决、幻影年份趋势、无检索依据的空白主张均被拒绝）；
- 一次端到端：合成 case.json + 两篇合成文献文本 → probe → extract →
  `qplan validate` → `evidence validate/conflicts` → `synthesis audit` →
  emit → `result.json`（含 case_id 与 output_contract 全字段）。

典型手工流程（真实案例，工作目录 /app/work）：

```bash
export SKILL="${SKILL_DIR:-/skills/weekly-skill}" WORK=/app/work OUT=/app/output
python "$SKILL/run.py" probe   --case /input/case.json --input /input --out "$WORK"
python "$SKILL/run.py" extract --work "$WORK"
# Agent 语义产物落盘：plan.json / queries.json+ledger.json / decisions.json /
# matrix.json / synthesis.json / gaps.json（模板见各题 SKILL.md）
python "$SKILL/run.py" qplan     validate plan.json plan_check.json
python "$SKILL/run.py" iterloop  signals  ledger.json
python "$SKILL/run.py" screen    validate records.json decisions.json screen_check.json
python "$SKILL/run.py" evidence  validate matrix.json matrix_check.json
python "$SKILL/run.py" evidence  conflicts matrix.json conflict_check.json
python "$SKILL/run.py" synthesis audit synthesis.json matrix.json synthesis_audit.json plan.json
python "$SKILL/run.py" gaps      map plan.json queries.json evidence.json coverage.json
python "$SKILL/run.py" gaps      validate gaps.json coverage.json gaps_check.json
python "$SKILL/run.py" trendstat yearly records.json yearly.json
python "$SKILL/run.py" trendstat audit trend_claims.json yearly.json topics.json trend_check.json
python "$SKILL/run.py" emit --work "$WORK" --out "$OUT" --status success \
    --artifact report=$WORK/report.md --artifact evidence_matrix=$WORK/matrix.json
```

所有演示数据仅为接口演示而构造，不得作为正式测试案例结果引用。
