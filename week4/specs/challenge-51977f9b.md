# 交付标准 · challenge-51977f9b 系统性文献综述

## 核心问题定义
判断本课题是否做对，看三件事：纳入与排除的每一篇是否都有可查的理由；综述中的每条论断是否能回链到具体证据；换一个人拿同样输入和记录能否复跑出基本一致的纳入集与结论。聚焦检索式、纳排标准、筛选记录、质量评价、可复核流程五环节。

## 答题过程设计
probe → extract → qplan（问题结构化为检索要素）→ queries.json（检索式+每段 intent）→ criteria.json（纳排条款先于筛选写定、版本化）→ identity 去重 → screen validate ×2（题录级/全文级，理由码+证据片段强制，PRISMA 计数可重算）+ screen conflicts（双人分歧待裁决）→ 质量评价（逐维度依据位置）→ evidence/synthesis（论断回链+冲突裁决）→ gaps → emit。

## 交付物清单（week4/Deep Research & Literature Review/challenge-51977f9b/v2/）
SKILL.md（name: systematic-review-trail，含本题判据对齐"三件事"）、run.py、selftest.py、drkit/（8 模块，screen 为本题核心）、hk/、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 9/9 checks pass（8 模块 demo + e2e，已运行）
- 合规：≤50 文件 / ≤2MB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
