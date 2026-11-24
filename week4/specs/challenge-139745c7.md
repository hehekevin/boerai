# 交付标准 · challenge-139745c7 科研文件智能检索：科研资料管理：整理文件，也保留版本关系

## 核心问题定义
本课题聚焦跨文件语义检索、章节定位、过滤条件和证据回链，要求把一个真实、高频、可检查的任务做成可复跑的 Benchmark，或做成可运行的 Skill、插件或轻量工作流。

## 答题过程设计
probe → extract → lskit 模块处理（filesearch）→ emit（result.json 含 case_id+output_contract 全字段）。语义判断由 Agent 完成并落盘 JSON；匹配/计数/差异/停止判据由引擎确定性完成。

## 交付物清单（week4/Literature Search/challenge-139745c7/v2/）
SKILL.md、run.py、selftest.py、lskit/（10 模块）、hk/、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 11/11 checks pass（已运行）
- 合规：21 文件 / ≤94KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
