# 规格说明：challenge-8021aacb（论文结构与逻辑优化）

## 选定问题
选题：论点-论据映射 + 可执行编辑动作的结构诊断（诊得准 + 改得动）。

## 引擎机制映射（awkit 模块 → 用途）
- `structcheck`：claims/facts 定位校验、结论闭环、循环检测、跨节重复 12-gram、结论尺度词标记
- `coverage`：研究问题提出-贯穿-贡献对齐核对
- `revisions`：edit_plan 的 move/merge/split/narrow 动作可落地执行并留痕
- `claims`：收窄改写后数字仍需绑定

## 输入 / 输出
输入：完整稿件；输出：diagnosis.md、edit_plan.json、struct.json、chain.json、result.json（JSON/Markdown 即可）

## 验收标准（机械可核）
- 每条诊断挂原文 evidence（子串校验）
- 六维分类固定
- 动作仅限可执行级
- 不虚构缺陷

## 通用约束
- 纯 stdlib；python-pptx/matplotlib/LibreOffice 仅作 try/except 增强，不可用时有诚实兜底。
- 中间产物全部落盘 JSON 于 /app/work；result.json 含 case_id 与全部 output_contract 键。
- ≤50 文件 / ≤2MB / 无符号链接 / SKILL.md frontmatter 合法 / GITHUB_URL.txt 首行 GitHub 链接。