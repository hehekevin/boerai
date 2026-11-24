# search-general-forge — 使用与方法说明

**全链路编排、六子场景可独立复跑、每条结果带依据、遗漏必说明。**

## 调用
三个子引擎（search_audit/screening_engine/iter_loop）按 case.json 路由执行；路由规则见 references/general-rules.md。

## 关键方法
盘点→路由→子引擎执行（0请求）→综合成文→契约校验。四步保底（范围/流程/依据/异常说明）。

## 维护
版本 1.0.0（2026-11），作者 dafeiyu。