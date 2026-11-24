# 交付标准（spec）：challenge-c050aaed 阅读批注与知识沉淀

## 核心问题定义（来自题面）
跑完"批注抽取—笔记结构化—关联—入库"闭环：批注逐条回到原文具体页与位置（锚点不漂移，类型与颜色含义不丢失）；笔记每条论断指到支撑它的原文片段（不退化为摘抄）；关联有依据、控制过度连接；沉淀条目可被真实问题检索到并按记录复跑核对（文件哈希+脚本版本，人工改动留痕）。

## 答题过程设计
1. probe/extract/blocks；批注整理 annotations.json（kind 四类枚举+颜色+file sha256+页/段 loc+quote）。
2. `lrkit.notes validate` 锚点逐字核验（漂移/错页抓出；OCR 低置信标注降级）。
3. 版本归并（同一文献多版本批注归并到同一文献 ID，依据落盘）。
4. 笔记结构化 notes.json（kind 五类，text=判断，anchor=原文片段）。
5. `lrkit.notes link` 候选关联（共享≥2实词）→ Agent 确认写 basis；`lrkit.notes notes` 总核验。
6. knowledge_base.md 入库；`lrkit.notes search` 检索入口。
7. emit 交付。

## 交付物清单
SKILL.md；run.py；selftest.py；engine（lrkit+hk）；examples/README.md；GITHUB_URL.txt。运行交付：annotations.json、notes.json、links.json、anno_report.json、notes_report.json、knowledge_base.md、result.json。

## 验收标准与自测结果
- `python selftest.py` → 15/15 checks pass；notes demo 断言锚点漂移被抓出、类型保真、无 basis 关联被拒绝、检索命中带 anchor。
- 合规：`hk.compliance.check_skill(v2/challenge-c050aaed)` → ok=true。
- 已知限制：手写批注/扫描件锚点只能到页级并依赖 OCR 质量；关联语义判定由 Agent 完成，引擎只强制 basis 存在。
