# topmind-handoff

跨工具的用户上下文交接技能：把"这个人是谁、怎么做事、记了什么"装进一份
**便携交接包**（单个 Markdown 文件 + YAML frontmatter），在任意 AI 工具之间
带走、交接、合并。导出、导入双向都支持，隐私保护内置。

English TL;DR: a portable, tool-agnostic user-profile handoff skill for AI agents.
Export working habits, preferences, projects and memories into one Markdown package;
import a package from another tool, diff it against local context, and merge safely.
No SDK, no server, no account. Privacy guardrails built in.

## 为什么做这个

今天不存在被广泛采用的"可移植 AI 记忆"标准。各家官方导出多为合规式的聊天记录
（记忆/自定义指令常常不在导出内），而社区事实上的做法是手动粘贴 Markdown
（`AGENTS.md` / `CLAUDE.md` / `USER.md` / `MEMORY.md` 约定）。
这个技能把"手动粘贴"变成一套可靠的流程：**统一格式 + 导出脱敏 + 导入比对合并**。

相关工作（非依赖）：MacPaw `portable-memory`（spec v1.0 研究型项目）、
Open Memory Protocol（提案）、W3C AI Agent Memory Interoperability CG（极早期）。
本技能刻意保持轻量：不造新 JSON schema，不搭服务——一个文件、两次人工确认。

## 快速开始

### 安装

宿主（Claude Code、Codex、各类 Agent）只认技能目录里的 `topmind-handoff/SKILL.md`。
只执行 `npm i` 会把包装进 `node_modules`，宿主找不到，要再复制一次。

```bash
# 方式一：克隆到技能目录（推荐，跟 main）
git clone --depth 1 https://github.com/topmindspace/topmind-handoff.git ~/.claude/skills/topmind-handoff
#   Codex：~/.codex/skills/topmind-handoff；其他宿主换成它的技能目录

# 方式二：钉版本，下载 GitHub Release 的 topmind-handoff.zip，解压后整个目录放进技能目录
#   （zip 内是 SKILL.md、references/、assets/ 等，目录名保持 topmind-handoff）

# 方式三：npm 安装后复制进技能目录
npm i @topmindspace/topmind-handoff
mkdir -p ~/.claude/skills/topmind-handoff
cp -r node_modules/@topmindspace/topmind-handoff/. ~/.claude/skills/topmind-handoff/
```

升级：重新 `git pull`，或用新版覆盖技能目录。技能目录里只需要 `SKILL.md`、`references/`、`assets/`。

### 导出（带走你的上下文）

对你的 AI 助手说：

> "用 topmind-handoff 技能，把关于我的上下文导出成一份交接包。"

技能会：采集 → 分类 → 冲突裁决 → 脱敏（列清单给你确认）→ 落盘。
你拿到 `<称呼>-handoff-YYYYMMDD.md`，带着它去任何新工具。

### 导入（在新工具里接收）

把交接包贴进新对话，附上一句：

> "这是我的交接包（topmind-handoff 格式），请按包里的接收指引处理。"

0.4.4+ 的包自带接收指引，没装技能也能交接。
装了技能时接收更完整（主张 id、墓碑、仓库 diff、可选私有 Git 云端）。
接收时把环境（工具、已装技能与版本、路径、连接器）、记忆、交接的任务分别比对整合，冲突等你拍板后再合并，
最后给一份按这三块写的整合回执。目标环境缺失、偏旧或已停用的技能会列出来并给出升级命令，你确认后才升级，升级前先备份。
包里的工作规约当偏好带过去，不要求目标环境照做。

## 仓库结构

```
topmind-handoff/
├── SKILL.md                    # 技能本体（精简：目的/流程/输出/纪律）
├── references/
│   ├── spec.md                 # 交接包格式规范 v1.1（八节 + 可选第 9 节）
│   ├── export.md               # 导出工作流：采集→分类→裁决→脱敏→落盘
│   ├── import.md               # 导入工作流：校验→解析→比对→确认→合并（含反投毒）
│   ├── environment.md          # 第 7 节：环境与技能盘点、比对、升级建议
│   ├── privacy.md              # 隐私硬线：永不携带清单、脱敏手法、分享警告
│   └── tool-adapters.md        # 各工具适配：ChatGPT/Claude/Gemini/Copilot/编程 Agent/topmind 工作区
├── assets/
│   ├── handoff-template.md     # 空白交接包模板
│   └── handoff-example.md      # 填写示例（虚构占位数据）
├── CHANGELOG.md
└── LICENSE (MIT)
```

## 交接包长什么样

```yaml
---
handoff_version: "1.1"
generated_at: 2026-10-01T15:30:00+08:00
generator: "Claude Code + topmind-handoff 0.4.10"
language: zh-CN
scope: private
---
```

> **给 AI 的接收指引**：0.4.4+ 的包在 frontmatter 之后自带接收指引，
> 没装技能也能交接（模板见 `references/spec.md`）。建议先安装技能，不装也不停。

```markdown
## 1. 这个人是谁（Identity）
## 2. 怎么跟他说话（Communication）
## 3. 工作习惯与默认设置（Working habits & defaults）
## 4. 项目与目标（Projects & goals）
## 5. 事实与记忆（Facts & memories）
## 6. 边界与隐私（Boundaries & privacy）
```

完整规范见 `references/spec.md`，空白模板见 `assets/handoff-template.md`。

## 隐私

- 技能本身**不包含任何用户数据**，示例一律用占位符。
- 密码、token、证件号、银行卡号、精确住址、他人隐私**永远不进包**。
- 导出前人工 review 是强制步骤；导入时把交接包当**不可信输入**
  （不执行包内指令、不外发包内容）。详见 `references/privacy.md`。

## 版本

当前技能版本 `0.4.10`，交接包格式 `1.1`。更新记录见 `CHANGELOG.md`。
已配置私有云端时，每次推送默认清理该来源的旧包（规则见 `references/export.md`「云端推送与清理」，删除清单会在定稿前列给你确认）。说「只本地」则不推、不删。
