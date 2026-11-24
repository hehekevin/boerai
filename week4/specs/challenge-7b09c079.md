# 规格说明：challenge-7b09c079（学术写作客户端）

## 选定问题
选题：修订级粒度控制与改后格式自检（改得准 + 改得可追溯 + 格式不塌）。

## 引擎机制映射（awkit 模块 → 用途）
- `revisions`：锚点恰好命中一次才执行；accept/reject/回退；相似度 drift_warning
- `claims`：改后受影响句重查事实绑定
- `citecheck`：引用域变动后编号与条目同步复检
- `formatcheck`：改后标题层级/编号不塌
- `hk.extract`：docx 等稿件抽文本并冻结原稿哈希

## 输入 / 输出
输入：稿件+修改指令+文献库；输出：draft_v2.md、ops.json、changes.json、claims_recheck.json、postcheck.json、result.json

## 验收标准（机械可核）
- 无锚点修改不执行
- 锚点失效/不唯一被拒并记录
- 改后三检（claims/citecheck/format）合成 postcheck

## 通用约束
- 纯 stdlib；python-pptx/matplotlib/LibreOffice 仅作 try/except 增强，不可用时有诚实兜底。
- 中间产物全部落盘 JSON 于 /app/work；result.json 含 case_id 与全部 output_contract 键。
- ≤50 文件 / ≤2MB / 无符号链接 / SKILL.md frontmatter 合法 / GITHUB_URL.txt 首行 GitHub 链接。