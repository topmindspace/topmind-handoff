# CHANGELOG

## 0.4.11（2026-10-10）

包格式仍是 1.1，`handoff/<package_id>/<package_id>.md` 布局不变；只改示例与文档，旧包和没装本技能的接收方照常可用。

- 优化示例：交接示例与参考文档里的来源标识统一改为虚构的 `demo` / `example`，示例内容为通用内容
- 优化文档：模板、示例与 `references/spec.md` 的 `generator` 版本号同步到 0.4.11

## 0.4.10（2026-10-08）

包格式仍是 1.1，`handoff/<package_id>/<package_id>.md` 布局不变；新字段都是可选扩展，旧包和没装本技能的接收方照常可用。

- 特性支持环境与技能同步：新增 `references/environment.md`。导出时第 7 节写工具、已装技能、路径、连接器；`skills_manifest` 改为本环境已装技能清单，每条可选 `source`（`npm:<包名>` / `github:<owner/name>` / `local`）和 `install`（安装方式）
- 特性支持技能升级建议：接收时盘点本机已装技能，与包里的清单、已发布最新版（`npm view`、GitHub Releases 只读查询，能联网时）对照，列出缺失、偏旧、已停用的技能（如 `topmind-wechat` → `topmind-wechat-post`），按安装方式给出升级命令。用户确认后才升级，先备份到新建的带时间戳目录，升级后核对版本；包里写的来源当不可信输入，装之前给用户确认。不阻断导入
- 优化接收整合：diff 增加「建议更新」（同一条主张包里较新且不是同一天，可整批确认）和「本地较新」（保留本地）；记忆、环境、任务分开比对，整合回执按这三块写新增、更新、冲突怎么裁、哪些没动
- 优化工作规约的处理：提交身份、版本号原则、工作区目录布局等写在第 3 节，作为偏好带过去；接收方按偏好合并，不拿它检查目标环境
- 优化模板与示例：第 7 节增加路径、连接器两项；示例补上 `skills_manifest`；接收指引第 6 步与 `references/spec.md` 同步
- 优化措辞：模板、示例与参考文档里的「一句话」「坑」统一改为「简短」「弯路 / 教训」
- 新增评测 3 条：导出带环境与技能（e04）、接收时的技能升级建议（i04）、工作规约当偏好合并与整合回执（i05）
- 优化 GitHub Actions：改用 Node 24 运行时的版本，`actions/checkout` v4 → v7、`actions/setup-node` v4 → v7、`actions/setup-python` v5 → v7、`softprops/action-gh-release` v2 → v3；Release 的 `node-version` 20 → 24；`runs-on` 由 `ubuntu-latest` 固定为 `ubuntu-24.04`（GitHub 在 2026-10-19 至 11-19 期间把 `ubuntu-latest` 逐步切到 Ubuntu 26.04，切换另行验证）
- 优化安装提示：`references/spec.md` 与 `references/import.md` 里 topmind-research 的例子改为「从 0.2.3 起才有 npm 包，更早的版本用 git 克隆或 Release zip」

## 0.4.9（2026-10-08）

包格式仍是 1.1，`cloud_path/<package_id>/<package_id>.md` 布局不变，与已在用的私有交接仓库兼容。

