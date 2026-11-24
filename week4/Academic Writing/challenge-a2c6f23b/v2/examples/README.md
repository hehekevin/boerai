# 示例（合成数据，非正式案例结果）

`python3 ../selftest.py` 会运行：
- 9 个引擎模块的 `--demo`（每个 demo 自带合成数据与断言，覆盖“抓得到错”
  与“放得过对”两个方向）；
- 一次端到端：合成 case.json + 文本材料 → probe → extract →
  `claims validate`（句级论断-来源绑定 + 数字一致性）→
  `deck build`（纯 zip PPTX + matplotlib PNG 预览 + LibreOffice PDF，若可用）→
  emit → result.json。

## 各模块最小调用（文件均为 JSON/UTF-8 文本，可用任何编辑器准备）

```bash
# 1) 论断-来源绑定 + 数字一致性（写作保真核心）
python ../run.py claims validate draft.md sources.json bindings.json computed.json work/claims.json --strict
# sources.json: [{"id":"S1","text":"来源全文","loc":"paper p.3"}]
# bindings.json: [{"sentence_id":"d0003","source_id":"S1","quote":"来源原文片段"}]
# computed.json: [{"value":"21","formula":"500*4.2/100","basis_sentence_ids":["d0001"]}]

# 2) 必需要点/章节覆盖
python ../run.py coverage check draft.md brief.json coverage_map.json work/coverage.json

# 3) 引用完整性（正文键 ↔ 参考文献表）
python ../run.py citecheck check draft.md work/citecheck.json

# 4) 双语一致性（术语表、段对齐、漏译、数字漂移）
python ../run.py bilingual check terms.json segments.json work/bilingual.json

# 5) 格式合规（标题层级、分节字数、参考文献字段顺序）
python ../run.py formatcheck check draft.md spec.json work/format.json

# 6) 修订簿记（锚点校验、改前/改后/依据、接受/拒绝）
python ../run.py revisions apply draft.md ops.json draft_v2.md work/changes.json

# 7) 结构与论证链（结论必挂支撑、循环论证、跨节重复、结论尺度）
python ../run.py structcheck check draft.md chain.json work/struct.json

# 8) 幻灯片（大纲校验 → 可编辑 PPTX → PNG/PDF 预览）
python ../run.py deck validate outline.json sources.json work/deck_check.json --slide-limit 12
python ../run.py deck build outline.json work/deck.pptx --preview work/preview

# 9) 评测簿记（锚点=可观察现象、0/1/2 双评、一致性、逐题报告）
python ../run.py scorecard lint-anchors anchors.json work/anchors_lint.json
python ../run.py scorecard score anchors.json ratings.json work/ratings_check.json
python ../run.py scorecard agree anchors.json ratings.json work/agree.json work/eval_report.md --adjudications adjudications.json
```

所有示例数据均为演示接口而构造，不得作为正式测试案例结果引用。
材料不足时一律走诚实路径：`awkit.claims.insufficient()` 生成“【材料不足】”
标注句，result.json 的 status 降级为 partial 并在 uncertainty 说明。
