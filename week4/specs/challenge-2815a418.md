# 交付标准 · challenge-2815a418 审稿回复与论文修改：完成产物，也保留来源

## 核心问题定义
题面四件事：答得全（每条意见及多个子要求都有明确处理结论）、改得准（"已修改"定位能在指定版本稿件中找到）、证得住（补实验/数据/文献有证据或替代说明）、对得上（回复信、修改稿、版本三者一致，多轮承诺可复核）。为事实、数字和引用保留来源或修改记录；材料不足、冲突、需人工确认的内容明确标注。

## 答题过程设计
probe → extract → respond 台账：意见拆解（子要求级）→ 逐条决策（adopt/partial/rebut/cannot_do + 理由 + 四档语气）→ 修改锚点（quote+locator）→ 证据清单（status+source）→ consistency 对修订稿逐锚点验证（unanswered/bad_anchors/open_evidence）→ 回复信 → emit。

## 交付物清单（week4/Academic Review/challenge-2815a418/v2/）
SKILL.md（含"四件事"对齐）、run.py、selftest.py、arkit/（11 模块，本题主力 respond/locate/findings/report）、hk/、examples/、GITHUB_URL.txt。案例交付：response_letter.md、response_ledger.json、consistency.json。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（respond demo 演示未答子要求与伪造"已修改"被抓出）
- 合规：22 文件 / ~116KB / hk.compliance.check_skill ok=true
- 真实可运行引擎，非模板壳；不含预制答案