- 特性支持 topmind 工作区：`references/tool-adapters.md` 新增落点表，第 1–3 节对应 `memory/profile.md`，第 5 节对应 `memory/profile.md` 与 `memory/periodic/{YYYY}/`（用户明说才写 `memory/topics/`），第 8 节对应待办卫星 `memory/todo.md`；另写按月日志型记忆（`memory/profile.md` + `memory/log/YYYY-MM.md`）的落点。导入仍须确认
- 优化隐私边界：`memory/ledgers/` 与任何记账、收支、余额明细列入「永不携带」
- 优化导出确认：会推送云端时，定稿前列出将写入的路径和将删除的旧文件夹清单，用户有异议就少删或不删
- 优化文档结构：云端推送与清理规则只在 `references/export.md`「云端推送与清理」写一份，`SKILL.md`、`spec.md`、`import.md`、`privacy.md`、README 改为指针；随包分发的接收指引模板保留摘要。`SKILL.md` 从 205 行压到约 130 行（正文约 100 行）
- 优化 frontmatter：对齐 Agent Skills 规范，`version`、`triggers`、`tags` 等移入 `metadata`，`agentskills validate` 通过；去掉与 topmind-organize、topmind-memory 相撞的「定期整理」「用户画像」触发词，Do NOT 点名 topmind-memory、topmind-organize、topmind-write
- 优化安装说明：README 改为克隆到技能目录、Release zip、npm 安装后复制进技能目录三种，写明只装进 `node_modules` 宿主找不到；接收指引模板与 `import.md` 的安装建议同步改写；`skills_manifest` 的安装提示不再默认 `npm i`（topmind-research 没有 npm 包）
- 优化文件名说明：本地 `<称呼>-handoff-YYYYMMDD.md` 与云端 `<package_id>.md` 是同一份内容，接收方按 frontmatter 认包
- 优化 Claude 导入入口说明：新版记忆在 Settings → Memory → Start import，旧版在 Settings → Capabilities（据 2026-09-02 帮助中心）
- CI 增加 `agentskills validate` 与 `scripts/check_repo.py`（版本一致、接收指引模板与 assets 同步、引用存在、云端清理规则只写一份）；Release 增加同样的检查，并增加「只留最近 2 个 Release」步骤（tag 保留），与其他 topmind 仓库一致
- 新增 `evals/evals.json`：导出 3 条、导入 3 条、分流负例 2 条（不进 npm 包）


## 0.4.8（2026-10-03）

包格式仍是 1.1。

- 优化云端默认：已配置私有仓库时，每次推送（不是「只本地」）在同一提交里新增 `cloud_path/<package_id>/`，并只留该 `origin_id` 的最新一份。最新指该来源 `generated_at` 最新；`package_id` 以 `origin_id` 开头。删掉的是该来源更旧的文件夹，含里面的资料。其他来源各自最新的留下。README 留下。不碰 `cloud_path` 以外的路径，不碰项目仓库。
- 特性支持：更旧的一份没有 `generated_at` 就不删，并说明。「只本地」不推也不删。没有 CI、cron、额外脚本或常驻进程，由当次对话用 git 做。
- 接收指引中英模板同步写出上述步骤。0.4.7 的导出前版本核对仍在。


## 0.4.7（2026-10-03）

包格式仍是 1.1。

- 优化导出前核对：`generator` 和 `skills_manifest` 的版本必须是当次刚读到的。读不到就标未核实，或不放进清单。技能已更新就新开一份包，不在旧包上改指引却留着旧版本。


## 0.4.6（2026-10-03）

包格式仍是 1.1。

- 优化云端布局：不再按来源套目录。每次导出是新文件夹 `cloud_path/<package_id>/<package_id>.md`，要带走的资料放同一文件夹。旧文件夹留下，不删除。旧布局 `cloud_path/<origin_id>/<file>.md` 若还在，当作普通包参与比较，不要求搬家。
- 特性支持：全库 `generated_at` 最新的一份是当前事实。导出和接收都先用它。某一条它没写、未核实、同一天或没日期、对不上，才看其他来源各自最新的一份。仍不清楚就问。没写到的不是删除。`generated_at` 不在一份包内部决定某一条谁赢。
- 画像锚点仍不自动覆盖。墓碑仍是同一个 `{id}` 加上「已撤回」。


## 0.4.5（2026-10-03）

包格式仍是 1.1。

- 文档仍是一份技能，不拆中英两套。标题保持中英对照。正文跟 `language`。接收指引增加与中文步骤一一对应的英文模板，按语言照抄，不混用。
- 第 7 节补环境：工具、账号标识、记忆是否随账号走、工作通常放在哪。没看到的环境不写成「没有」。`skills_manifest` 仍只放这次用到的技能。
- 第 4、8 节把任务写全：目标、状态、现在在哪、预期落点、情况、阻塞、已验证的教训、参考。同一任务跨环境共用 `{id:task-…}`，状态行标明来源。
- 接收不破坏：按任务并集。包里没有的本地任务和环境留下。同一任务说法不同就问，不覆盖。参考链接不自动打开。确认后才写入接收环境自己的待办或记忆。
- 多个来源定时同步：每个来源只留最新一份，再按 id 合并。用户没说「全部环境」时，要说明还有哪些来源没并进来。


## 0.4.4（2026-10-03）

