# 排序规则（ranking-rules.md）

## 1. 权重表（显式可复算）
relevance_terms 0.45 / recency 0.25 / venue 0.20 / study_type 0.10
recency = (year-2015)/11 截断到[0,1]；study_type 研究型1.0 其他0.4。

## 2. 标签分层
| 层 | 判据 | 处置 |
|-|-|-|
| core_evidence | >=0.6 | 核心证据 |
| method_reference | 0.4-0.6 | 方法参考 |
| background | 0.2-0.4 | 背景资料 |
| exclude_candidate | <0.2 | 待人工复核，不直接删除 |

## 3. 冲突处理
same_study_multi_report→合并保留正式版；preprint_version→标记待替换；标注分歧→人工复核。

## 4. 并列与同分
年份新→旧，再标题字典序；规则显式声明。

## 5. 异常处置
见 SKILL.md 异常表。