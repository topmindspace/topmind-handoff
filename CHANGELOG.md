# CHANGELOG

## 0.3.0（2026-10-01）

导入流程傻瓜化：交接包自带接收指引，零依赖。

- 包新增"接收指引"区块（`references/spec.md`）：frontmatter 之后固定 4 行模板，
  没装技能的 AI 照着做就行；级别为推荐（SHOULD），老包依然合法，
  `handoff_version` 保持 `1.0` 不变
- 用户在新工具里只需贴包 + 一句话："这是我的交接包（topmind-handoff 格式），
  请按包里的接收指引处理。"——不用再背 6 步流程
- `SKILL.md` 的导入工作流压缩为 3 步（读指引→diff→确认合并），
  `references/import.md` 保留为完整版并注明"傻瓜版/完整版"关系
- 修正 `import.md` 冲突裁决第 1 条：逐条按日期比，整包 `generated_at`
  只表示导出时间，不直接决定单条胜负（之前表述不精确）
- `README` / `tool-adapters.md` 的导入一句话指令同步更新；
  模板与示例包带上接收指引区块
- `spec.md` 增加版本同步提醒：发版 bump 时 `generator` 里的技能版本号
  与 `package.json` / `SKILL.md` / `README` / `CHANGELOG` 四处保持一致

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