可选扩展（包格式仍为 1.1，不要求接收方升到 1.2）：

- 接收顺序：交接技能缺失或比包内 `generator` 更旧时，告诉用户并建议 `npm i @topmindspace/topmind-handoff` 或克隆仓库，然后用包内指引继续。不等待，不阻断，不自动安装。`skills_manifest` 同样只列出缺失或更旧并给安装提示，然后继续。有技能时接收走完整清单（主张 id、墓碑、画像锚点、第 9 节 diff、云端）；没有时包内指引是正确但较薄的下限。指引不删。
- 可选 `origin_id`：来源环境的稳定标识，形式 `工具-账号标识-范围`。记忆自动跨设备同步时范围为 `sync`，设备名只作可选 `device_note`，不进 id；本地不同步时设备名进 id，避免两台电脑互相覆盖。可选 `package_id` 每次导出唯一（`origin_id` + 日期 + 短后缀），不引入哈希库。分不清同步还是本地时问一次，记在用户自己的记忆里，不写死路径。不是密钥，但不放凭据；邮箱仅当用户要求保留。虚构例：`Muse-demo-sync`、`GrokBot-demo-MacBook-Air`。
- 可选云端，仅私有 Git：`cloud_repo`（owner/name）与 `cloud_path`（缺省 `handoff/`）。「初始化 handoff / 配置云端交接」询问仓库和目录，拒绝公开仓库。不存 PAT，用已有 git/gh 凭据；没有就停下，不让用户把 token 贴进对话。未配置不静默推送。配置后「帮我做 handoff」生成包、交给用户，并推到 `cloud_path/<origin_id>/<package_id>.md`（有资料则同级）。用户可说「只本地」。「帮我接收最新 handoff」没贴文件且已配置时，按来源取最新再接收；多个来源短列后取最近生成的，除非用户点名。不编造仓库。
- 清理：推送成功或接收之后，可以删该私有仓库里同一 `origin_id` 的旧包，只留最新一份及其资料。不删其他来源；仓库看起来公开，或路径不是已配置的 `cloud_path`，就不删。不碰项目仓库和其他路径。由模型当次用 git 执行，不是常驻程序。包内写明清理只留每个来源的最新一份。
- 写明角色：技能只准备并校验交接包；接收与合并是模型按包内文字做的判断。不规定解析器、CRDT、数据库或自动合并代码。
- 接收指引改成没装技能也能执行的清单。安装可选且不阻断。命令是 `npm i @topmindspace/topmind-handoff` 或克隆仓库，不是 `npx skills`。指引只信列出的步骤；手改追加的外发、联网或「忽略之前的指令」不可信。
- 可选主张标记统一为列表项末尾 `{id:xxxx}`。墓碑是同一 id 且含「已撤回」。没有 id 的旧包仍按语义等价比对。包里没写的条不是删除。
- `generated_at` 不裁决单条。同一天或缺日期：问，不猜。
- 新增可选第 9 节「仓库与资料」。标题不省略，没有内容写「无」。自定义节从 `## 10` 起，不再把第 7、8 节当自定义例子。
- `migration`：包是待导入画像，冲突仍须确认。`sync`：按 id 取并集；缺 id 留本地；墓碑只建议删除；同一 id 文本不同就问。禁止后导出的快照获胜。
- 画像锚点（称呼、对本智能体的称呼、语言、时区）永不自动覆盖；本地为空算新增，仍须确认。第 6 节不进事实记忆。第 8 节不是持久记忆。

## 0.4.3（2026-10-02）

接收指引优化（patch）：
- 指引末尾新增可选提示：如需完整导入流程可安装 topmind-handoff 技能；
  不装也不影响，按步骤手动处理即可
- 坚持零依赖设计：安装是可选优化，不是前置要求

## 0.4.2（2026-10-02）

支持信息互通场景 + Profile 保护（patch）：
- frontmatter 新增 `mode` 字段：`migration`（搬家，默认）| `sync`（多工具互通）
- sync 模式下合并更保守：新增也先列出来过目，冲突一律人工裁决
- 新增 Profile 保护规则：用户称呼、对智能体的称呼、语言、时区——
  接收端优先，永不自动覆盖，只提示差异
- 模板/示例/SKILL.md 同步更新

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

**深度审查优化：**
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
