# 导出与更新

编译规则见 `references/compile.md`。本文件只写人要做的步骤。

## 更新云端记忆

1. 在记忆仓库里拉取。
2. 按类别写入。一次闲聊不进信箱。重复出现、会跨工具用的偏好才追加。
   称呼、对本智能体的称呼、语言、时区是身份锚点，只由 human 写。边界也只由 human 写。
   跨工具偏好用 `scope: shared`。场景习惯用 `scope: scenario:<场景>`，不写进 shared。
   另一台要接着做的下一步、以及产出记在哪，见 `references/compile.md`。技能版本和连接器写在环境卡片上，不写成共享事实。
   改已有主题沿用原来的 id，`base` 填当前链头，不另起一条 id。
   不写密码、API key、token、聊天记录，不改别人的信箱。
3. 知道才写。没有来源就标在 `text` 里「未核实」，不编造 `op_id` 以外的内容。`op_id` 用 `<origin_id>#` 加本文件内递增的号，不和已有号重复。
4. 只追加 `outbox/<自己的 origin_id>.md`。要改这台的路径、连接器、已装技能或覆盖项，就整文件替换 `environments/<自己的 origin_id>.md`，并更新 `refreshed`。
5. 运行 `python3 scripts/compile_memory.py <记忆目录>`。`--check` 必须通过。
6. 给用户看一段短确认：新增了哪些 id、哪几条变成未裁决、哪几条只是提议、卡片改了什么、脱敏删了什么。用户点头后再提交。
7. 同一次提交包含信箱、这台卡片、`views/` 和 `STATUS.md`。用户没说「只本地」才推送。

视图或 `STATUS.md` 发生合并冲突时，按 `references/compile.md` 丢掉视图再编译。不要手抄一边的视图盖住另一边。

## 初始化

「初始化 handoff」或「配置云端交接」：

```bash
python3 scripts/compile_memory.py --init <空目录> --private --origin <origin_id> --role <场景>
```

公开仓库拒绝，目录不会被创建。空目录会得到骨架、空视图和一次本地提交，里面没有 workflow。
然后由用户把这个目录推到自己的私有仓库。技能不创建 Release，不写 `.github/workflows`。

## 给我一份交接包

断网也可以做。

```bash
python3 scripts/compile_memory.py --render <记忆目录> --origin <origin_id> --out <称呼>-handoff-YYYYMMDD.md
```

包是 `handoff_version: "2"`。正文和 `--startup` 是同一份投影：带覆盖的共享视图、一个场景、本环境范围、冲突、未复核、环境卡片，以及 `## 10` 操作附录。
附录声明这些操作已经反映在视图里。渲染不推送，也不改其他环境的信箱。

交给用户时附上分享警告（`references/privacy.md`）。回执只给路径、冲突条数、附录里的 `op_id` 个数。不复述全文。

## 脱敏

落盘前按 `references/privacy.md` 扫描将要追加的操作、卡片和包。命中就不写入。
路径里的用户名写成 `~`。联系方式默认不写，除非用户明确要求保留。

## 这台以某场景为主

```bash
python3 scripts/compile_memory.py --own <记忆目录> --scenario <场景> --origin <origin_id>
```

只改写入权。身份和边界仍只接受 `outbox/human.md`。
