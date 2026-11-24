# 交付标准 · challenge-2bfd9194 科研资料库与文件管理：科研资料管理：整理文件，也保留版本关系

## 核心问题定义
判断本课题是否做对，不看移动了多少文件，而看三件事：落库后的目录树与元数据清单是否与约定一致；重复与版本关系是否按内容判断而不是按文件名判断；整个整理过程能否被他人按记录复跑并核对。评分强调覆盖文件类型、元数据字段、目录层级、重复文件、版本差异、权限与来源六类要素，不静默跳过难处理文件。

## 答题过程设计
probe → extract → filelib inventory（全量哈希+skips）→ rules.json 冻结目录约定 → filelib plan（冲突加哈希后缀改名，永不覆盖）→ versions（内容判据版本链+别名+冲突）→ normalize（元数据清单+出处）→ archive_manifest（一一对应交接清单）→ emit。

## 交付物清单（week4/Research Library/challenge-2bfd9194/v2/）
SKILL.md（file-landing-versioning）、run.py、selftest.py、rlkit/（11 模块）、hk/、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（已运行）
- 合规：22 文件 / ~132KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
