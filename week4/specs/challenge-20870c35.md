# 规格说明：challenge-20870c35（学术汇报内容组织）

## 选定问题
选题：页级证据映射 + 听众/时长约束下的叙事组织（页面论断可溯源、取舍可复核）。

## 引擎机制映射（awkit 模块 → 用途）
- `deck`：outline 校验（claim/要点/备注/证据/页数）、可编辑 PPTX、PNG/PDF 真渲染
- `structcheck`：汇报主线论断-证据链，结论必挂支撑
- `claims`：页面数字字面一致性规则同源复用
- `coverage`：主线必需环节（问题/方法/结果/结论）覆盖

## 输入 / 输出
输入：论文/材料+听众+时长+页数+模板；输出：deck.pptx、outline.json、deck_check.json、preview/、qa.json、result.json

## 验收标准（机械可核）
- content 页无证据即拒
- 页面数字必须字面命中证据
- 备注复读即拒
- 预览真实生成或如实 unavailable

## 通用约束
- 纯 stdlib；python-pptx/matplotlib/LibreOffice 仅作 try/except 增强，不可用时有诚实兜底。
- 中间产物全部落盘 JSON 于 /app/work；result.json 含 case_id 与全部 output_contract 键。
- ≤50 文件 / ≤2MB / 无符号链接 / SKILL.md frontmatter 合法 / GITHUB_URL.txt 首行 GitHub 链接。