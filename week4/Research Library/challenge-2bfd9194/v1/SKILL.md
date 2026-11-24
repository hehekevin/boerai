---
name: lib-manager-forge
description: 科研资料库与文件管理：批量上传（哈希一致/断点续传/特殊字符/压缩包展开）、目录组织（约定树/归位/去重/空目录清理/命名规范）、元数据维护（多来源抽取带出处）、版本管理（哈希+修改时间重建版本链）。
---

# lib-manager-forge

## 核心原则（不可违反）
1. **件上传**：批量/断点续传/大文件/特殊字符/压缩包展开；入库文件与源文件哈希一致（sha256逐个核对）。
2. **录组织**：按项目/年份/数据类型约定生成目录树；归位/去重/空目录清理/命名规范化（classify_engine --rename）。
3. **据维护**：从文件名/内容/伴随表格/人工补录抽取字段形成结构化清单，字段出处保留（clean_engine --normalize trace）。
4. **本管理**：内容哈希+修改时间重建版本链；明确谁替代谁、差异在哪——归档不删除（classify_engine --versions）。
5. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 入库校验（0请求）：哈希核对+压缩包展开清单
### 阶段2 目录组织（0请求）：`python scripts/classify_engine.py --classify/--rename`
### 阶段3 元数据维护（0请求）：`python scripts/clean_engine.py --normalize`
### 阶段4 版本链（0请求）：`python scripts/classify_engine.py --versions`
### 阶段5 成文（1请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/lib-manager-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 哈希不一致 | 上传失败清单重传 |
| 特殊字符文件名 | 规范化+原名保留记录 |
| 版本冲突 | 链上标注替代关系 |
| 空目录 | 清理清单（不删资料文件） |

## 资源清单
scripts：classify_engine.py, clean_engine.py, file_search.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。