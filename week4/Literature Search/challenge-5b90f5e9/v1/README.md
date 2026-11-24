# systematic-screening-forge — 使用与方法说明

**协议先行、逐条理由码、计数闭合、人工确认点显式。**

## 调用
见 SKILL.md 工作流；引擎子命令：--protocol / --screen / --dedup-multi / --audit。

## 关键方法
PICO 协议骨架（0请求）→ 多源去重（合并依据留痕）→ 逐条筛选（理由码+证据片段）→ pending 模型复核 → 计数闭合审计（FAIL 修复再交付）。

## 边界与限制
适用：系统综述纳排、检索协议审计。不适用：全文内容分析。限制：仅标题记录升 pending 不强行判定。

## 维护
版本 1.0.0（2026-11），作者 dafeiyu。脚本改动同步 examples。
