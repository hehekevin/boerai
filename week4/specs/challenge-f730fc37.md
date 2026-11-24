# 交付标准（spec）：challenge-f730fc37 阅读客户端

## 核心问题定义（来自题面）
在同一处走完"打开文献—定位到相关段落—选中文本提问—保存批注或结论—回看复核"的阅读闭环：答案对应当前页面与选中文本；定位落到真实原文位置（处理物理页/印刷页不一致、跨栏、扫描件）；批注、问答结论与阅读位置可保存、回看、导出；操作路径、原文锚点和每次运行原始输出可被他人复核复现。

## 答题过程设计
1. probe/extract/blocks；session.json 第 1 条 open（file+sha256+页数，loc 用物理页 p.N 并注明映射）。
2. `lrkit.reader locate`（page/section/keyword 统一入口）。
3. ask 记录：selection（loc+逐字 quote）+question+answer+evidence；缺依据写明不编造。
4. annotate 记录 → annotations.json（批注与锚点绑定）。
5. `lrkit.reader validate` 闭环核验（open 存在、seq 单调、锚点逐字可核）。
6. `lrkit.reader export` → reading_record.json（锚点+哈希+版本）。
7. emit 交付。

## 交付物清单
SKILL.md；run.py；selftest.py；engine（lrkit+hk）；examples/README.md；GITHUB_URL.txt。运行交付：session.json、reading_record.json、annotations.json、session_report.json、report.md、result.json。

## 验收标准与自测结果
- `python selftest.py` → 15/15 checks pass；reader demo 断言完整会话通过、锚点错位（0.87→0.78）被抓出、导出文件生成。
- 合规：`hk.compliance.check_skill(v2/challenge-f730fc37)` → ok=true。
- 已知限制：本技能是数据层 MVP 而非 GUI；扫描件无文本层时定位只能到页级。
