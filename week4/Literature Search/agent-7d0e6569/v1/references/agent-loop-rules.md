# 迭代闭环规则（agent-loop-rules.md）

## 1. 轮次台账（强制）
每轮记录：round/query/db/hits_raw/cost_min/cum_unique_est/marginal_gain。缺 hits 的轮次 marginal_gain=null 且不参与停止判据。

## 2. 停止判据（四类）
| 类型 | 判据 | 说明 |
|-|-|-|
| coverage | cum_unique/expected_corpus >= 目标% | 覆盖度达标 |
| marginal_gain | 最后轮 新增命中/成本 < 阈值 | 补检收益趋零 |
| budget | 累计耗时 >= 预算 | 预算耗尽 |
| max_rounds | 轮次 >= 上限 | 防无限循环 |
人工介入点（HUMAN: 前缀行）出现时单独列出，不计入自动停止。

## 3. 回退协议
连续2轮边际收益=0 → 回退到最后一个有收益轮次；命中集与查询式全部保留（证据不丢弃）；换用备用路径时记录切换原因。

## 4. 人工介入协议
触发器：连续失败3次/敏感领域/规则歧义。转交材料：当前台账+已获证据+待决问题。人工判断以 HUMAN: 行回写台账，介入点可统计。

## 5. 异常处置
日志损坏→重建标注；hits缺失→null处理；无介入点→如实报告。
