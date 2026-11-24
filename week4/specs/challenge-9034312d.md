# 交付标准 · challenge-9034312d 实验装置与技术路线图

## 核心问题定义
判断本课题是否做对，不看图画得多漂亮，而看三件事：图上的每个实体能否追溯到输入材料，实体之间的连接与先后顺序是否成立，交付物能否被别人打开、修改并复跑出同一张图。

可选择的突破方向：  
优先考虑以下五个方向，也允许提出其他具有明确科研价值的绘图问题。

## 答题过程设计（加载 Skill 的 Agent 在固定案例上执行）
1. `probe`：读取 /input/case.json 真实结构（键、output_contract、文件清单+sha256、任务文本），不凭字段名猜内容。
2. `extract`：把 PDF/CSV/XLSX/DOCX 抽成带页码/表行定位的文本与数据行；扫描件记录 error，不臆造。
3. 写 spec.json：实体—关系清单先行（每个元素绑逐字引文+定位），数值只来自数据表；编辑类任务按 source-preserving edit 规则重建。
4. `build`：渲染→导出（SVG/PDF/PNG/TIFF）→25 项自检→result.json（case_id + output_contract 全字段 + element_inventory + data_mapping + checks + sources + uncertainty + changes）。
5. `verify`：按 FAIL 项的 fix 修复，重跑到 fail=0；不能消除的写入 uncertainty，status 如实降级。

## 交付物清单（week4/Scientific Graphics/challenge-9034312d/v2/）
SKILL.md（含本题评分对齐表）、run.py、selftest.py、engine/（17 模块）、docs/（SPEC/CHECKS/METHOD/USAGE）、resources/（配色/关系语义/期刊预设）、examples/（5 类示例，标注为示例）、GITHUB_URL.txt。

## 验收标准（自测命令与结果）
- `python3 selftest.py` → 5/5 examples built cleanly（已运行通过）
- 合规：40 个文本文件 / ≤275KB 总量 / 无超 500KB 单文件 / 无软链 / 全 UTF-8 / frontmatter 含 name+description（已检查通过）
- 端到端：模拟案例 probe→extract→build 得 status=success、24 项检查全过、PDF 文字可抽取（引擎级，week3 已验证）
- 交付物为真实可运行引擎，非模板壳；不含预制答案
