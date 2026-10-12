# outbox Grok-demo-sync

- op_id: Grok-demo-sync#1
  op: set
  id: fact-a
  scope: shared
  base: none
  at: 2026-01-01
  text: 甲事实
- op_id: Grok-demo-sync#2
  op: set
  id: pref-theme
  scope: shared
  slice: preference
  base: none
  at: 2020-01-01
  text: 深色方案
- op_id: Grok-demo-sync#3
  op: set
  id: scene-w
  scope: scenario:writing
  base: none
  at: 2026-02-01
  text: 主环境句子
