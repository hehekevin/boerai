# 规格说明：challenge-a2c6f23b（学术写作领域总课题）

## 选定问题
选题：来源保真写作通用管线（完成产物，也保留来源）——全部 9 模块的质量门组合。

## 引擎机制映射（awkit 模块 → 用途）
- `claims`：句级绑定+数字一致性（核心）
- `coverage`：必需要点/章节
- `citecheck`：引用完整性
- `bilingual`：双语术语
- `formatcheck`：格式
- `revisions`：改稿留痕
- `structcheck`：论证链
- `deck`：结构化产物为幻灯片时
- `scorecard`：需要评测时

## 输入 / 输出
输入：事实底稿+约束；输出：draft.md、claims_report.json、coverage/citecheck/format、quality_gate.json、result.json

## 验收标准（机械可核）
- 质量门全绿才 success
- 诚实【材料不足】路径 demo 覆盖
- 不新增材料外事实

## 通用约束
- 纯 stdlib；python-pptx/matplotlib/LibreOffice 仅作 try/except 增强，不可用时有诚实兜底。
- 中间产物全部落盘 JSON 于 /app/work；result.json 含 case_id 与全部 output_contract 键。
- ≤50 文件 / ≤2MB / 无符号链接 / SKILL.md frontmatter 合法 / GITHUB_URL.txt 首行 GitHub 链接。