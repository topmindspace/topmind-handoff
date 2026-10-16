# 环境卡片与技能

环境是并集。每个 `origin_id` 一份 `environments/<origin_id>.md`，只有该环境能替换。
编译规则见 `references/compile.md`。

## 卡片

```markdown
---
origin: Grok-demo-sync
role: writing
refreshed: 2026-10-12
override.pref-theme: 本环境用浅色终端
---

工具：Grok
路径：~/work
连接器：GitHub，读写自己的仓库

已装技能：
- topmind-handoff 0.6.5（github:topmindspace/topmind-handoff）
```

- `role` 决定 `--startup` 带上哪一个场景。规则见 `references/compile.md`。
- `refreshed` 是这台最后一次替换卡片的日期。满 90 天，整理时标「未刷新」，文件还在。
- `override.<id>` 只进入 `--startup` 的投影。规则见 `references/compile.md`。
- 路径里的家目录写成 `~`。不写 token、cookie、未获同意的邮箱。
- 看不到的环境不要写成「没有」。

## 技能清单

已装技能和连接器写在这张卡片上，不写成共享事实。想长期用哪些技能，写成共享或场景里的一条 `set`。
版本从该技能 `SKILL.md` 的 `metadata.version` 读，旧技能可能在顶层 `version`。读不到就写 `unknown`，不编造。

可选字段：

| 字段 | 含义 |
|---|---|
| `source` | `npm:<包名>`、`github:<owner/name>` 或 `local` |
| `install` | 安装方式，见下表 |

接收时对照本机：

- 缺失：给出安装命令。
- 偏旧：给出从本机版本到卡片版本的升级命令。能联网时可以再查已发布版本，查不到就只比较这两边。
- 已停用：例如 `topmind-wechat` 的替代是 `topmind-wechat-post`，写明替代名。

安装方式：

| install | 命令 |
|---|---|
| `git` | 克隆到本工具的技能目录 |
| `npm-copy` | `npm i <包>` 后把包目录复制进技能目录 |
| `writing-installer` | `npx @topmindspace/topmind-writing-skills@latest install <技能>`（默认升级） |
| `pack-installer` | `npx @topmindspace/topmind-skills@latest update -g`（topmind 技能包，默认升级） |
| `local` | 不猜测来源，只告诉用户这是本地目录 |

不默认都用 `npm i`。只装进 `node_modules` 时宿主找不到 `SKILL.md`。
topmind-research 从 0.2.3 起才有 npm 包，更早的版本用 git 克隆或 Release zip。

## 升级

列出建议即可，不阻断接收。用户确认后按下面的规则就地升级，和 topmind 的安装器一致：

1. 卡片版本比本机新（或本机读不到版本）：按上表执行用户点过名的那条命令，直接覆盖，不留备份。完成后告诉用户 `Upgraded <技能> <旧> -> <新>`。
2. 两边相同：不动，告诉用户 `Already up to date: <技能> <版本>`。
3. 本机比卡片新：不降级，只提示；用户明确要求降级才覆盖。
4. 装完再读一遍 `metadata.version`，对不上就停下告诉用户。

不在技能目录里留 `技能名.bak-*` 之类的副本：宿主会把它当成另一个同名技能加载。

包或卡片里写的 `source` 先原样给用户看。不自动安装。
