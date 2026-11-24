# 清洗规则（cleaning-rules.md）

## 1. 规则库（编号+优先级）
| 规则 | 优先级 | 适用 | 失效 |
|-|-|-|-|
| R1 字段改名 | 1 | 映射表内列名 | 未映射→unmapped清单 |
| R2 类型转换 | 2 | 数值型字符串 | 失败保留原值+cast_failed |
| R3 枚举归一 | 3 | 枚举字段 | 未知值保留+标记 |
| R4 缺失/未知 | 4 | 全字段 | 无 |

## 2. 单位换算表
percent/%→ratio(×0.01)、mg→g(×0.001)、kg→g(×1000)、mL→L、mm/cm→m、min/h→s。未收录（如kPa）→needs_manual。复合单位逐段换算；区间值分别转换。

## 3. 合并判定键
同物质(material/substance)+同实验标识(experiment_id)才合并；键字段缺失→独立记录。冲突字段全部保留。

## 4. 追溯规范
trace记录：{rule_id, row, field, change, old/new}。审计FAIL条件：缺rule_id或缺row。

## 5. 异常处置
见 SKILL.md 异常表。