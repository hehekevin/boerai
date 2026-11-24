# multidb-union-search-forge — 使用与方法说明

**各库各语法、字段有映射、合并留裁决、来源可回溯、失败即披露。**

## 调用
--demo（内置演示）/ --merge（合并）/ --degrade（降级报告）。方言适配表与优先级表见 references。

## 关键方法
FIELD_MAP 跨库映射（missing/unknown 区分）→ 合并键（DOI优先）→ 字段级裁决留痕 → 降级披露。已知限制：仅大小写差异可能误计冲突。

## 维护
版本 1.0.0（2026-11），作者 dafeiyu。