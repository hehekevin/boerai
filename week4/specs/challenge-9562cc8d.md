# 交付标准 · challenge-9562cc8d 科研数据可视化：科研数据分析：给出结果，也保留计算依据

## 核心问题定义
不看生成多少张图，而看图上的每个视觉元素是否与源数据一一对应、交付的图能否不经二次修补直接进入投稿或正式报告、从数据到成图的过程能否被他人按记录重跑。

## 答题过程设计
probe → extract/tables → profile（轴变量类型与单位提示）→ clean（口径先定，图注引用账本）→ stats（图上数字只来自 stats.json）→ dakit.charts select_chart（数据形态→图型+理由+被否决项：饼图不做无序比较、并列柱不做时间序列等）→ validate_spec（轴类型/单位/误差表示/基线截断/3D/双轴/类别超限机检，不过不出图）→ Agent 按 spec 出图与图注 → report 回填 → emit。引擎不渲染图片，产出并校验可审计 spec。

## 交付物清单（week4/build/research-data-analysis/v2/challenge-9562cc8d/）
SKILL.md、run.py、selftest.py、dakit/（7 模块，charts 为核心）、hk/、examples/README.md、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 8/8 checks pass（charts demo 断言六类选型规则与单位冲突/文本时间轴/基线截断拒绝逻辑）
- 合规：hk.compliance.check_skill ok=true
- 真实可运行引擎，非模板壳；不含预制答案
