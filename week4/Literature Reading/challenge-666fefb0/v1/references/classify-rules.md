# 分类规则（classify-rules.md）

## 1. 分类法结构
[{name, keywords[], children:[{name, keywords[]}]}]。子类命中优先于父类（层级路径输出）。

## 2. 标签粒度控制
max 5/doc；同义合并 casefold；停用词表（研究/方法/paper/method等）；CJK 2-4字串+英文词。

## 3. 命名降级
| 情形 | 规则 |
|-|-|
| 特殊字符 | 替换为 _ |
| 超长>120 | 截断+... |
| 缺字段 | NA 占位 |
| 同名冲突 | 追加 idx |

## 4. 版本判定
键：doi > (title_norm+author+year)。预印本标记（arxiv/preprint）；重复→保留正式版/信息全者，**归档不删除**。

## 5. 异常处置
见 SKILL.md 异常表。