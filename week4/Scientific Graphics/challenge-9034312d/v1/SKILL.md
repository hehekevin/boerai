---
name: device-flow-forge
description: 实验装置与技术路线图：结构表达（装置清单/装配说明→部件接口/装配关系/同类区分/接口对齐/局部放大）、工序表达（工艺→编号流程图；主序列/并行支路/循环回流/终止条件；编号与正文逐条对照）、流向表达（箭头线型颜色编码物料能量信息；分流合流回流废料；防反向断头箭头）。
---

# device-flow-forge

## 核心原则（不可违反）
1. **构表达**：装置清单/装配说明/方法段落→部件与接口抽取；单元装置结构与装配关系；同类部件区分/接口对齐/局部放大（bio_device --device）。
2. **序表达**：工艺描述→带编号流程图；主序列/并行支路/循环回流/终止条件；编号与正文逐条对照（bio_device --process）。
3. **向表达**：箭头/线型/颜色编码物料/能量/信息流；分流合流/回流/废料出口；避免方向相反或断头箭头（bio_device --flowdir）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 部件（0请求）：`python scripts/bio_device_engine.py --device parts.json`
### 阶段2 工序（0请求）：`--process`
### 阶段3 流向（0请求）：`--flowdir flow.json`
### 阶段4 SVG生成（1-2请求）+成文

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/device-flow-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 接口不明 | 对齐待确认 |
| 断头箭头 | flowdir校验FAIL修复 |
| 编号错位 | 与正文对照清单 |

## 资源清单
scripts：bio_device_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。