# 双语对照输出格式（bilingual-table.md）

> 每段一个块。`### Pxxx` 后接页码段位提示；**原文**/**译文**/**记号** 三行齐全。此格式是 verify_translation.py 的解析契约，不得改动字段名。

### P001（p.1 ¶1）
**原文**：We propose a two-stage training framework for protein structure prediction.
**译文**：我们提出一种用于蛋白质结构预测的两阶段训练框架。
**记号**：术语 two-stage training framework ✓

### P002（p.1 ¶2）
**原文**：The encoder processes 128x128 inputs with a stride of 2, following Ref. [7].
**译文**：编码器按步长 2 处理 128x128 输入，做法遵循文献 [7]。
**记号**：[7] ✓ | 2 ✓ | 128x128 ✓

## 格式规则

1. **段头**：`### Pxxx（p.N ¶M）`——页码与段落位次来自 segments.json；跨页续段可写 `（p.2–3）`。
2. **原文**：逐字照抄 segments.json 对应段（不得"顺手修正"）。
3. **译文**：遵循 translation-rules.md；译不准处句尾加【译注：…】；未译处写【未译：原因】。
4. **记号**：列出本段核对过的记号（`[7] ✓ | Table 2 ✓`）。可选行，核对完就写上，方便复核者快速扫读。
5. 段块之间空一行；不要把两段并进一个块。
