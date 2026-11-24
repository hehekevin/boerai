---
name: browser-ext-forge
description: 学术浏览器插件：详情页/预印本/PDF阅读器稳定读取（懒加载/分页/多标签）、章节图表编号或文本指纹定位（重开/缩放/换设备可复现）、引用收集（字段规范/DOI校验/批量去重入库）、受控多步操作（状态保持/中断续作）。
---

# browser-ext-forge

## 核心原则（不可违反）
1. **文浏览**：出版商详情页/预印本/PDF阅读器稳定读取标题/作者/摘要/正文结构与图表——懒加载/分页渲染/多标签处理（content_extract --extract）。
2. **面定位**：章节号/图表编号/文本指纹定位——重新打开/缩放/换设备后仍可复现（file_search --locate 逻辑）。
3. **用收集**：可见信息+元数据抽取规范字段；作者缩写/期刊名变体/DOI校验；批量收集去重+本地库写入（multidb_engine 字段映射+classify --versions 去重）。
4. **作增强**：结构查看器/检索页/投稿系统受控多步操作——状态保持中断可续（sw_agent --plan 步骤序列）。
5. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 页面正文识别（0请求）：`python scripts/content_extract.py --extract page.html`
### 阶段2 定位（0请求）：`python scripts/file_search.py --locate`
### 阶段3 引用收集（0请求）：`python scripts/multidb_engine.py --merge`（字段标准化+去重）
### 阶段4 受控操作（0请求）：`python scripts/sw_agent.py --plan/--gates`
### 阶段5 成文（1-2请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/browser-ext-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 懒加载未完成 | gaps 声明未读取区域 |
| DOI校验失败 | 标记不入库 |
| 操作中断 | 状态快照续作 |

## 资源清单
scripts：content_extract.py, file_search.py, multidb_engine.py, sw_agent.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。