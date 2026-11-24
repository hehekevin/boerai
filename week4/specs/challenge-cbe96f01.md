# 交付标准 · challenge-cbe96f01 引用与事实核验：发现问题，也给出证据

## 核心问题定义
题面三件事：每条结论是否能指到具体原文位置；判定是否与引文语义一致；换一个人按记录复核能否得到同一批结论。核心是区分"引用存在"与"引用支持结论"：四态判定（完整支持/部分支持/不支持/无法判定），source 片段缺失时只能是"无法判定"，不臆断。

## 答题过程设计
probe → extract → audit 预扫描 → 抽取带引用论断为 pairs.json（source 只来自案例快照）→ crosscheck side-by-side 四态建议（内容词重叠 + claim_only/source_only）→ Agent 逐对确认 → consistency 摘要/正文/图表数字一致性 → 台账入册 → validate → report → emit。

## 交付物清单（week4/Academic Review/challenge-cbe96f01/v2/）
SKILL.md（含"三件事"对齐）、run.py、selftest.py、arkit/（11 模块，本题主力 crosscheck/consistency/locate/findings/report）、hk/、examples/、GITHUB_URL.txt。案例交付：report.md/report.json、ledger.json、crosscheck.json、consistency.json、pairs.json。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（crosscheck demo 演示 supported/unsupported/undeterminable 三态）
- 合规：22 文件 / ~116KB / hk.compliance.check_skill ok=true
- 真实可运行引擎，非模板壳；不含预制答案
