---
name: ppt-template-forge
description: 母版/版式/占位符识别与正确套用（缺失替代）、版心内定位对齐（溢出阶梯）、中英字体/主题色/对比度/字体缺失回退、图表等比缩放（坐标轴图例可读/矢量位图混排）。
---

# ppt-template-forge

## 核心原则（不可违反）
1. **板套用**：识别母版/版式/占位符结构；内容写入正确版式；保留主题字体与主题色；占位符缺失→正文版式替代并记录。
2. **式约束**：固定版心内定位对齐；文本框溢出/标题过长/多图并排/跨页一致——可解释的字号间距阶梯（28/18/12）。
3. **体颜色**：中英文字体搭配、字号层级、主题色与强调色、对比度与印刷可读性；字体缺失回退记录防错乱。
4. **表适配**：等比缩放或裁切保留坐标轴图例可读；统一编号与正文引用；矢量位图混排。
5. **脚本先行**：fit-template 恒为0模型请求。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 模板适配（0请求）：`python scripts/ppt_engine.py --fit-template slides.json template.json`
### 阶段2 溢出处理（0请求）：溢出清单+阶梯下移
### 阶段3 成文（1请求）

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/ppt-template-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 占位符缺失 | 正文版式替代+记录 |
| 文本溢出 | 阶梯降级/下移备注/拆页 |
| 字体缺失 | 回退字体记录 |

## 资源清单
scripts：ppt_engine.py + inspect_case + validate_result；references/rules.md；templates/result.schema.json；examples；README。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。