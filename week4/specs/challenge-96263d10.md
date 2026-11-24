# 规格说明：challenge-96263d10（学术格式与模板适配）

## 选定问题
选题：模板规格抽取成检查项 + 转换保真比对（认得准 + 排得对 + 转得全）。

## 引擎机制映射（awkit 模块 → 用途）
- `formatcheck`：层级/编号/字数/参考文献字段顺序/作者截断逐项核对
- `citecheck`：重排后引用键仍可解析
- `revisions`：格式改动锚定留痕
- `claims`：句级 id 用于保真比对基线
- `hk.extract`：模板与稿件抽取

## 输入 / 输出
输入：稿件+模板/格式规定（字体：Liberation Serif）；输出：adapted.md、spec.json、format_before/format.json、fidelity.json、result.json

## 验收标准（机械可核）
- spec 每条注明来源
- violations 清零
- 未登记的内容差异视为丢失
- 字体回退如实记录

## 通用约束
- 纯 stdlib；python-pptx/matplotlib/LibreOffice 仅作 try/except 增强，不可用时有诚实兜底。
- 中间产物全部落盘 JSON 于 /app/work；result.json 含 case_id 与全部 output_contract 键。
- ≤50 文件 / ≤2MB / 无符号链接 / SKILL.md frontmatter 合法 / GITHUB_URL.txt 首行 GitHub 链接。