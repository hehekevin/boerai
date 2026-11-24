# 交付标准 · challenge-5047f57f 学术浏览器插件：科研自动化：完成操作，也保留过程轨迹

## 核心问题定义
判断本课题是否做对，看三件事：任务是否在真实页面上跑通并交出可用的产物；产物里的字段和位置能否与原文逐项对上；整个过程能否被别人按记录复跑并解释失败原因。special 明确：未改动的科学来源 HTML 快照、真实 Chromium/Playwright 与 MV3 属组织方运行环境；源快照 HTTP 与在线出版商严格区分；Skill 侧在离线快照上完成确定性抽取，不伪造在线验证。

## 答题过程设计
probe（冻结快照哈希）→ htmlsnap parse（citation/DC/og meta 抽取+字段出处+参考文献列表防误取警告）→ htmlsnap anchor（元素 id/文本指纹定位+行号）→ normalize/identity（规范记录+去重审计）→ library.json → emit。

## 交付物清单（week4/Research Library/challenge-5047f57f/v2/）
SKILL.md（page-citation-capture）、run.py、selftest.py、rlkit/（11 模块）、hk/、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（htmlsnap demo 含"参考文献列表不入当前论文记录"断言）（已运行）
- 合规：22 文件 / ~132KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
