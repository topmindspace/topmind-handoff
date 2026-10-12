# 编译规则（唯一规则正文）

视图由本机脚本编译。模型决定追加哪条操作、冲突问用户哪一句。模型不手写 `views/` 或 `STATUS.md`。
脚本不联网，不猜谁赢，不改信箱。

```bash
python3 scripts/compile_memory.py <记忆目录>
```

不要用整包的 generated_at 选举当前事实，也不要删除旧文件夹。
记忆仓库不配 workflow，不做 Release，不向用户要 token。没有定时任务，没有常驻进程。

## 目录

```text
README.md
authority.md
STATUS.md
views/shared.md
views/scenario-<场景>.md
facts/
environments/<origin_id>.md
outbox/<origin_id>.md
```

权威是 `outbox/`、`authority.md` 和 `environments/`。`views/` 和 `STATUS.md` 是同一次编译的结果。
`STATUS.md` 的 `compiled_from` 必须等于每个信箱文件的最后一条 `op_id`（空信箱记为 `-`）。对不上就当视图无效，重新编译后再读。

Git 合并若在 `views/` 或 `STATUS.md` 上冲突：两边的视图都丢掉，保留全部信箱，在本机重新编译。不要手改视图来完成合并。

## 三个范围

| 范围 | 谁写入视图 | 同时写 |
|---|---|---|
| `shared` | 因果链上的 `set` / `retract` | 不同 id 都留下；同一 id 分叉就冲突 |
| `scenario:<名>` | 该场景的主环境，以及 `human` | 场景文件互不合并 |
| `origin:<origin_id>` | 该环境自己的操作 | 只出现在该环境的开工读取里 |

身份（`slice: identity`）和边界（`slice: boundaries`）只接受 `outbox/human.md` 里的操作。别的环境写了 `set`，也只记成提议，不进共享视图。
场景在 `authority.md` 里有主人时，主人以外、且不是 `human` 的 `set` / `retract` 同样只记成提议。`op: propose` 永远不成为链头。

`authority.md` 的身份和边界固定是 `human`。把某台设成场景主人：

```bash
python3 scripts/compile_memory.py --own <记忆目录> --scenario writing --origin <origin_id>
```

改完主人后立刻重新编译。原先写进该场景、现在无权的 `set` 离开场景视图，记成提议。

环境卡片只有该 `origin_id` 能整文件替换。卡片上的 `override.<id>` 只在这台的开工读取里盖住共享事实，不改 `views/shared.md`。

## 操作

写在 `outbox/<origin_id>.md` 末尾。来源以文件名计，条内写的 origin 不算。

```text
- op_id: Grok-demo-sync#14
  op: set
  id: pref-zh
  scope: shared
  slice: preference
  base: none
  closes: []
  at: 2026-10-12
  text: 全程中文
  detail: |
    可选的长说明
```

- `op`：`set`、`retract`、`propose`。
- `base`：接着哪一条。新链写 `none`。
- `closes`：裁决时填当前全部链头的 `op_id`。集合刚好相等，这条成为唯一链头。多出来或少一条，这条不生效，冲突还在。
- `at`：给人看，也给定复核期用。它不挑选链头。
- 同一个 `op_id` 出现几次只计第一次。

同一条主张上，`base` 相同的两条 `set` 都留下，视图写「未裁决」，谁的日期更晚都一样。不同 id 互不影响。
`closes` 只盖住一部分链头时不生效，原来的链头还在。两条 `closes` 都刚好等于当前链头时，两条都留下，仍是未裁决。
裁决成为链头之后，后继 `set` 用它做 `base`。一条后继就是新链头。两条后继用同一个 `base`，再次未裁决。

## 开工时读什么

只读四样：共享视图、本环境卡片 `role` 对应的那一个场景、该环境卡片、与本环境有关的冲突。
`scope: origin:<本环境>` 里已经生效的条目只附在这次开工读取，不进共享视图和场景视图。别的环境写这个范围，只记成提议。
其他场景和其他环境的任务不放进这次上下文。本环境覆盖项只存在于这次投影里，并且不再带上原来的长说明。

## 整理

用户说「整理云端记忆」才运行：

```bash
python3 scripts/compile_memory.py --organize <记忆目录> --today YYYY-MM-DD
```

- 事实索引压到约 200 行或 25KB 以内。长说明移到 `facts/`，索引留一行。收起某一类时，没有长说明的短行也写进同一个 `facts/` 文件。
- 身份和边界满 180 天、偏好满 90 天、项目状态满 30 天，标「未复核」。未复核仍然有效。
- 环境卡片的 `refreshed` 满 90 天，标「未刷新」，文件保留。
- 信箱不改写。不折叠历史，除非用户另说一句要归档。

## 同一次更新里有什么

追加本环境的操作，或替换本环境的卡片，然后立刻编译。确认后的提交同时包含信箱、卡片、视图和 `STATUS.md`。
公开仓库拒绝。凭据只用已经配好的 git 或 `gh`。没有凭据就停下，不索要 token。
