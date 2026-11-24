"""harbor_kit · 通用运行时工具包（所有赛道共用）

职责边界：
- probe      读 /input/case.json 与 /input 的真实结构（不猜 schema）
- extract    把 PDF/CSV/XLSX/DOCX/JSON/TXT 抽成带定位的文本与数据行
- result     组装 result.json：case_id + output_contract 全字段 + 状态 + 来源 + 不确定性
- compliance 交付前自查：文件数/大小/UTF-8/frontmatter/GITHUB_URL

引擎只做确定性簿记；语义判断（相关性、分类、写作）由加载 Skill 的 Agent 完成，
中间产物一律落盘为 JSON，保证可复跑、可审计。
"""
