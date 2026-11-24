# 交付标准 · agent-d1ab67e5 科研软件操作 Agent：科研自动化：完成操作，也保留过程轨迹

## 核心问题定义
判断本课题是否做对，不看点了多少次、封装了多少个接口，而看三件事：任务是否真的在目标软件里跑完并交出可继续使用的产物；软件实际状态与导出结果是否与任务给定的参数、单位、版本一致；失败发生时能否被发现、被回滚、被复核。special 明确要求：真实 UCI 科学数据集 + 真实 LibreOffice 导入/配置/重算/PDF 导出，有意义的终态/失败/恢复/幂等断言；禁止模拟软件或"写出来"的成功。

## 答题过程设计
probe → extract → soffice_ops status（可用性诚实确认）→ OpLedger 账本包裹的逐步真实执行（import_dataset → recalculate 专用重算 profile → verify_computed CSV 网格核对 → export_pdf 魔数校验）→ assert_idempotent / rollback → emit。每一步断言 exit code、产物存在、大小>0；soffice 不可用时只报 unavailable，绝不伪造。

## 交付物清单（week4/Research Library/agent-d1ab67e5/v2/）
SKILL.md（software-ops-ledger）、run.py、selftest.py、rlkit/（11 模块）、hk/、examples/、GITHUB_URL.txt。

## 验收标准与自测结果
- `python3 selftest.py` → 12/12 checks pass（含真实 LibreOffice 24.2 重算：缓存值 0 → 真实值 5；PDF 魔数校验；不可用路径断言）（已运行）
- 合规：22 文件 / ~133KB / 无软链 / UTF-8 / frontmatter 合法 / GITHUB_URL.txt 有效（已检查）
- 真实可运行引擎，非模板壳；不含预制答案
