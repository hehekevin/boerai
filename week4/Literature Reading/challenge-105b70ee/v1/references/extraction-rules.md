# 提取规则（extraction-rules.md）

## 1. 结论三档触发词
| 档 | 触发 |
|-|-|
| 明确结论 | we show/demonstrate/achieved/outperform/结果表明 |
| 限制条件 | limitation/however/only/受限于/样本量小 |
| 推测表述 | may/might/suggest/可能/提示/有望 |

## 2. 数值五要素
value + unit + error± + stat_sig + conditions。unit缺失→missing_unit；上下文含p值/significant→stat_sig记录。

## 3. 条件抽取五类
样本(n=)/实验设置(batch/lr/epochs)/数据来源(dataset/来自)/比较基线(baseline/相比)/时间点。

## 4. 噪声过滤
纯小数字（<10且无单位无误差无显著性）跳过。

## 5. 锚点规范
para_no + section；locate 校验所有抽取项必须带锚点。

## 6. 异常处置
见 SKILL.md 异常表。