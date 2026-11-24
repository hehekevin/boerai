---
name: format-spec-forge
description: 模板规格逐项提取（栏数/字号/行距/页边距/层级/题注/文献样式/导出）、逐项符合核对、转换完整性（无删除合并图片化）、交付可用（字体嵌入/页码目录/保留可编辑源）。
---

# format-spec-forge

## 核心原则（不可违反）
1. **认得准**：从模板文件与格式要求提取可逐项核对的规格——不凭经验；未声明项标"需确认"。
2. **排得对**：标题层级/编号/题注交叉引用/文献条目/页眉页脚逐项符合——不只外观相似。
3. **转得全**：正文/图表/公式/脚注/批注/修订/域代码/目录无删除/合并/改写/图片化。
4. **交得出**：文件可打开、字体嵌入、页码目录可用、保留可编辑源文件、他人可按记录复核。
5. **脚本先行**：extract/conform/completeness 恒为0模型请求。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 规格提取（0请求）：`python scripts/format_spec.py --extract template.json`
### 阶段2 逐项核对（0请求）：`python scripts/format_spec.py --conform doc.json spec.json`
### 阶段3 完整性校验（0请求）：`python scripts/format_spec.py --completeness before.json after.json`
### 阶段4 成文（1请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/format-spec-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 规格未声明 | 需确认清单，不凭经验 |
| 完整性LOST | 定位丢失项，禁止交付 |
| 字体缺失 | 回退记录防版式错乱 |

## 资源清单
scripts：format_spec.py + inspect_case + validate_result；references/rules.md；templates/result.schema.json；examples；README。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。