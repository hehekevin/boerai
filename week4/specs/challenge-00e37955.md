# 交付标准 · challenge-00e37955 资料管理领域总课题：科研资料管理：整理文件，也保留版本关系

## 核心问题定义
对真实文件库完成组织、元数据、版本、检索与交接：资料结果与输入文件和题目规则一一对应；哈希、来源、权限、变更和日志让他人可复跑核对；跳过、冲突、无权限、重复如实记录，不把未完成写成完成。special 明确：组织方授权的真实文档库修复（真实文件、别名、管理性版本注记、元数据、检索问题、真实恢复/索引操作），不编造原始 PDF/私有 Zotero 账户/语义金标准。

## 答题过程设计
probe → extract → filelib inventory（skips 留痕）→ versions（内容哈希判重复、版本链、注记核验）→ normalize（字段出处）→ filelib plan + archive_manifest → tags（审计+幂等+回退）→ kb（检索问答核验）→ emit。

## 交付物清单（week4/Research Library/challenge-00e37955/v2/）
SKILL.md（research-library-steward）、run.py、selftest.py、rlkit/（11 模块）、hk/、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（已运行）
- 合规：22 文件 / ~132KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
