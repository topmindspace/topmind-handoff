# CHANGELOG

## 0.7.3（2026-11-15）

- **CLI 自动化写入与裁决**：新增 `--set`、`--retract`、`--resolve`、`--work`、`--replay`。自动分配递增 `op_id`、自动查找当前唯一链头填入 `base`（消除漏填 `base` 导致的伪冲突）、自动收集分叉链头填入 `closes`，完成后立即重编视图。
- **双层工作交接与跨端信息同步**：`--work` 默认按环境维护一份【当前工作】（`id: work.<origin_id>`，自动带 `[<origin_id>]` 前缀，跨环境同步进展、并行零冲突）；支持 `--local` 记本机私有工作、`--topic <专项名>` 记跨环境特定项目交接、`--done` 完结撤回清理。
- **记忆新陈代谢与排版清理**：`work` 维度纳入 30 天复核期；消除 `--startup` 与交接包投影中的重复套娃标题；规范化宿主记忆合并接口 `HostMergePlan`（`plan_host_merge` / `apply_host_merge`）；清理历史冗余代码与旧版章节号残留。

## 0.7.2（2026-10-26）

- 权限、完整性与隐私加固：human 保护绑定主张 id；`STATUS.md` 双摘要校验权威输入、编译器与派生产物；离线重放预检因果依赖；运行时阻断明显凭据与未泛化个人主目录。
- 安装与更新：支持 `npx @topmindspace/topmind-handoff@latest install` 与 `update`，就地升级不留备份副本。
- 记忆仓库模型：每个环境只追加自己的 `outbox/<origin_id>.md` 或替换自己的 `environments/<origin_id>.md`，本机编译 `views/` 与 `STATUS.md`，`knowledge/` 存放跨环境共享的经验、收藏与提示词。
