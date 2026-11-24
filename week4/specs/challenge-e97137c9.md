# 交付标准 · challenge-e97137c9 文献综述生成

## 核心问题定义
判断本课题是否做对，看三件事：筛选标准是否先于写作写明并被一致执行；每条实质论断能否指回具体文献的具体位置；主题划分与研究空白是不是从这批文献里长出来的而不是套上去的。反面证据并列呈现，引用强度与原文一致。

## 答题过程设计
probe → extract → criteria.json（筛选先于写作）→ identity 去重 → screen validate（一致执行）→ themes.json（主题含 basis+support_record_ids+boundary）→ matrix.json（证据表：quote+locator+strength）→ evidence validate/conflicts（冲突并列+裁决）→ draft.md 逐句登记 synthesis.json（表述强度对应 claim.strength）→ synthesis audit（悬空引用/伪造 claim_id/静默遗漏拒绝）→ gaps validate（空白落到证据缺口）→ emit。

## 交付物清单（week4/Deep Research & Literature Review/challenge-e97137c9/v2/）
SKILL.md（name: review-draft-evidence-link，含本题判据对齐"三件事"）、run.py、selftest.py、drkit/（8 模块）、hk/、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 9/9 checks pass（8 模块 demo + e2e，已运行）
- 合规：≤50 文件 / ≤2MB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
