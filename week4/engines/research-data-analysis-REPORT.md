# Research Data Analysis 赛道构建报告（week4, v2）

构建时间：2026-11-24 UTC。构建目录：`/bohr-workspace/user-files/week4/build/research-data-analysis/`。

## 结构
```
engine/            # 主副本：dakit/ + hk/ + run.py + selftest.py + examples/README.md
skills/<cid>.SKILL.md   # 7 份技能说明（中文，exemplar 结构）
specs/<cid>.md          # 7 份交付标准
v2/<cid>/               # 7 份组装好的提交目录（SKILL.md/run.py/selftest.py/dakit/hk/examples/GITHUB_URL.txt）
```

## dakit 引擎模块（纯标准库：csv/sqlite3/statistics/math/json/difflib/re/hashlib）
| 模块 | 职责 | demo 验证要点 |
|---|---|---|
| profile | schema/类型推断、表头单位提示、候选主键（唯一且无缺失）、跨表 join 候选（名称相似+值重叠+类型兼容加权置信度） | 类型/缺失率/单位/主键断言；join 重叠率 1.0；空表与全缺失列警告 |
| align | 多来源列→目标 schema 映射：exact 1.0 / normalized 0.9 / synonym 0.75 / fuzzy 0.5–0.7（needs_review）；<0.6 进 unresolved 显式列出，绝不静默丢弃；合并时未映射列保留在 _extra_fields | 同义词（sample_id→id、测定值→value）、未解析列、extra 保留断言 |
| clean | 清洗账本：规则外置 JSON；missing（哨兵可配，drop/fill_value/fill_mean/fill_median/flag）、outlier（IQR 栅栏/z-score，drop/cap/flag）、duplicate（真实主键归一化，keep first/last）；每条规则记录 affected_row_ids+before/after 行数+前后分布+fill_value/criterion | 12 行已知答案集断言三条规则行 id 与行数；fill_median 口径断言 |
| stats | 描述统计（mean/sd/se/median/IQR/偏度/超额峰度）；t 检验（单样本/Welch/配对，t 分布经不完全 β 精确实现）；χ² 独立性（不完全 γ）；Pearson 相关；Cohen's d 与 95%CI（t 分位数二分反解）；假设检查：偏度/峰度正态性经验规则、Brown–Forsythe 方差齐性、样本量警告、Bonferroni 多重比较提示 | 教科书金标准：Student 睡眠配对 t=4.0621/df=9/p=0.002833、CI [0.7001,2.4599]；R 文档 Welch t=-5.4349/df=21.982/p=1.855e-05；手算 χ²=6.6516/p=0.00991；t/F/χ² 临界值断言 |
| charts | 数据形态→图型规则（distribution/comparison/relation/trend/composition），每条带 justification 与 rejected（饼图不做无序比较、并列柱不做时间序列等）；validate_spec 机检轴类型/单位冲突/同轴多单位/误差表示(sd/se/ci95)/基线截断/3D/双轴/类别超限 | 六类选型、单位冲突、文本时间轴、截断基线拒绝断言 |
| dbrun | SQLite 只读运行器：mode=ro、缺库报错不建空库；PRAGMA 实读 schema（表/列/类型/PK/FK/行数）；查询记录 SQL 原文+行数+耗时+列出处（歧义标注）；JOIN 行数膨胀检查；快照 CSV+sha256+行数一致性自检；拒绝写操作与多语句 | 现场建 2 表玩具库（含 FK、一对多）：自省/聚合/膨胀/快照/写拒绝/缺库断言 |
| report | 报告回填：{{点.路径|round:n}} 只允许来自 stats JSON；解析失败列出全部缺失并拒绝；mapping 记录每个数字出处；validate strict 模式列出手改数字 | 6 占位符回填、不可追溯占位符拒绝、篡改数字检出断言 |

hk/ 为共享 harbor_kit 原样复制（probe/extract/result/compliance）。

## 每挑战 SKILL 名称与侧重
| cid | name | 侧重模块链 |
|---|---|---|
| agent-6aefb2fd | research-data-pipeline | 全链 profile→align→clean→stats→charts→report |
| challenge-5c56458d | sqlite-query-audit | dbrun 为核心（自省→查询→膨胀检查→快照）+ 下游统计/回填 |
| challenge-95620c56 | research-data-analysis-core | 总课题通用全链（含数据库分支） |
| challenge-9562cc8d | scientific-chart-spec | charts 选型+validate_spec 一致性校验为核心 |
| challenge-9ec929fe | reproducible-analysis-run | selftest 环境自检+run.log 留痕+静默错误机检清单 |
| challenge-a0e888fa | cleaning-ledger | clean/profile 为核心；聚合转录表不插补、不总体推断（修订版约束） |
| challenge-c0e1e220 | assumption-first-statistics | stats 假设先行+效应量+CI+解释规范 |

每份 SKILL.md 含：frontmatter（英文 description，Use when/NOT for）、何时使用、输入、输出、工作流（确切命令）、本题判据对齐（引题面原文映射机制）、交付物、证据与审计规则、方法与近似（披露义务）、异常处理表、最小示例、公开作品 URL。

## 验证结果（全部实跑）
- selftest.py：7/7 个 v2 均 **8/8 checks pass**（7 模块 demo + e2e 合成案例 probe→extract→tables→profile→clean→stats→charts→report→emit→result.json；e2e 注入缺失/异常/重复并机检 n==账本 after_n、报告数字同源）
- hk.compliance.check_skill：7/7 个 v2 均 **ok=true**（18 文件、~126KB、无软链、全 UTF-8、frontmatter 合法、GITHUB_URL.txt 首行有效；检查前已清 __pycache__）

## 关键决策与假设
1. **统计精确实现**：t/F 经正则化不完全 β（NR 连分式）、χ² 经不完全 γ；t 分位数二分反解 CDF（~1e-8）。无 pandas/numpy/scipy。
2. **近似披露**：正态性用偏度/峰度经验规则（|skew|≤2、|excess kurtosis|≤7，非正式检验，n<20 功效低）；方差齐性用 Brown–Forsythe；Welch df 用 Satterthwaite。代码注释与每份 SKILL.md 双声明。
3. **可视化题不渲染图片**：离线标准库无绘图后端且引擎不做视觉判断——charts 产出并校验可审计 chart spec，绘图由 Agent 按 spec 执行；此决策已写入 SKILL.md "不适用"。
4. **清洗题修订版约束**：聚合转录表只做规则化处置与标记，不填补来源缺失、不做总体统计推断，SKILL.md 显著声明。
5. **e2e 用合成数据**：18 行合成 CSV 含注入故障；examples/README.md 声明非正式案例结果；不含任何正式案例（UCI/Iris/Wine）的预制答案。
6. 正式案例形态（UCI Concrete 1030 / Iris 150 bezdek / Wine 178 + SQLite）由 probe→extract/tables→profile/dbrun 通用路径覆盖，未针对特定数据集硬编码。

## 已知限制
- 统计覆盖面聚焦两组/配对/列联/相关；三组及以上 ANOVA、非参数检验（Mann-Whitney 等）未实现，SKILL.md 指引写 uncertainty。
- charts.validate_spec 只能校验声明的 spec；Agent 实际绘图代码与 spec 的一致性依赖 Agent 遵守（无法机检像素）。
- fuzzy 列映射（difflib）对中文缩写字段能力有限，一律 needs_review。
