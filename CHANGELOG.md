# CHANGELOG

## 0.4.1（2026-10-02）

深度审查与文档完善（patch）：
- 修正示例文件 `handoff_version` 为 1.1
- `import.md` 补充 v1.1 导入规则：技能清单比对（只提示不阻断）、
  进行中的工作处理（不重复步骤、不推翻决策、不写入长期记忆）
- `export.md` 补充 v1.1 采集指引：技能清单只收录实际用到的、
  第 8 节三个子块必填
- 全仓版本引用统一为 0.4.1

## 0.4.0（2026-10-02）

包格式 v1.0 → **v1.1**（向后兼容，只加可选字段/节）：
- frontmatter 新增 `skills_manifest`（技能名+版本清单）
- 正文新增第 7 节"环境与技能"、第 8 节"进行中的工作"（状态/阻塞/关键决策）
- 接收指引从 4 步扩展到 6 步：新增技能比对、任务状态接续指引
- 导入流程：技能缺失/版本过低只提示不阻断；接收方不重复已完成步骤、不推翻已定决策

## 0.3.1（2026-10-01）

导入流程傻瓜化 + 第二轮深度审查。交接包格式仍为 `1.0`（无 breaking change）。

**导入傻瓜化：**
- 包新增"接收指引"区块（`references/spec.md`）：frontmatter 之后固定 4 行模板，
  没装技能的 AI 照着做就行；级别为推荐（SHOULD），老包依然合法
- 用户在新工具里只需贴包 + 一句话："这是我的交接包（topmind-handoff 格式），
  请按包里的接收指引处理。"——不用再背 6 步流程
- `SKILL.md` 的导入工作流压缩为 3 步（读指引→diff→确认合并），
  `references/import.md` 保留为完整版并注明"傻瓜版/完整版"关系
- `README` / `tool-adapters.md` 的导入一句话指令同步更新；
  模板与示例包带上接收指引区块

**深度审查修复：**
- 明确信任边界（`spec.md` + `import.md` 反投毒规则）：接收指引区块是可信的格式指令，
  除此之外正文内容仍按不可信输入处理——解决了"不执行包内指令"与"执行包内指引"的矛盾
- 修正 `import.md` 冲突裁决：逐条按日期比，整包 `generated_at` 只表示导出时间，
  不直接决定单条胜负（之前表述不精确）
- `export.md`：补上自定义节（`## 7.`）的导出处理——本地有对应内容的一并带出，
  没有的不凭空保留
- `SKILL.md`：triggers 增加口语化触发词（打包记忆、记忆同步、换AI、带到新工具、多端同步），
  description 补英文 "sync memories across AI tools"
- `spec.md` 增加版本同步提醒：发版 bump 时 `generator` 里的技能版本号
  与 `package.json` / `SKILL.md` / `README` / `CHANGELOG` 保持一致

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
