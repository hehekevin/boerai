# 规格说明：benchmark-d57ad64a（学术写作 Benchmark 与评测工具）

## 选定问题
选题：评分锚点与双评一致性（锚点打得齐 + 报告说得清），兼顾题集设计与运行复现。

## 引擎机制映射（awkit 模块 → 用途）
- `scorecard`：锚点=可观察现象 lint、0/1/2 评分合法性、双评 agreement、裁定只修锚点不改分、逐题报告
- `claims`：参考答案自身的事实-来源绑定验证（答案站得住）
- `coverage`：题面必需要点结构化，作为锚点与完成判定的分母
- `hk.probe`：冻结输入 sha256，支撑运行复现

## 输入 / 输出
输入：题面/待评稿件/既有锚点；输出：tasks.json、anchors.json、ratings.json、agree.json、eval_report.md、result.json

## 验收标准（机械可核）
- lint-anchors 拒绝空泛锚点
- 非法评分被拒
- 分歧>1档必须裁定
- 报告分数可从 ratings 复算
- selftest 全绿

## 通用约束
- 纯 stdlib；python-pptx/matplotlib/LibreOffice 仅作 try/except 增强，不可用时有诚实兜底。
- 中间产物全部落盘 JSON 于 /app/work；result.json 含 case_id 与全部 output_contract 键。
- ≤50 文件 / ≤2MB / 无符号链接 / SKILL.md frontmatter 合法 / GITHUB_URL.txt 首行 GitHub 链接。