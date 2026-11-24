# iterative-search-agent-forge — 使用与方法说明

**每轮留台账、停止有判据、回退保证据、介入可追溯。**

## 调用
--ledger（构建台账）/ --stop（四类停止判据）/ --rollback（回退点）。参数：--target-coverage/--gain-threshold/--budget-minutes/--max-rounds。

## 关键方法
确定性引擎0请求；marginal_gain=新增命中/成本；连续2轮零收益标记回退；HUMAN: 行标记介入点。

## 边界
适用：检索/爬取类迭代闭环。不适用：一次性任务。

## 维护
版本 1.0.0（2026-11），作者 dafeiyu。