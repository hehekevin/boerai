# 交付标准 · challenge-80dd5ddc 科研知识库问答：科研资料管理：整理文件，也保留版本关系

## 核心问题定义
判断本课题是否做对，看三件事：答案里的每个关键论断是否都能落到具体文件、具体版本和具体段落；对于知识库里确实没有依据的问题，成果是否敢说"没有"并说明缺什么；换一个人拿着提交的记录，能不能把同样的问答重新走一遍。

## 答题过程设计
probe → extract → filelib/versions（组织基础：重复副本与版本链）→ kb index（块+定位+sha256）→ kb search（打分候选）→ Agent 写 claims.json（论断+引用块+逐字 quote）→ kb validate（引用文本必须真实出现在定位块，机械核验）→ 缺证分级（no/weak/conflicting evidence + 缺什么）→ emit。

## 交付物清单（week4/Research Library/challenge-80dd5ddc/v2/）
SKILL.md（kb-grounded-qa）、run.py、selftest.py、rlkit/（11 模块）、hk/、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（kb demo 含引用核验正反断言与 no_evidence 分级）（已运行）
- 合规：22 文件 / ~132KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
