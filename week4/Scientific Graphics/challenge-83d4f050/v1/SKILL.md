---
name: bio-pathway-forge
description: 生物机制图与通路图：命名规范（基因/蛋白书写区分/物种前缀/同义旧名/复合物家族/实体ID来源——防同名异义异名同义）、调控语义（促进抑制磷酸化泛素化结合募集转运→可区分箭头端点+证据强度）、拓扑布局（上下游/受体胞内核内层级/跨膜区室/分支反馈环——布局传达机制）。
---

# bio-pathway-forge

## 核心原则（不可违反）
1. **名规范**：基因斜体/蛋白正体书写区分；物种前缀；同义名与旧名合并；复合物与家族成员；实体ID与来源标注——防同名异义和异名同义混淆（bio_device --entities）。
2. **控语义**："促进/抑制/磷酸化/泛素化/结合/募集/转运"→可区分箭头类型与端点样式；证据强度标注（bio_device --relations）。
3. **扑布局**：上下游顺序/受体-胞内-核内层级/跨膜与区室位置/分支反馈环走向——布局本身传达正确机制结构（bio_device --topology）。
4. **脚本先行**。

## 运行环境约定
输入 `/input/case.json`；输出 `/app/output`；引擎以 `<SKILL_DIR>` 指代。

## 工作流程
### 阶段0 盘点（1请求）
### 阶段1 实体清单（0请求）：`python scripts/bio_device_engine.py --entities text.json`
### 阶段2 关系映射（0请求）：`--relations`
### 阶段3 拓扑（0请求）：`--topology relations.json`
### 阶段4 SVG生成（1-2请求）+成文

### 交付（0请求）
组装 `/app/output/result.json`（合并 output_contract + case_id）：
```bash
python <SKILL_DIR>/scripts/validate_result.py --case /input/case.json --result /app/output/result.json --manuscript /app/output/bio-pathway-forge.md --require "原则关键词1,原则关键词2,异常关键词" --names "p1,p2,p3"
```

## 异常处置速查
| 情形 | 处置 |
|-|-|
| 命名歧义 | ID标注消歧 |
| 关系方向不明 | 待确认标记 |
| 区室未知 | 布局降级声明 |

## 资源清单
scripts：bio_device_engine.py + inspect_case + validate_result。

## 预算红线
64 模型请求/900秒。确定性子命令恒为0请求。过60%时间冻结 status=partial。