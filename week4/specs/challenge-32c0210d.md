# 规格说明：challenge-32c0210d（学位论文与长文档写作）

## 选定问题
选题：跨章节一致性与可追溯改稿（连得上 + 改得动 + 查得清）。

## 引擎机制映射（awkit 模块 → 用途）
- `claims`：strict 模式逐句绑定，数字一致性
- `bilingual`：术语表机械套用，同一概念同一写法
- `citecheck`：引用键解析、条目字段、编号连续
- `formatcheck`：标题层级/编号/分节字数
- `revisions`：导师意见拆操作、锚点唯一、drift_warning、可回退
- `structcheck`：跨节重复、无支撑结论、循环论证
- `coverage`：提纲要点覆盖

## 输入 / 输出
输入：提纲/章节/文献/意见；输出：thesis.md、plan.json、terms.json、各校验报告、changes.json、result.json

## 验收标准（机械可核）
- 全套校验通过才 success
- 材料不足走【材料不足】标注 + partial
- 每条改动留 before/after/reason

## 通用约束
- 纯 stdlib；python-pptx/matplotlib/LibreOffice 仅作 try/except 增强，不可用时有诚实兜底。
- 中间产物全部落盘 JSON 于 /app/work；result.json 含 case_id 与全部 output_contract 键。
- ≤50 文件 / ≤2MB / 无符号链接 / SKILL.md frontmatter 合法 / GITHUB_URL.txt 首行 GitHub 链接。