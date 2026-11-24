# 交付标准 · challenge-a57a8549 实验方案设计领域总课题

## 核心问题定义
开放性领域课题的统一底座：识别子题型（A 生成/优化、B 比较选择、C 可行性审查、D 结果解释）后共用同一引擎——带定位结构抽取、六面检查表（可裁剪并记录理由）、精确资源核对、风险台账、版本差异、结论计算。输入输出明确、完成标准可核、边界写清。

## 答题过程设计
probe → extract → 子题型判定（依据 task.md 原句落盘）→ 按路径执行（A: typed 方案+验证门+plandiff；B: 统一口径矩阵+choice；C: 全检查表+resources+verdict；D: 解释台账+异常映射）→ emit。

## 交付物清单（week4/Experimental Design/challenge-a57a8549/v2/）
SKILL.md（判据对齐引用题面四常见问题与三条完成标准）、run.py、selftest.py、edkit/、hk/、examples/、GITHUB_URL.txt。案例交付：公共 report/checklist/verdict + 子题型专属产物。

## 验收标准与自测结果
- `python3 selftest.py` → 7/7 checks pass；hk.compliance.check_skill ok=true
- 子题型模糊时按最保守路径（全检查表）执行并在 summary 写明判定依据
