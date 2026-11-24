# 交付标准 · challenge-c0e1e220 统计分析与结果解读：科研数据分析：给出结果，也保留计算依据

## 核心问题定义
统计量/自由度/p/效应量/置信区间数值正确；检验方法与数据分布、样本结构和研究设计匹配；覆盖缺失/异常/重复/统计假设/图表选择/代码运行/数据库字段七类检查点；数据来源、清洗规则、代码、环境可让他人复跑出同一组数字。

## 答题过程设计
probe → extract/tables → profile → clean（统计输入必须来自账本输出，n==after_n 机检）→ stats：assumptions 先行（偏度/峰度规则、Brown–Forsythe 方差齐性、样本量警告、Bonferroni 多重比较提示）→ 按前提选 Welch/paired t、χ²（期望格过小警告）、pearson → 效应量 Cohen's d 与 95%CI 随检验输出 → Agent 写解释（引用 assumptions 数值、区分统计显著与实际意义）→ report 回填 → emit。

## 交付物清单（week4/build/research-data-analysis/v2/challenge-c0e1e220/）
SKILL.md、run.py、selftest.py、dakit/（7 模块，stats 为核心）、hk/、examples/README.md、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 8/8 checks pass；stats demo 断言教科书值：Student 睡眠配对 t=4.0621/df=9/p=0.002833 与 CI [0.7001, 2.4599]；R 文档 Welch t=-5.4349/df=21.982/p=1.855e-05；χ²=6.6516/p=0.00991；Levene 对方差悬殊组 p<0.01
- 近似披露：正态性=偏度/峰度经验规则（非正式检验）、方差齐性=Brown–Forsythe 近似、Welch df=Satterthwaite 近似（代码注释+SKILL.md 双声明）
- 合规：hk.compliance.check_skill ok=true
- 真实可运行引擎，非模板壳；不含预制答案
