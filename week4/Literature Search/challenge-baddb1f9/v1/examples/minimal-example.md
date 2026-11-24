# 最小调用示例（示例数据，非正式案例结果）

## 调用（路由到覆盖率审计子场景）
```bash
python scripts/inspect_case.py /input/case.json
python scripts/search_audit.py --coverage refs.tsv results.tsv
python scripts/search_audit.py --classify refs.tsv results.tsv
python scripts/screening_engine.py --screen refs.tsv criteria.json
python scripts/validate_result.py --case /input/case.json --result result.json --manuscript report.md --require "范围,依据,遗漏,候选" --names "scope,evidence,misses,candidates"
```
