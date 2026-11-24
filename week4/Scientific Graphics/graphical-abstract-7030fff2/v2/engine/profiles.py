"""Per-figure-class conventions.

A profile only supplies defaults and the class-specific completeness rules; it
never supplies scientific content.  The five profiles correspond to the five
figure classes the engine supports.
"""
from __future__ import annotations

PROFILES: dict[str, dict] = {
    "relationship_schematic": {
        "label_zh": "科研示意图 / 关系示意图",
        "canvas": {"preset": "nature_double", "dpi": 600},
        "legend_swatches": ["arrow", "tbar", "line", "dash"],
        "caption_recipe": "先说明方框、箭头、虚线与分组边界的含义，再说明标注数值的单位与来源。",
        "must_state": ["实体类别（模块/过程/数据）", "关系类型与方向", "分组或包含边界", "标注数值的单位"],
        "checks": ["SEM-RELATION-WORD", "SEM-DIRECTION", "LEG-EXISTS", "GEO-NODE-OVERLAP"],
    },
    "data_chart": {
        "label_zh": "科研数据图表",
        "canvas": {"preset": "nature_double", "dpi": 600},
        "legend_swatches": ["bar", "line", "box"],
        "caption_recipe": "写明每个面板的图型、统计量（mean/SD/SEM）、样本量 n、误差线含义与显著性标记的定义。",
        "must_state": ["坐标轴量与单位", "误差线含义", "样本量 n", "显著性标记定义", "数据来源表与列名"],
        "checks": ["UNIT-CONSISTENT", "LEG-MATCHES-DATA", "CMP-AXIS-UNITS", "NUM-TRACEABLE"],
    },
    "mechanism_pathway": {
        "label_zh": "生物机制图与通路图",
        "canvas": {"preset": "nature_double", "dpi": 600},
        "legend_swatches": ["arrow", "tbar", "diamond", "dash"],
        "caption_recipe": "先给区室定义（自上而下的顺序），再给箭头语义（激活/抑制/结合/间接），最后给读出型标注的定量含义。",
        "must_state": ["区室划分与顺序", "激活与抑制的图形语法", "跨膜与转位方向", "复合物与修饰关系"],
        "checks": ["SEM-RELATION-WORD", "SEM-DIRECTION", "SEM-LEGEND-TYPES", "GLYPH-CJK"],
    },
    "apparatus_route": {
        "label_zh": "实验装置与技术路线图",
        "canvas": {"preset": "nature_double", "dpi": 600},
        "legend_swatches": ["arrow", "line", "bar"],
        "caption_recipe": "按物料流向复述装置顺序，给出关键工况（温度、压力、流量）及其单位，再说明步骤编号与时长。",
        "must_state": ["部件名称与数量", "接口与管路连接", "物料流向", "工况参数与单位", "步骤编号与顺序"],
        "checks": ["GEO-NODE-OVERLAP", "NUM-TRACEABLE", "CMP-RELATIONS"],
    },
    "graphical_abstract": {
        "label_zh": "图形摘要",
        "canvas": {"preset": "ga_landscape", "dpi": 600},
        "legend_swatches": ["color", "arrow", "bar"],
        "caption_recipe": "用一句话给出主线（问题→方法→结果→结论），并说明颜色/长度编码的变量与单位。",
        "must_state": ["研究对象", "方法与关键步骤", "核心结果及其编码", "结论", "颜色编码变量"],
        "checks": ["CMP-PANEL-LETTERS", "LEG-MATCHES-DATA", "NUM-TRACEABLE", "GEO-TEXT-OVERLAP"],
    },
}

ALIASES = {
    "schematic": "relationship_schematic",
    "relationship": "relationship_schematic",
    "chart": "data_chart",
    "plot": "data_chart",
    "mechanism": "mechanism_pathway",
    "pathway": "mechanism_pathway",
    "apparatus": "apparatus_route",
    "technical_route": "apparatus_route",
    "workflow": "apparatus_route",
    "ga": "graphical_abstract",
    "graphical_abstract": "graphical_abstract",
}


def get(kind: str) -> dict:
    key = ALIASES.get((kind or "").strip().lower(), (kind or "").strip().lower())
    return PROFILES.get(key, PROFILES["relationship_schematic"])


def default_canvas(kind: str) -> dict:
    return dict(get(kind).get("canvas") or {})
