---
name: ppt-gen-edit-forge
description: PPT生成（内容取舍/页序/叙事角色）与编辑（压缩/扩写/换受众/换语言，术语与论文一致）、图表插入（重绘vs引用原图）、多轮迭代（版本比对/回退）。
---

# ppt-gen-edit-forge

## 核心原则（不可违反）
1. **面生成**：从正文/结果段/提纲出发做内容取舍与页序规划；每页明确叙事角色。
2. **容编辑**：压缩/扩写/换受众（导师/评审/同行）/换语言改写；术语/符号与论文一致。
3. **表插入**：还原图表处理图注/编号/单位/引用；有底层数据才可重绘，否则只引用原图。
4. **稿迭代**：多轮修改版本可比对——每轮改了什么/为什么/改坏如何回退（rollback_point）。
5. **脚本先行**：edit/fit-template 恒为0模型请求。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 生成骨架（0请求）：`python scripts/ppt_engine.py --outline paper.json`
### 阶段2 编辑操作（0请求+1-2请求改写）：`python scripts/ppt_engine.py --edit slides.json ops.json`
### 阶段3 图表槽位（0请求）：`python scripts/ppt_engine.py --figures paper.json`
### 阶段4 模板适配（0请求）：`python scripts/ppt_engine.py --fit-template slides.json template.json`
### 阶段5 成文（1请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/ppt-gen-edit-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 未知action | unknown_action 记录不执行 |
| 术语漂移 | glossary 校验 |
| 版本冲突 | rollback_point 链 |

## 资源清单
scripts：ppt_engine.py + inspect_case + validate_result；references/rules.md；templates/result.schema.json；examples；README。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。