# 交付标准 · zotero-ai-a207356c Zotero AI 插件：科研自动化：完成操作，也保留过程轨迹

## 核心问题定义
判断本课题是否做对，看三件事：任务是否在真实文献库上从头走到尾；库里最终留下的条目和字段是否与原文和题目要求对得上；整个操作过程能否被别人按记录重跑一遍。special 明确：每案 3 条真实来源记录、预初始化来源支撑库、DOI/冻结元数据/RIS/本地出版商文件、真实笔记/附件/SQLite 状态；C03 只读为组织方显式策略；图像型专利为 out-of-scope 控制项；不得把激活当作语义 AI 成功。

## 答题过程设计
probe → extract → 复制库到 work（原始只读）+ ledger 快照 → normalize（RIS/Zotero JSON 映射）→ metarepair（fill_missing 默认不覆盖已有正确字段，冲突留痕；无快照=unrepaired 不编字段）→ identity（幂等去重+冲突审计）→ sqlite_ops migrate（事务+回滚+verify）→ tags（幂等审计+回退；未知条目 refused 防错落）→ kb（库内回答引用机械核验，超范围说"库内无依据"）→ emit。

## 交付物清单（week4/Research Library/zotero-ai-a207356c/v2/）
SKILL.md（zotero-library-ops）、run.py、selftest.py、rlkit/（11 模块）、hk/、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（metarepair demo 含"已有字段不被覆盖"、tags demo 含回滚恢复初态断言）（已运行）
- 合规：22 文件 / ~133KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
