# 第4周 77题逐题工作规范（每轮工作前必读）

## 流程（每题6步，禁止跳步）
1. **brief_read**: 精读题面（week4-briefs/{cid}.json 的 content 全文）——重点：四问、突破方向、可评范围约束、Harbor契约
2. **spec_designed**: 写交付物标准到 week4-specs/{cid}.md——含：核心问题定义、答题过程设计（工作流程阶段）、交付物清单、验收标准（自测命令）
3. **skill_built**: 按标准生成完整交付物——专属领域脚本（真实可运行）+ SKILL.md（按四问定制）+ references（按方向定制）+ templates + examples + README
4. **self_tested**: 执行 week4-specs/{cid}.md 中的自测命令——引擎子命令全跑一遍 + 合规检查（文件数≤50、单文件≤500KB、总量≤2MB、UTF-8、frontmatter合法）
5. **ready_to_submit**: 全部通过才置 true；任何一步失败修复后重测
6. **等待用户确认后**才提交（playground submit），提交后回填 attempt_id

## 资产索引
- 题面库: week4-briefs/{cid}.json
- 精读提取: week4-perchallenge.json（四问/方向/范围）
- 进度: week4-progress.json（每轮开始先读）
- 逐题标准: week4-specs/{cid}.md
- 已验证引擎: track-engines/literature-search/{search_audit,screening_engine,patent_search}.py
- 共享脚本: zeros/shared/{inspect_case,validate_result}.py
- 输出目录: week4/{赛道}/{cid}/v1/

## 质量红线（第3周0分教训）
- Harbor评分器要求 complete genuinely-derived solution——模板壳必判0
- 脚本必须真实可运行且已自测
- 预算: 64模型请求/900秒 → 确定性脚本0请求，模型仅语义复核
- 评分维度: 实际效果40/使用增益25/创新增益15/可靠体验10/生态贡献10

## 进度速览（当前）
- 已完成完整交付物: 3/77（0467f5db 复用提交、5b90f5e9、ad3e9357）
- 已提交等待评分: 6道（101463-101467、101554）
