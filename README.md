# topmind-handoff

![topmind-handoff — 多个环境，一份能接手的记忆](assets/cover.jpg)

跨工具的用户记忆，放在你自己的私有 Git 仓库里。每个环境只往自己的信箱追加操作，本机脚本编译出共享视图和场景视图。不能拉取仓库的工具，用同一份结果渲染成 Markdown 交接包（`handoff_version: "2"`）。

技能只做这一件事。它不依赖别的技能，也不替你写日常备忘、整理笔记或出稿。

English: cross-tool memory kept in your own private git repo. Each environment appends to its own outbox, and a local script compiles a shared view plus one view per scenario. Tools that cannot pull the repo get a version 2 Markdown package. Install and update with npx. The skill stores no token, and the memory repo needs no CI or Release.

## 安装和更新

宿主读的是技能目录里的 `topmind-handoff/SKILL.md`。需要 Node.js 18+ 来执行安装命令，需要 Python 3 来编译。编译不联网。

```bash
npx @topmindspace/topmind-handoff@latest install
npx @topmindspace/topmind-handoff@latest update
```

`install` 默认写到 `~/.agents/skills/topmind-handoff/`。其他宿主用 `--to` 指到它的技能目录：

```bash
npx @topmindspace/topmind-handoff@latest install --to ~/.claude/skills
npx @topmindspace/topmind-handoff@latest install --to ~/.codex/skills
npx @topmindspace/topmind-handoff@latest install --to ~/.cursor/skills
```

`update` 不带 `--to` 时，会逐个更新上面四个全局目录里已经装过的副本。

| 本机情况 | 结果 |
|---|---|
| 还没有这份技能 | `Installed topmind-handoff <版本>` |
| 版本相同 | `Already up to date: topmind-handoff <版本>` |
| 本机更旧 | `Upgraded topmind-handoff <旧> -> <新>`，就地换掉，不留备份目录 |
| 本机更新 | 保持不动。要覆盖时加 `--force` |

也可以全局安装后用同一条命令：`npm i -g @topmindspace/topmind-handoff`，然后 `topmind-handoff install` 或 `topmind-handoff update`。

从 Git 安装时，目录本身就是技能目录：

```bash
git clone --depth 1 https://github.com/topmindspace/topmind-handoff.git ~/.agents/skills/topmind-handoff
git -C ~/.agents/skills/topmind-handoff pull
```

装好的目录里要有 `SKILL.md`、`references/`、`assets/`、`examples/`、`topmind_handoff/` 和 `scripts/compile_memory.py`。

## 你怎么说

步骤在 [`SKILL.md`](SKILL.md)。没点名方向时，「做个交接」「做个handoff」「工作交接」先整合读得到的最新记忆，再把这台的新操作写回。

| 你说 | 做的事 |
|---|---|
| 「初始化 handoff」「配置云端交接」 | 空的私有目录写骨架、自说明、`knowledge/`，编译空视图，做一个本地提交。公开仓库会拒绝 |
| 「更新云端记忆」 | 只追加本环境信箱，或只替换本环境卡片。编译后，确认了再推送 |
| 「按云端记忆接手」「帮我接收最新 handoff」 | `--check` 通过后读开工投影。确认后写入本工具，不覆盖已有正文 |
| 「给我一份交接包」「导出记忆」 | 从本机仓库渲染。断网也可以 |
| 「整理云端记忆」 | 索引仍是一条主张一行。超过预算才收成目录，长说明进 `facts/`。不改信箱 |
| 「沉淀经验」「记个经验」「收藏帖子」「存提示词」 | 写进记忆仓库的 `knowledge/`。普通 Markdown，不进编译 |
| 「这台以写作为主」 | 该场景的直接写入权交给这台。其他环境只能提议 |

「记住这个」、整理本机笔记、当前工作区里的素材、出稿，都不走这里。

## 两套目录

技能目录是装进来的程序。记忆仓库是你的私有数据，本机另有一个克隆，不是技能目录。

仓库文件：

