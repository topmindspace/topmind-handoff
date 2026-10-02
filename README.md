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

```bash
# npm 安装（v0.4.0+）
npm i @topmindspace/topmind-handoff
# 或直接 clone
git clone https://github.com/topmindspace/topmind-handoff.git
```

### 导出（带走你的上下文）

对你的 AI 助手说：

> "用 topmind-handoff 技能，把关于我的上下文导出成一份交接包。"

技能会：采集 → 分类 → 冲突裁决 → 脱敏（列清单给你确认）→ 落盘。
你拿到 `<称呼>-handoff-YYYYMMDD.md`，带着它去任何新工具。

### 导入（在新工具里接收）

把交接包贴进新对话，附上一句：

> "这是我的交接包（topmind-handoff 格式），请按包里的接收指引处理。"

0.4.0+ 的包自带 4 行接收指引，没装技能的 AI 照着做就行。
装了本技能的助手会走完整流程（校验 → 解析 → diff → 确认 → 合并），
diff 出新增/冲突/已撤回三类，冲突等你拍板后再合并。

## 仓库结构

```
topmind-handoff/
├── SKILL.md                    # 技能本体（精简：目的/流程/输出/纪律）
├── references/
│   ├── spec.md                 # 交接包格式规范 v1.0（frontmatter + 六节）
│   ├── export.md               # 导出工作流：采集→分类→裁决→脱敏→落盘
│   ├── import.md               # 导入工作流：校验→解析→比对→确认→合并（含反投毒）
│   ├── privacy.md              # 隐私硬线：永不携带清单、脱敏手法、分享警告
│   └── tool-adapters.md        # 各工具适配：ChatGPT/Claude/Gemini/Copilot/编程 Agent
├── assets/
│   ├── handoff-template.md     # 空白交接包模板
│   └── handoff-example.md      # 填写示例（虚构占位数据）
├── CHANGELOG.md
└── LICENSE (MIT)
```

## 交接包长什么样

```yaml
---
handoff_version: "1.0"
generated_at: 2026-10-01T15:30:00+08:00
generator: "Claude Code + topmind-handoff 0.4.0"
language: zh-CN
scope: private
---
```

> **给 AI 的接收指引**：0.4.0+ 的包在 frontmatter 之后自带 4 行固定指引，
> 没装技能的 AI 照着做就行（模板见 `references/spec.md`）。

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

当前技能版本 `0.3.1`，交接包格式 `1.0`。更新记录见 `CHANGELOG.md`。
