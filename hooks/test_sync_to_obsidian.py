#!/usr/bin/env python3
"""sync_to_obsidian.py のユニットテスト

対象: _strip_system_content, _is_real_user_input, _format_tool_call
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

# テスト対象モジュールをインポート
sys.path.insert(0, str(Path(__file__).parent))
import sync_to_obsidian as mod
from sync_to_obsidian import _strip_system_content, _is_real_user_input, _format_tool_call


FIXED_NOW = datetime(2026, 4, 17, 12, 34, 56)
FIXED_LATER = datetime(2026, 4, 17, 12, 35, 40)


# ══════════════════════════════════════════════════════════════
# _strip_system_content
# ══════════════════════════════════════════════════════════════
class TestStripSystemContent(unittest.TestCase):
    """正規表現ベースのタグ除去。壊れやすいため境界条件を重点的にテスト"""

    # ── 基本除去 ──

    def test_strip_system_reminder(self):
        text = "<system-reminder>some noise</system-reminder>"
        self.assertEqual(_strip_system_content(text), "")

    def test_strip_command_message(self):
        text = "<command-message>terse-mode</command-message>"
        self.assertEqual(_strip_system_content(text), "")

    def test_strip_command_name(self):
        text = "<command-name>/terse-mode</command-name>"
        self.assertEqual(_strip_system_content(text), "")

    # ── 複数タグ ──

    def test_strip_multiple_tags(self):
        text = (
            "<command-message>terse-mode</command-message>\n"
            "<command-name>/terse-mode</command-name>"
        )
        self.assertEqual(_strip_system_content(text), "")

    def test_strip_mixed_tag_types(self):
        text = (
            "<system-reminder>noise</system-reminder>"
            "<command-message>cmd</command-message>"
            "<command-name>name</command-name>"
        )
        self.assertEqual(_strip_system_content(text), "")

    # ── タグ内改行（re.DOTALL） ──

    def test_multiline_system_reminder(self):
        text = "<system-reminder>\nline1\nline2\nline3\n</system-reminder>"
        self.assertEqual(_strip_system_content(text), "")

    def test_multiline_with_markdown(self):
        text = (
            "<system-reminder>\n"
            "# Heading\n"
            "- bullet\n"
            "```code```\n"
            "</system-reminder>"
        )
        self.assertEqual(_strip_system_content(text), "")

    # ── タグ + 実テキスト混在 ──

    def test_tag_with_real_text_after(self):
        text = "<system-reminder>noise</system-reminder>\n探索して"
        self.assertEqual(_strip_system_content(text), "探索して")

    def test_tag_with_real_text_before(self):
        text = "質問です\n<system-reminder>noise</system-reminder>"
        self.assertEqual(_strip_system_content(text), "質問です")

    def test_real_text_between_tags(self):
        text = (
            "<command-message>cmd</command-message>\n"
            "これが本文\n"
            "<command-name>name</command-name>"
        )
        self.assertEqual(_strip_system_content(text), "これが本文")

    # ── Skill 注入 ──

    def test_skill_injection_removed(self):
        text = "Base directory for this skill: /path/to/skill\n\n# Skill Name\nLots of content..."
        self.assertEqual(_strip_system_content(text), "")

    def test_skill_injection_after_tag_strip(self):
        """タグ除去後に残ったテキストがSkill注入パターンの場合"""
        text = (
            "<command-message>wise</command-message>\n"
            "<command-name>/wise</command-name>\n"
            "Base directory for this skill: /path\n\n# Wise Mode\ncontent"
        )
        self.assertEqual(_strip_system_content(text), "")

    def test_non_skill_text_starting_with_base(self):
        """'Base' で始まるが Skill 注入ではないテキスト"""
        text = "Based on the analysis, we should..."
        self.assertEqual(_strip_system_content(text), "Based on the analysis, we should...")

    # ── エッジケース ──

    def test_empty_string(self):
        self.assertEqual(_strip_system_content(""), "")

    def test_whitespace_only(self):
        self.assertEqual(_strip_system_content("   \n\t  "), "")

    def test_plain_text_unchanged(self):
        text = "これは普通のユーザー入力です"
        self.assertEqual(_strip_system_content(text), text)

    def test_mismatched_tags_still_stripped(self):
        """開始と終了が異なるタグ名でも除去される（正規表現が独立マッチ）。
        システムタグ同士のクロスマッチは実害なし"""
        text = "<system-reminder>content</command-name>"
        self.assertEqual(_strip_system_content(text), "")

    def test_angle_brackets_in_normal_text(self):
        """HTML風のテキストが誤って除去されない"""
        text = "Use <div> for layout"
        self.assertEqual(_strip_system_content(text), "Use <div> for layout")

    def test_nested_tags_not_greedy(self):
        """複数タグが貪欲マッチで1つに結合されない"""
        text = (
            "<system-reminder>A</system-reminder>"
            "KEEP THIS"
            "<system-reminder>B</system-reminder>"
        )
        self.assertEqual(_strip_system_content(text), "KEEP THIS")


# ══════════════════════════════════════════════════════════════
# _is_real_user_input
# ══════════════════════════════════════════════════════════════
class TestIsRealUserInput(unittest.TestCase):
    """フィルタ漏れ = Obsidian にゴミが出力される。False negative/positive 両方テスト"""

    # ── str 入力 ──

    def test_plain_text_is_real(self):
        self.assertTrue(_is_real_user_input("探索して"))

    def test_empty_string_not_real(self):
        self.assertFalse(_is_real_user_input(""))

    def test_whitespace_only_not_real(self):
        self.assertFalse(_is_real_user_input("   \n  "))

    def test_system_tag_only_not_real(self):
        self.assertFalse(
            _is_real_user_input("<system-reminder>noise</system-reminder>")
        )

    def test_command_tags_only_not_real(self):
        text = (
            "<command-message>terse-mode</command-message>\n"
            "<command-name>/terse-mode</command-name>"
        )
        self.assertFalse(_is_real_user_input(text))

    def test_tag_plus_real_text_is_real(self):
        text = "<system-reminder>noise</system-reminder>\n質問です"
        self.assertTrue(_is_real_user_input(text))

    def test_skill_injection_not_real(self):
        text = "Base directory for this skill: /path\n\n# Skill\ncontent"
        self.assertFalse(_is_real_user_input(text))

    # ── list 入力: text ブロック ──

    def test_list_with_text_block_is_real(self):
        content = [{"type": "text", "text": "探索して"}]
        self.assertTrue(_is_real_user_input(content))

    def test_list_with_empty_text_block_not_real(self):
        content = [{"type": "text", "text": ""}]
        self.assertFalse(_is_real_user_input(content))

    def test_list_with_tag_only_text_not_real(self):
        content = [{"type": "text", "text": "<system-reminder>x</system-reminder>"}]
        self.assertFalse(_is_real_user_input(content))

    # ── list 入力: tool_result ブロック ──

    def test_list_tool_result_only_not_real(self):
        content = [
            {
                "type": "tool_result",
                "tool_use_id": "abc",
                "content": "result data",
            }
        ]
        self.assertFalse(_is_real_user_input(content))

    def test_list_tool_result_plus_tag_text_not_real(self):
        content = [
            {"type": "tool_result", "tool_use_id": "abc", "content": "data"},
            {"type": "text", "text": "<system-reminder>x</system-reminder>"},
        ]
        self.assertFalse(_is_real_user_input(content))

    def test_list_tool_result_plus_real_text_is_real(self):
        content = [
            {"type": "tool_result", "tool_use_id": "abc", "content": "data"},
            {"type": "text", "text": "実際のユーザー入力"},
        ]
        self.assertTrue(_is_real_user_input(content))

    # ── list 入力: str 要素 ──

    def test_list_with_plain_string_is_real(self):
        content = ["普通のテキスト"]
        self.assertTrue(_is_real_user_input(content))

    def test_list_with_tag_string_not_real(self):
        content = ["<system-reminder>noise</system-reminder>"]
        self.assertFalse(_is_real_user_input(content))

    # ── エッジケース ──

    def test_empty_list_not_real(self):
        self.assertFalse(_is_real_user_input([]))

    def test_none_not_real(self):
        self.assertFalse(_is_real_user_input(None))

    def test_int_not_real(self):
        self.assertFalse(_is_real_user_input(42))

    def test_dict_not_real(self):
        """list でも str でもない dict → False"""
        self.assertFalse(_is_real_user_input({"type": "text", "text": "hello"}))

    def test_list_with_unknown_block_type_not_real(self):
        content = [{"type": "image", "source": "data:..."}]
        self.assertFalse(_is_real_user_input(content))


# ══════════════════════════════════════════════════════════════
# _format_tool_call
# ══════════════════════════════════════════════════════════════
class TestFormatToolCall(unittest.TestCase):
    """ツール種別ごとの分岐。出力形式の正確性とクラッシュ耐性"""

    # ── Bash ──

    def test_bash_basic(self):
        result = _format_tool_call("Bash", {"command": "ls -la"})
        self.assertIn("$ ls -la", result)
        self.assertIn("🔧", result)

    def test_bash_with_description(self):
        result = _format_tool_call("Bash", {"command": "ls", "description": "List files"})
        self.assertIn("$ ls", result)
        self.assertIn("List files", result)

    def test_bash_empty_command(self):
        result = _format_tool_call("Bash", {"command": ""})
        self.assertIn("🔧", result)
        # クラッシュしない

    def test_bash_no_command_key(self):
        result = _format_tool_call("Bash", {})
        self.assertIn("🔧", result)

    # ── Read / Write / Edit ──

    def test_read(self):
        result = _format_tool_call("Read", {"file_path": "/tmp/test.py"})
        self.assertIn("Read", result)
        self.assertIn("/tmp/test.py", result)

    def test_write(self):
        result = _format_tool_call("Write", {"file_path": "/tmp/out.py"})
        self.assertIn("Write", result)
        self.assertIn("/tmp/out.py", result)

    def test_edit(self):
        result = _format_tool_call("Edit", {"file_path": "/tmp/edit.py"})
        self.assertIn("Edit", result)
        self.assertIn("/tmp/edit.py", result)

    def test_read_empty_path(self):
        result = _format_tool_call("Read", {"file_path": ""})
        self.assertIn("Read", result)

    def test_read_no_path_key(self):
        result = _format_tool_call("Read", {})
        self.assertIn("Read", result)

    # ── Glob ──

    def test_glob_basic(self):
        result = _format_tool_call("Glob", {"pattern": "**/*.py"})
        self.assertIn("Glob", result)
        self.assertIn("**/*.py", result)

    def test_glob_with_path(self):
        result = _format_tool_call("Glob", {"pattern": "*.md", "path": "/src"})
        self.assertIn("*.md", result)
        self.assertIn("/src", result)

    def test_glob_without_path(self):
        result = _format_tool_call("Glob", {"pattern": "*.md"})
        self.assertIn("*.md", result)
        self.assertNotIn(" in ", result)

    # ── Grep ──

    def test_grep_basic(self):
        result = _format_tool_call("Grep", {"pattern": "TODO"})
        self.assertIn("Grep", result)
        self.assertIn("TODO", result)

    def test_grep_with_path(self):
        result = _format_tool_call("Grep", {"pattern": "def foo", "path": "/src"})
        self.assertIn("def foo", result)
        self.assertIn("/src", result)

    def test_grep_without_path(self):
        result = _format_tool_call("Grep", {"pattern": "error"})
        self.assertNotIn(" in ", result)

    # ── Agent ──

    def test_agent(self):
        result = _format_tool_call("Agent", {"description": "Search codebase"})
        self.assertIn("Agent", result)
        self.assertIn("Search codebase", result)

    def test_agent_empty_description(self):
        result = _format_tool_call("Agent", {"description": ""})
        self.assertIn("Agent", result)

    # ── Skill ──

    def test_skill_basic(self):
        result = _format_tool_call("Skill", {"skill": "commit"})
        self.assertIn("/commit", result)

    def test_skill_with_args(self):
        result = _format_tool_call("Skill", {"skill": "terse-mode", "args": "ultra"})
        self.assertIn("/terse-mode", result)
        self.assertIn("ultra", result)

    def test_skill_without_args(self):
        result = _format_tool_call("Skill", {"skill": "commit", "args": ""})
        # args が空なので余計なスペースだけが付く等の問題がないか
        self.assertIn("/commit", result)

    # ── フォールバック ──

    def test_unknown_tool(self):
        result = _format_tool_call("CustomTool", {"key": "value"})
        self.assertIn("CustomTool", result)
        self.assertIn("🔧", result)

    def test_unknown_tool_empty_input(self):
        result = _format_tool_call("Something", {})
        self.assertIn("Something", result)

    # ── 全ツールで str が返る ──

    def test_all_return_str(self):
        tools = [
            ("Bash", {"command": "echo hi"}),
            ("Read", {"file_path": "/f"}),
            ("Write", {"file_path": "/f"}),
            ("Edit", {"file_path": "/f"}),
            ("Glob", {"pattern": "*"}),
            ("Grep", {"pattern": "x"}),
            ("Agent", {"description": "d"}),
            ("Skill", {"skill": "s"}),
            ("Unknown", {}),
        ]
        for name, inp in tools:
            with self.subTest(tool=name):
                result = _format_tool_call(name, inp)
                self.assertIsInstance(result, str)
                self.assertTrue(len(result) > 0)


# ══════════════════════════════════════════════════════════════
# Local logging / main / Obsidian sync
# ══════════════════════════════════════════════════════════════
class TestLocalLogging(unittest.TestCase):
    def _payload(self, cwd: str) -> dict:
        return {
            "session_id": "session-1234567890",
            "cwd": cwd,
            "tool_name": "Bash",
            "tool_input": {
                "command": "pytest",
                "description": "Run test suite",
            },
            "tool_result": "PASS",
        }

    def test_post_tool_use_creates_local_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = mod.write_local_log(
                self._payload(tmpdir), "PostToolUse", now=FIXED_NOW
            )

            self.assertIsNotNone(log_file)
            self.assertTrue(log_file.exists())
            content = log_file.read_text(encoding="utf-8")
            self.assertIn("# Claude Code Session Log", content)
            self.assertIn("**Project:** " + Path(tmpdir).name, content)
            self.assertIn("**Session:** session-1234567890", content)
            self.assertIn("### [12:34] `Bash` — Run test suite", content)
            self.assertIn("```bash\npytest\n```", content)
            self.assertIn("PASS", content)

            session_map = Path(tmpdir) / ".claude" / "log" / ".sessions"
            self.assertTrue(session_map.exists())
            self.assertIn("session-1234567890", session_map.read_text(encoding="utf-8"))

    def test_stop_reuses_same_file_even_if_session_map_is_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = self._payload(tmpdir)
            first_log = mod.write_local_log(payload, "PostToolUse", now=FIXED_NOW)
            self.assertIsNotNone(first_log)

            session_map = Path(tmpdir) / ".claude" / "log" / ".sessions"
            session_map.unlink()

            stop_payload = {"session_id": payload["session_id"], "cwd": tmpdir}
            stop_log = mod.write_local_log(stop_payload, "Stop", now=FIXED_LATER)

            self.assertEqual(first_log, stop_log)
            content = first_log.read_text(encoding="utf-8")
            self.assertIn("> Turn ended at 12:35:40", content)

    def test_missing_session_id_skips_local_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = mod.write_local_log({"cwd": tmpdir}, "PostToolUse", now=FIXED_NOW)
            self.assertIsNone(result)
            self.assertFalse((Path(tmpdir) / ".claude" / "log").exists())


class TestSyncToObsidian(unittest.TestCase):
    def test_sync_session_to_obsidian_writes_note(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            project_dir = root / "project"
            project_dir.mkdir()
            vault_dir = root / "vault"
            vault_dir.mkdir()
            transcript_path = root / "transcript.jsonl"
            transcript_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "type": "user",
                                "message": {"content": "調べて"},
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "type": "assistant",
                                "message": {
                                    "content": [
                                        {"type": "text", "text": "了解です"},
                                        {
                                            "type": "tool_use",
                                            "name": "Bash",
                                            "input": {"command": "ls"},
                                        },
                                        {
                                            "type": "tool_result",
                                            "content": "hooks\nREADME.md",
                                        },
                                    ]
                                },
                            },
                            ensure_ascii=False,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = {"session_id": "session-1234567890", "cwd": str(project_dir)}
            with mock.patch.object(mod, "VAULT_DIR", str(vault_dir)):
                with mock.patch.object(
                    mod, "get_transcript_path", return_value=transcript_path
                ):
                    note_path = mod.sync_session_to_obsidian(payload, now=FIXED_NOW)

            self.assertEqual(note_path, vault_dir / "2026-04-17 project.md")
            self.assertTrue(note_path.exists())
            content = note_path.read_text(encoding="utf-8")
            self.assertIn("project: project", content)
            self.assertIn("session: session-", content)
            self.assertIn("### 👤 User\n調べて", content)
            self.assertIn("### 🤖 Claude", content)
            self.assertIn("🔧 `$ ls`", content)
            self.assertIn("```result\nhooks\nREADME.md\n```", content)

    def test_sync_session_to_obsidian_returns_none_when_vault_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = {"session_id": "session-1234567890", "cwd": tmpdir}
            with mock.patch.object(mod, "VAULT_DIR", ""):
                note_path = mod.sync_session_to_obsidian(payload, now=FIXED_NOW)
            self.assertIsNone(note_path)


class TestMain(unittest.TestCase):
    def test_main_writes_local_log_when_called_with_event_arg(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = {
                "session_id": "session-1234567890",
                "cwd": tmpdir,
                "tool_name": "Read",
                "tool_input": {"file_path": "README.md"},
                "tool_result": "",
            }
            with mock.patch.object(mod, "_now", return_value=FIXED_NOW):
                mod.main(
                    ["sync_to_obsidian.py", "PostToolUse"],
                    json.dumps(payload, ensure_ascii=False),
                )

            log_file = Path(tmpdir) / ".claude" / "log" / "2026-04-17_123456.md"
            self.assertTrue(log_file.exists())
            content = log_file.read_text(encoding="utf-8")
            self.assertIn("### [12:34] `Read` — `README.md`", content)

    def test_main_ignores_empty_stdin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.object(mod, "_now", return_value=FIXED_NOW):
                mod.main(["sync_to_obsidian.py", "PostToolUse"], "")
            self.assertFalse((Path(tmpdir) / ".claude" / "log").exists())


if __name__ == "__main__":
    unittest.main()
