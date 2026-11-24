# 多文档比较规则（compare-rules.md）

## 1. 七字段统一定义
research_object/data_source/method/conditions/metrics/main_result/limitations。抽取时记录取值规则与原文位置。

## 2. 可比性
条件描述一致→full；差异→subset_only（子集清单）。指标口径不同（accuracy vs AUC）→不可直接数值比较。

## 3. 冲突归因
方向冲突（提高vs降低）→归因候选=有差异的字段；模型按原文裁决具体差异（样本量/方法/条件/口径）。

## 4. 异常处置
见 SKILL.md 异常表。