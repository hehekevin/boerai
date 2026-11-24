# 规格说明：ppt-c7b80f0d（论文转学术 PPT）

## 选定问题
选题：主线提取 + 页级引用定位 + 备注分离生成（转换是结构重写的机械保证）。

## 引擎机制映射（awkit 模块 → 用途）
- `structcheck`：问题-做法-证据-结论链
- `deck`：evidence 挂页、数字/单位字面一致、备注复读拦截、页数上限
- `hk.extract`：PDF 带页码抽取

## 输入 / 输出
输入：论文（+模板/页数）；输出：deck.pptx、outline.json（页级金标准）、deck_check.json、preview/、result.json

## 验收标准（机械可核）
- 图号与 evidence.loc 一致
- 数值单位不改写
- 备注提供页面外信息
- 可复跑同一版式

## 通用约束
- 纯 stdlib；python-pptx/matplotlib/LibreOffice 仅作 try/except 增强，不可用时有诚实兜底。
- 中间产物全部落盘 JSON 于 /app/work；result.json 含 case_id 与全部 output_contract 键。
- ≤50 文件 / ≤2MB / 无符号链接 / SKILL.md frontmatter 合法 / GITHUB_URL.txt 首行 GitHub 链接。