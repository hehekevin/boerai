# recent-lit-tracker-forge — 使用与方法说明

**水位定增量、快照定基线、窗口防漂移、重试保幂等、版本可复算。**

## 调用
--baseline / --dedupkeys / --window / --retrylog 四子命令。

## 关键方法
快照diff（new/updated/removed三分类）→ 去重键碰撞检测 → 窗口边界规则 → 幂等重试审计。

## 维护
版本 1.0.0（2026-11），作者 dafeiyu。