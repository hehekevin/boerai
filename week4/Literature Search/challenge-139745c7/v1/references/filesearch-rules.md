# 文件检索规则（filesearch-rules.md）

## 1. 排序公式
score = filename_hits×3 + content_hits。文件名命中权重高（作者意图明确）。

## 2. 证据回链格式
{file_path, line_no, section_heading, section_line, excerpt}——每项可独立验证。

## 3. 硬过滤语义
ext/name_contains/year/content_contains 逐条 AND；不满足的过滤器记录到 unsatisfiable_filters（含原因），绝不放宽。

## 4. 版本识别
内容 sha256 相同=副本；文件名含 v\d+/final/old/copy/备份/旧版=疑似版本变体。旧版本不作为独立证据。

## 5. 异常处置
见 SKILL.md 异常表。