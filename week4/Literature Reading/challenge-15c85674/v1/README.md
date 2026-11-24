# literature-qa-forge — 使用与方法说明

**跨语言检索定位证据、逐题作答附锚点、条件不丢、不确定不编。**

## 调用
--index / --retrieve / --scaffold / --uncertainty 四子命令。

## 关键方法
ZH_EN_MAP 跨语言扩展→段落评分检索（Results加权）→子问拆分脚手架→不确定性五类审计。修复记录：zh词典须对原文匹配（非bigram）。

## 边界
适用：带段落编号的论文问答。不适用：PDF解析/图像识别/联网。

## 维护
版本 1.0.0（2026-11），作者 dafeiyu。