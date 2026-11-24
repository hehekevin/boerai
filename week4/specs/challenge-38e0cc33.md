# 交付标准 · challenge-38e0cc33 科研绘图领域总课题

## 核心问题定义
完成题面要求的核心科研绘图任务并交付可复核成果。

## 答题过程设计（加载 Skill 的 Agent 在固定案例上执行）
1. `probe`：读取 /input/case.json 真实结构（键、output_contract、文件清单+sha256、任务文本），不凭字段名猜内容。
2. `extract`：把 PDF/CSV/XLSX/DOCX 抽成带页码/表行定位的文本与数据行；扫描件记录 error，不臆造。
3. 写 spec.json：实体—关系清单先行（每个元素绑逐字引文+定位），数值只来自数据表；编辑类任务按 source-preserving edit 规则重建。
4. `build`：渲染→导出（SVG/PDF/PNG/TIFF）→25 项自检→result.json（case_id + output_contract 全字段 + element_inventory + data_mapping + checks + sources + uncertainty + changes）。
5. `verify`：按 FAIL 项的 fix 修复，重跑到 fail=0；不能消除的写入 uncertainty，status 如实降级。

## 交付物清单（week4/Scientific Graphics/challenge-38e0cc33/v2/）
SKILL.md（含本题评分对齐表）、run.py、selftest.py、engine/（17 模块）、docs/（SPEC/CHECKS/METHOD/USAGE）、resources/（配色/关系语义/期刊预设）、examples/（5 类示例，标注为示例）、GITHUB_URL.txt。

## 验收标准（自测命令与结果）
- `python3 selftest.py` → 5/5 examples built cleanly（已运行通过）
- 合规：40 个文本文件 / ≤275KB 总量 / 无超 500KB 单文件 / 无软链 / 全 UTF-8 / frontmatter 含 name+description（已检查通过）
- 端到端：模拟案例 probe→extract→build 得 status=success、24 项检查全过、PDF 文字可抽取（引擎级，week3 已验证）
- 交付物为真实可运行引擎，非模板壳；不含预制答案
