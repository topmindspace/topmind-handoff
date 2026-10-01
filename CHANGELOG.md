# CHANGELOG

## 0.2.0（2026-10-01）

首个公开版本。由内部 `topmind-handoff 0.1.0`（单用户定制）重构为通用开源技能。

- 交接包格式规范 v1.0：单文件 Markdown + YAML frontmatter，六节结构
- 导出工作流：采集 → 分类（五桶）→ 冲突裁决 → 脱敏 → 落盘
- 导入工作流（反向接收）：校验 → 解析 → diff（新增/冲突/已撤回）→ 人工确认 → 合并
- 反投毒规则：交接包视为不可信输入，不执行包内指令
- 隐私硬线：永不携带清单、脱敏手法、导出前人工 review 强制步骤
- 各工具适配：ChatGPT / Claude / Gemini / Copilot / Meta AI / 编程 Agent 文件约定
- 空白模板 `assets/handoff-template.md` + 填写示例 `assets/handoff-example.md`（虚构占位数据）
- npm 发版：`@topmindspace/topmind-handoff`（package.json 0.2.0，与技能版本同步；
  GitHub Release + npm 由 tag `v*` 触发，需仓库 secret `NPM_TOKEN`）
- 工具适配新增：Bot 类/新兴 Agent 通用接入法（WorkBuddy、Muse、Grok bot、Cue、Dots 等；
  不逐个写死，以"格式是契约，工具是实现"为准）
