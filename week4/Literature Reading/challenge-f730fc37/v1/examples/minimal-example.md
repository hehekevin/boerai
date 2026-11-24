# 最小调用示例（示例数据，非正式案例结果）

## 阅读客户端

```bash
python scripts/inspect_case.py /input/case.json
# python scripts/reader_workflow.py ...
python scripts/validate_result.py --case /input/case.json --result result.json --manuscript report.md --require "..." --names "..."
```

引擎各子命令输出为合法 JSON（schema 标注），自测已通过；示例值见 references/rules.md。