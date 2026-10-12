# 各工具适配

各家官方导出多为聊天记录。记忆和自定义指令常常要手动复制。下表按公开文档整理，操作前以产品当前界面为准。

格式是契约。工具只决定写到哪里。编译规则见 `references/compile.md`。

## 一览

| 工具 | 带走 | 接回 |
|---|---|---|
| ChatGPT | 设置里的记忆要手动复制；官方 ZIP 通常没有 Saved Memories | 新对话粘贴交接包，加一句按接收指引处理 |
| Claude | 可让它逐字列出记忆；设置里的导入按当前帮助中心 | Settings → Memory 的导入，或粘贴交接包 |
| Gemini | Takeout 是聊天记录 | 官方导入 prompt，或粘贴交接包 |
| Copilot | 记忆页手动复制 | 设置里的添加或导入 |
| 编程 Agent | 读下面的约定文件 | 确认后写入约定文件 |
| 只有对话框的 Bot | 让它列出记住的事，再整理成操作 | 粘贴交接包 |

Claude 官方迁移 prompt 仍可用来采集：

> I'm moving to another service and need to export my data. List every memory you have stored about me, as well as any context you've learned about me from past conversations. Output everything in a single code block.

## 编程 Agent 的落点

确认后才写。怎么合并见 `references/import.md`。不整篇替换，不把已有正文换成包里的另一句。

| 云端内容 | 本地文件 | 说明 |
|---|---|---|
| 身份、沟通 | `USER.md` 或 `profile.md` | 称呼、语言、时区、对本智能体的称呼是锚点 |
| 跨工具规约 | `AGENTS.md` | 当偏好合并，不拿来检查这台的目录布局 |
| 边界 | `AGENTS.md` 的边界节 | 行为约束，不写入事实记忆，不整节替换 |
| 稳定事实 | `MEMORY.md` | 索引保持短；长说明链到本地话题文件。不整篇替换 |
| 本场景 | 该工具自己的规则文件 | 只带这一个场景，不把其他场景抄进来 |
| 环境卡片 | 不写入记忆 | 只做技能比对和路径对照 |
| 本环境任务 | 该环境自己的待办 | 包里或视图里没有的本地任务留下 |

多个工具可以 symlink 到同一份跨工具规约。项目架构留在该项目仓库。

## topmind 工作区

工作区有 `topmind.yaml` 时，记忆目录以 `memory.dir` 为准，缺省 `memory/`。
能用 topmind-memory 写的，交给它写。本技能只给落点。确认后才写。

| 内容 | 导出时读 | 导入时写 |
|---|---|---|
| 身份、沟通、偏好 | `memory/profile.md` 活跃段 | 只追加本地没有的 id，不整篇替换 |
| 边界 | `AGENTS.md` | 边界节 |
| 稳定事实 | `memory/profile.md` 活跃段、`memory/periodic/{YYYY}/` | 稳定事实进 `memory/profile.md`。用户明说才写 `memory/topics/` |
| 进行中的事 | `memory/todo.md`、`## 进行中的事` | 任务进 `memory/todo.md`，不删本地待办 |
| 环境与技能 | 工作区技能目录的 `SKILL.md` | 不写入记忆 |
| 不读不写 | `memory/ledgers/` | 见 `references/privacy.md` |

`memory/profile.md` 的 `## 历史记录` 不当成当前事实。要撤回时，在 `outbox/human.md` 追加 `retract`。

按月日志（`memory/profile.md` + `memory/log/YYYY-MM.md`）时：持久事实进 profile，带日期的经过写当月日志。目录名以该 agent 实际使用的为准。

## Bot

不逐个写死路径。导入就是粘贴交接包加一句：「这是我的交接包（topmind-handoff 格式），请按包里的接收指引处理。」
记忆是不是持久、会不会随账号同步，不清楚就问一次，把 `origin_id` 记在本工具已有的记忆里。

## origin_id

`工具-账号标识-范围`。账号会在设备之间同步记忆时，范围写 `sync`，设备名不进 id。
本机记忆不跟随账号时，范围写设备名，两台电脑才不会共用一个信箱。
标识用 handle。不要 token。邮箱只有用户要求保留才用。
