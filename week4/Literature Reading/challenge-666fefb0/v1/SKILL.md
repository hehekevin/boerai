---
name: lit-classify-forge
description: 文献与资料自动分类。目录层级分类（跨主题主分类+副标签带依据），标签生成（粒度受控/同义合并/停用词防爆炸），约定模板自动命名（特殊字符/超长/多语言/缺字段降级），版本区分（哈希+DOI+标题作者年份识别重复；预印本vs正式版；归档不删除防误删）。触发词：自动分类、标签、命名、版本去重。
---

# lit-classify-forge — 文献与资料自动分类

一句话：**分类带依据、标签控粒度、命名有降级、版本只归档。**

## 核心原则（不可违反）

1. **分类带依据**：按项目/主题/文献类型/年份维度建层级；跨主题文献主分类+副标签，每条归属带命中关键词依据。
2. **标签控粒度**：每文档上限5个标签；同义合并(casefold)；停用词过滤（研究/方法/paper等）——避免标签爆炸。
3. **命名有降级**：约定模板（作者-年份-标题/DOI/期刊缩写）生成文件名；特殊字符替换、超长截断、多语言保留Unicode、缺失字段NA占位——降级规则显式记录。
4. **版本防误删**：哈希+DOI+标题作者年份三重识别重复；区分预印本/正式版/补充材料/修订版；**归档而非删除**。
5. **脚本先行**：四子命令恒为0模型请求。

## 工作流程

### 阶段 0：盘点（1次请求）
```bash
python <SKILL_DIR>/scripts/inspect_case.py /input/case.json > /app/work/00_inventory.txt
```

### 阶段 1：分类（0请求 + 1次请求补充分类法）
```bash
python <SKILL_DIR>/scripts/classify_engine.py --classify <记录.json> <分类法.json> > /app/work/classified.json
```
分类法树由模型按资料集补充（keywords 由题面上下文定）。

### 阶段 2：标签生成（0请求）
```bash
python <SKILL_DIR>/scripts/classify_engine.py --tags <记录.json> > /app/work/tags.json
```

### 阶段 3：自动命名（0请求）
```bash
python <SKILL_DIR>/scripts/classify_engine.py --rename <记录.json> "{authors}_{year}_{title}" > /app/work/names.json
```

### 阶段 4：版本去重（0请求）
```bash
python <SKILL_DIR>/scripts/classify_engine.py --versions <记录.json> > /app/work/versions.json
```

### 阶段 5：成文与交付（约1-2次模型请求）
组装 result.json（合并 output_contract + case_id）。核验：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/classify-report.md --require "分类|classify|层级|taxonomy,标签|tag|粒度,命名|rename|文件名,版本|version|重复|去重" --names "classify,tags,rename,versions"
```

## 异常处置速查

| 情形 | 处置 |
|-|-|
| 无分类法输入 | 骨架+模型按资料集补充，标注待确认 |
| 全部未分类 | 分类法关键词与资料集不匹配→报告并建议调整 |
| 命名冲突（同名文件） | 追加 idx 后缀 |
| 预算不足 | classified.json 先落盘 status=partial |

## 资源清单
- `scripts/classify_engine.py` — classify/tags/rename/versions（确定性引擎）
- `scripts/file_search.py` — 文件定位辅助
- `scripts/inspect_case.py`、`scripts/validate_result.py`
- `references/classify-rules.md`、`templates/result.schema.json`
- `examples/minimal-example.md`、`README.md`

## 预算红线
64 模型请求/900秒。四子命令恒为0请求。过60%时间冻结。