# topmind-handoff

跨工具的用户记忆：放在你自己的私有 Git 仓库里。每个环境只往自己的信箱追加操作，本机脚本编译出共享视图和场景视图。
不能拉取仓库的工具，用同一份编译结果渲染成一份 Markdown 交接包（`handoff_version: "2"`）。

English TL;DR: a private git repo of per-origin outboxes. A local script compiles the shared view and one view per scenario. Offline tools receive a version 2 Markdown package rendered from those views. No memory-repo CI, no Release, no stored token.

## 为什么这样分

画像、场景习惯、某台机器的环境，不能用同一种规则合并。
共享事实按因果链更新。场景之间保持独立。每台机器只改自己的卡片。
日期不挑选谁赢。同一条主张分叉时，两条都留下，等人裁决。

相关背景：各家官方导出仍多是聊天记录。`AGENTS.md` 适合项目指令。个人记忆还没有被广泛采用的交换标准。本技能不采用研究用的加密单元格或数据库，编译在本机完成。

## 安装

宿主只认技能目录里的 `topmind-handoff/SKILL.md`。`npm i` 若只进 `node_modules`，要再复制一次。

```bash
git clone --depth 1 https://github.com/topmindspace/topmind-handoff.git ~/.claude/skills/topmind-handoff
```

Codex 用 `~/.codex/skills/topmind-handoff`。其他宿主换成它的技能目录。
升级是在该目录里 `git pull`。目录里需要 `SKILL.md`、`references/`、`assets/`、`topmind_handoff/` 和 `scripts/compile_memory.py`。

## 日常说法

- 「做个交接」「做个handoff」「工作交接」：先整合读得到的最新记忆，再把这台的新操作写回。没点名接收或推送时走这一轮。离线有包就只接收；没有仓库先问一次。步骤在 `SKILL.md`。
- 「初始化 handoff」：空目录写骨架、一份自解释的说明、编译空视图、做一个本地提交。公开仓库会拒绝。
- 「更新云端记忆」：追加本环境的操作，本机编译，确认后和视图放在同一次提交里推送。
- 「按云端记忆接手」：`--check` 通过后跑 `--startup`。确认后写入本工具，不覆盖已有正文。
- 「给我一份交接包」：断网也能从本机仓库渲染。
- 「整理云端记忆」：把事实索引压短，标出未复核和未刷新。不改信箱。
- 「这台以写作为主」：该场景的直接写入权交给这台。其他环境只能提议。

编译规则只在 [`references/compile.md`](references/compile.md)。

## 仓库结构

```text
SKILL.md
references/compile.md          # 编译规则，只此一份
references/spec.md             # 交接包 2
references/export.md
references/import.md
references/environment.md
references/privacy.md
references/tool-adapters.md
assets/handoff-template.md
assets/handoff-example.md
topmind_handoff/               # 本机编译器
scripts/compile_memory.py
```

## 隐私

技能本身没有用户数据。密码、token、证件号、银行卡号、精确住址、他人隐私、记账明细不进入信箱或包。
导出前要你看过脱敏说明。交接包只在你自己的工具之间流转。详见 [`references/privacy.md`](references/privacy.md)。

## 版本

当前技能版本 `0.6.0`，交接包格式 `2`。更新记录见 `CHANGELOG.md`。
