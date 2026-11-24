# 问题驱动检索规则（qdriven-rules.md）

## 1. 六要素矩阵
| 槽位 | 提取目标 | 缺失处置 |
|-|-|-|
| object | 研究对象（人群/材料/系统） | 模型补充 basis=model |
| mechanism | 机制/现象/任务 | 同上 |
| method | 方法/技术/算法 | 同上 |
| time_range | 年份区间 | N/A 合法（不限时间） |
| comparison | 比较关系 | N/A 合法（无对照研究） |
| evidence | 证据类型要求 | 同上 |

## 2. 组合模板
R1-core = object AND mechanism AND method（前三要素）
R1-broad = object OR mechanism（兜底召回）
时间窗作为独立 AND 条件追加。

## 3. 多轮协议
R1→评估→R2（同义词扩展+字段放宽）→评估→R3（缺口驱动）。每轮调整理由入台账。

## 4. 停止判据
最后轮新增=0 / 轮次>=5 / 证据充分（>=2轮且有实质命中且无缺口）→ 停止；4轮以上未停→human_needed。

## 5. 异常处置
见 SKILL.md 异常表。