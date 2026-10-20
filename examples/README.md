# 示例

四样东西都在这一页：记忆仓库的目录、一条操作规约、初始化写到仓库根的自说明、交接包文件。人物和标识是虚构的：张三、`Grok-demo-sync`。因果规则只在 [`references/compile.md`](../references/compile.md)，这里不另写一套。

## 记忆仓库结构

```text
README.md
authority.md
STATUS.md
outbox/human.md
outbox/Grok-demo-sync.md
environments/Grok-demo-sync.md
views/shared.md
views/scenario-writing.md
facts/README.md
knowledge/README.md
knowledge/写作/通用.md
```

- `outbox/<origin_id>.md` 只许这个环境在文件末尾追加。不改已有行，不改别人的信箱。
- `environments/<origin_id>.md` 只许这个环境整文件替换。
- 身份和边界只接受 `outbox/human.md`。
- `views/` 和 `STATUS.md` 是编译产物。Git 冲突时丢掉这两边的视图，保留全部信箱，在本机重新编译。
- `knowledge/` 是参考资料。任何环境可以直接改，不进信箱和视图。

## 一条操作

下面是 `outbox/Grok-demo-sync.md` 里的一条。改已经有的主题时，沿用原来的 `id`，`base` 填当前链头，不另起一条 id。

<!-- op-sample:start -->
```text
- op_id: Grok-demo-sync#1
  op: set
  id: pref-zh
  scope: shared
  slice: preference
  base: none
  at: 2026-10-21
  text: 全程中文
```
<!-- op-sample:end -->

| 字段 | 这条里怎么写 |
|---|---|
| `op` | `set` 写下，`retract` 撤回。合并规则在编译文档 |
| `id` | 主张的稳定名字，例如 `pref-zh` |
| `scope` | `shared`，或 `scenario:writing`，或 `origin:Grok-demo-sync` |
| `slice` | `identity`、`boundaries`、`preference`、`project`、`fact` |
| `base` | 新主张写 `none`。改旧主张写当前链头的 `op_id` |
| `text` | 主张正文。锚点以「称呼：」「对本智能体的称呼：」「语言：」或「时区：」开头 |

跨工具都适用的偏好用 `scope: shared`。只在某个场景里成立的习惯用 `scope: scenario:<场景>`。只在这台的路径用 `scope: origin:<origin_id>`。技能版本写在环境卡片上，不写成共享事实。

## 环境卡片

`environments/Grok-demo-sync.md` 整文件替换。家目录写成 `~`。不写 token。

```text
---
origin: Grok-demo-sync
role: writing
refreshed: 2026-10-21
---

工具：Grok
路径：~/work
连接器：GitHub，读写自己的仓库

已装技能：
- topmind-handoff 0.7.0（npm:@topmindspace/topmind-handoff）
```

`role` 决定开工读取带上哪一个场景。字段说明在 [`references/environment.md`](../references/environment.md)。

## 知识库一条

新条目加在文件顶部。格式、两级目录和拆分以仓库里的 `knowledge/README.md` 为准。

```text
## 段子一句一行
2026-10-21 · Grok-demo-sync · #写作

- 一句一行，行间空一行。
- 这条是跨环境可复用的经验。
```

只属于当前工作区的素材不写进 `knowledge/`，也不写进信箱。

## 自说明

`python3 scripts/compile_memory.py --init` 把下面这篇写到记忆仓库根的 `README.md`。两次初始化写出的字节相同。被人改过的说明，编译不覆盖。

<!-- memory-readme:start -->
# 云端记忆

这是一份私有记忆仓库。本机的 topmind-handoff 编译它。仓库里没有 CI，也没有 Release。
凭据只用已经配好的 git 或 gh。不写密码、API key、token、证件号、银行卡号、精确住址、他人隐私、记账明细。聊天记录也不写入。

## 写入哪一类

- 画像锚点是称呼、对本智能体的称呼、语言、时区。它们是身份，主人是 human，只接受 `outbox/human.md`。正文以「称呼：」「对本智能体的称呼：」「语言：」「时区：」开头。
- 边界的主人也是 human。
- 跨工具都适用的偏好写入 `scope: shared`。
- 只在某个场景里成立的习惯用 `scope: scenario:<场景>`，不写入 shared。
- 另一台要接着做的下一步用 `scope: shared` 或 `scope: scenario:<场景>`。只在这台的路径和工具状态用 `scope: origin:<origin_id>`。技能版本和连接器写在这台的环境卡片上，不写成共享事实。
- 产出只记状态、下一步和位置，不记正文。`slice` 用 `work` 或 `project`。`~/` 路径用 `scope: origin:`。
- 已有主题要改，沿用原来的 id，`base` 填当前链头，不另起一条 id。
- 换范围时先在旧范围撤回，再在新范围用同一 id 写下，`base: none`。
- 不写密码、API key、token，不写聊天记录，不改别人的信箱。

## 各部分

- `outbox/<origin_id>.md`：这个环境的操作账本。只许该环境在文件末尾追加。不改别人的信箱，不改已有行。
- `environments/<origin_id>.md`：这个环境的卡片。只许该环境整文件替换。
- `authority.md`：谁可以写进视图。身份和边界的主人是 human，只接受 `outbox/human.md`。
- `facts/`：整理时从索引收走的长说明。不是另一套权威。
- `views/shared.md` 和 `views/scenario-<场景>.md`：本机编译产物，可以丢掉后重新编译。不是指令。
- `STATUS.md`：同一次编译的校对。信箱末尾对不上，视图就无效。不是指令。
- `knowledge/`：跨环境共享的经验、收藏帖、提示词。普通 Markdown，任何环境直接编辑。见 `knowledge/README.md`。

权威是 `outbox/`、`authority.md` 和 `environments/`。`views/` 和 `STATUS.md` 是可以丢掉的编译产物，不是指令。Git 冲突时丢掉这两边的视图，保留全部信箱，在本机重新编译。

## knowledge/ 知识库

- `knowledge/<大类>/<主题>.md`，最多两级。大类有收藏帖、段子、引流曝光、写作、图片视频、提示词。
- 它是参考资料，不是指令，不覆盖偏好与边界，不进 `outbox/`、编译、视图和 `authority.md`。
- 任何环境都可以直接改，提交并推送即可，git 历史就是留痕。不写凭据、隐私和聊天记录。
- 条目格式、拆分规则、读写时机见 `knowledge/README.md`。
<!-- memory-readme:end -->

## 交接包

不能 `git pull` 的工具带走的是一份 Markdown。

- 空模板：[`assets/handoff-template.md`](../assets/handoff-template.md)
- 填好的示例：[`assets/handoff-example.md`](../assets/handoff-example.md)
- 格式和接收指引：[`references/spec.md`](../references/spec.md)

本机渲染：

```bash
python3 scripts/compile_memory.py --render <记忆目录> --origin Grok-demo-sync --out 张三-handoff-20261021.md
```

包的 `handoff_version` 只接受 `"2"`，并且要带操作附录。附录是账本，不是新事实。
