"""The unspecified handoff round is the shipped skill text, not a compiler flag."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from topmind_handoff.cli import USAGE  # noqa: E402
from topmind_handoff.model import compiler_version  # noqa: E402


def handoff_section(skill: str) -> str:
    start = skill.index("## 工作流")
    end = skill.index("### 初始化")
    return skill[start:end]


class SkillRouteTests(unittest.TestCase):
    def test_unspecified_phrase_integrates_then_writes_back(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        section = handoff_section(skill)
        self.assertIn(f'version: "{compiler_version()}"', skill)
        for phrase in ("「做个handoff」", "「做个交接」", "「工作交接」", "「Handoff」", "「交接」", "「记忆同步」"):
            self.assertIn(phrase, section)
        self.assertLess(
            section.index("先做下面的「按云端记忆接手」"),
            section.index("再做「更新云端记忆」"),
        )
        self.assertIn("某一侧没有新内容就停在那一侧，不推空提交。", section)
        self.assertIn("没有新操作就不提交、不推送。", section)
        self.assertIn("对话里已有交接包：只做「只有交接包」。不推送。", section)
        self.assertIn("不跑 `--organize`，也不跑 `--init`。问一次", section)
        self.assertIn("「帮我接收最新 handoff」「import handoff」只做接手", section)
        self.assertIn("「给我一份交接包」「交接手册」「导出记忆」「打包记忆」「export handoff」只渲染", section)
        self.assertIn("「更新云端记忆」只写回", section)
        self.assertIn("「整理云端记忆」只整理", section)
        self.assertIn("「初始化 handoff」「配置云端交接」只初始化", section)
        self.assertIn("「这台以写作为主」「这台以某场景为主」只跑 `--own`", section)
        self.assertNotIn("--sync", USAGE)
        self.assertNotIn("--render-legacy", USAGE)
        for phrase in (
            "称呼、对本智能体的称呼、语言、时区",
            "边界的主人也是 human",
            "scope: shared",
            "scope: scenario:",
            "scope: origin:",
            "不写成共享事实",
            "不另起一条 id",
            "聊天记录",
            "不改别人的信箱",
        ):
            self.assertIn(phrase, skill)
        self.assertIn("待提炼", section)
        self.assertIn("把这份清单给用户看", section)
        self.assertIn("不自动撤回", section)
        self.assertIn("不跑 `--organize`", section)
        self.assertIn("「整理云端记忆」只整理", section)
        self.assertIn("用户说「整理云端记忆」才跑 `--organize`", skill)
        self.assertIn("没有定时任务，没有常驻进程", skill)
        self.assertNotIn("cron", skill.lower())
