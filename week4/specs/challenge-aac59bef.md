# 交付标准（spec）：challenge-aac59bef 网页文献阅读与翻译

## 核心问题定义（来自题面）
把网页论文处理成"干净正文 + 分段译文 + 来源对照"：抓下来的必须是论文正文（不是摘要页/订阅页/导航页，剔除相关文章与参考文献）；译文逐段对得上原文（不漏译、不补写、术语全文一致、公式上下标数字单位原样保留）；读者凭交付物能回到原始页面核对每条内容（URL、抓取时间、段落锚点、页面版本）。遇登录/付费墙/改版/超时停止并说明。

## 答题过程设计
1. Agent 按任务说明抓取页面落盘（引擎不联网）。
2. `lrkit.webtext extract` 正文切分 + 抓错页信号（无段落/密度低）——有信号回到抓取步。
3. 建 glossary.json（一词多译须注明条件，`lrkit.terms glossary` 检查）。
4. Agent 逐段翻译写 alignment.json（漏译标 omitted+reason）。
5. `lrkit.terms align`（源段全覆盖、译文数字防补写）+ `lrkit.terms terms`（术语一致）。
6. `lrkit.webtext manifest` 登记抓取轨迹（HTTP 快照与实时页面分开登记版本）。
7. emit 交付。

## 交付物清单
SKILL.md；run.py；selftest.py；engine（lrkit+hk）；examples/README.md；GITHUB_URL.txt。运行交付：translation.md、main_text.json、alignment.json、glossary.json、fetch_manifest.json、terms_report.json、result.json。

## 验收标准与自测结果
- `python selftest.py` → 15/15 checks pass；webtext demo 断言剔除导航/广告/参考文献并识别纯导航页；terms demo 断言术语不一致与译文补写数字被抓出。
- 合规：`hk.compliance.check_skill(v2/challenge-aac59bef)` → ok=true。
- 已知限制：正文识别为启发式规则，复杂动态页面需 Agent 调整抓取方式后重跑；引擎不做翻译质量评分（由 Agent/评审判断）。