```text
SKILL.md                         # 智能体怎么做交接
references/compile.md            # 编译规则，只此一份
references/spec.md               # 交接包格式 2，含接收指引
references/import.md             # 接收时怎么合并
references/export.md             # 人要做的写入步骤
references/environment.md        # 环境卡片、安装和升级
references/tool-adapters.md      # 写到各工具的哪个文件
references/privacy.md            # 什么不能写
assets/cover.jpg                 # 仓库封面图
assets/handoff-template.md       # 交接包空模板
assets/handoff-example.md        # 交接包示例
examples/README.md               # 记忆仓库结构、一条规约、自说明
topmind_handoff/                 # 本机编译器
scripts/compile_memory.py
bin/topmind-handoff.js           # 安装器。npm 包和 Git 仓库里有，技能目录里不需要
```

记忆仓库（`--init` 写出来的形状）：

```text
README.md                        # 自说明。被人改过的不覆盖
authority.md                     # 谁可以写进视图
STATUS.md                        # 校对。信箱末尾对不上，视图就无效
outbox/<origin_id>.md            # 该环境只许在末尾追加
environments/<origin_id>.md      # 该环境只许整文件替换
views/shared.md                  # 编译产物，可以丢掉再编译
views/scenario-<场景>.md
facts/                           # 整理时收走的长说明
knowledge/                       # 经验、收藏、提示词。不进编译
```

目录里每一项谁能写、一条操作长什么样、自说明全文、交接包文件在哪，见 [`examples/README.md`](examples/README.md)。因果规则只在 [`references/compile.md`](references/compile.md)。

## 隐私

技能本身没有用户数据。示例只用 `张三` 和 `Grok-demo-sync`。密码、token、证件号、银行卡号、精确住址、他人隐私、记账明细不进入信箱或包。交接包只在你自己的工具之间流转。详见 [`references/privacy.md`](references/privacy.md)。

## 能力与恢复边界

| 能力 | 程序保证与限制 |
|---|---|
| 权限 | human 已标为身份或边界的 id，其他环境换类别、换范围或卡片覆盖项都不能改写 |
| 视图完整性 | 检查全部权威输入、编译器和生成文件内容；旧 STATUS 需要重新编译。开工读取会自行拒绝失效视图 |
| 重复操作 | 同 id、同内容和来源才幂等跳过；矛盾重复拒绝 |
| 自动链头与工作同步 | `--set` / `--retract` / `--resolve` / `--work` 自动算 `op_id`、接当前链头 `base` 并重编；默认每环境一份【当前工作】同步进展，支持 `--topic` 专项交接与 `--done` 清理 |
| 离线重放 | 先模拟依赖和裁决（`--replay`）；缺依赖时零写入。v2 单来源附录不保证全新账本独立重建 |
| 隐私 | 本地阻断明显凭据、私钥形状和个人主目录；其余语义隐私继续人工检查 |
| 复核 | 实际开工显式传用户时区下的 `--today YYYY-MM-DD`；未刷新状态写在派生产物，不改其他环境卡片 |
| 初始化私有性 | `--public` 拒绝；`--private` 是调用方声明，远端可见性要由联网操作层另行核实 |

`--check`、`--startup`、`--open` 只读。`--set`、`--retract`、`--resolve`、`--work` 追加本环境信箱并自动重新编译；普通编译会重写视图和 STATUS；`--render` 内部会编译；`--organize` 写派生产物；`--init` 创建骨架和本地提交。校验失败先重新编译，缺因果依赖先补齐可信操作，隐私命中先处理输入；不要手改视图。

应用的会话状态和待确认队列留在原工作区。handoff 接收已确认的语义候选，保存操作及产出指针。集成应复用原确认机制，避免复制会话全文或另建事实真源。各宿主实际可写位置与持久化能力需现场核实；目前没有通用宿主写入器。

## 版本

当前技能版本 `0.7.3`，交接包格式 `2`。更新记录见 [`CHANGELOG.md`](CHANGELOG.md)。
