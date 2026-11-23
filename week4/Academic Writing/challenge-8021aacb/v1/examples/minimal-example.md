# 最小调用示例（示例数据，非正式案例结果）

## 调用

```bash
python scripts/structure_audit.py --outline manuscript.md --out outline.json
python scripts/structure_audit.py --dup manuscript.md --out dups.json
python scripts/structure_audit.py --claims manuscript.md --out claims.json
# （模型：诊断与动作 -> diagnosis-report.md / edit-actions.json）
python scripts/validate_result.py --case /input/case.json --result result.json --manuscript diagnosis-report.md --require "位置,章节|动作,action|依据,原文" --names "diagnosis,actions,evidence"
```

## 示意诊断（节选）

```markdown
D1 [重复衔接] 第2.3节 段2 与 第4.2节 段1 重复（overlap=0.62，dups.json#1）
依据：两段均表述"小样本条件下精度下降明显"。
动作：MERGE — 保留 4.2 表述，2.3 改为一句回指"（详见 4.2）"。
```
```json
{"id":"A1","type":"MERGE","target":"2.3 段2","with":"4.2 段1","after":"2.3 段2 替换为回指句"}
```
