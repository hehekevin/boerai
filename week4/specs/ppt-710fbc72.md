# 规格说明：ppt-710fbc72（学术 PPT 模板与格式适配）

## 选定问题
选题：模板约束结构化 + 批量一致性巡检 + 导出一致性记录（真实套用可查证）。

## 引擎机制映射（awkit 模块 → 用途）
- `deck`：槽位约束校验、build、渲染
- `claims`：页内数字与源一致
- `formatcheck`：字号/字数阶梯思想同源用于 tpl_spec

## 输入 / 输出
输入：内容+模板（母版/版式/占位符/字体/页脚）；输出：deck.pptx、tpl_spec.json、conformance.json、preview/、result.json

## 验收标准（机械可核）
- 母版继承情况如实记录（未继承不掩饰）
- 整册逐项 pass/fail
- 导出差异逐页落记录

## 通用约束
- 纯 stdlib；python-pptx/matplotlib/LibreOffice 仅作 try/except 增强，不可用时有诚实兜底。
- 中间产物全部落盘 JSON 于 /app/work；result.json 含 case_id 与全部 output_contract 键。
- ≤50 文件 / ≤2MB / 无符号链接 / SKILL.md frontmatter 合法 / GITHUB_URL.txt 首行 GitHub 链接。