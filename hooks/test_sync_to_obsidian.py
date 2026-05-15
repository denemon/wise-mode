#!/usr/bin/env python3
"""sync_to_obsidian.py のユニットテスト

対象: _strip_system_content, _is_real_user_input, _format_tool_call
"""
import json
import os
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


class _EnvIsolatedTestCase(unittest.TestCase):
    """CLAUDE_PROJECT_DIR を payload.cwd より優先で読むため、
    テスト実行環境の env が漏れ込むと payload で指定した tmpdir 以外に
    ログが書き込まれ得る。各テストの前に env を空に固定する。"""

    def setUp(self) -> None:
        patcher = mock.patch.dict(
            os.environ, {"CLAUDE_PROJECT_DIR": ""}, clear=False
        )
        patcher.start()
        self.addCleanup(patcher.stop)


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
        self.assertNotIn("/commit ", result)  # 末尾に余計なスペース無し

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
# extract_text
# ══════════════════════════════════════════════════════════════
class TestExtractText(unittest.TestCase):
    """役割別テキスト抽出 — user は system タグ除去、assistant は素通り"""

    def test_string_user_strips_system_tags(self):
        out = mod.extract_text(
            "<system-reminder>x</system-reminder>本文", role="user"
        )
        self.assertEqual(out, "本文")

    def test_string_assistant_preserves_content(self):
        self.assertEqual(mod.extract_text("通常の応答", role="assistant"), "通常の応答")

    def test_list_text_block(self):
        out = mod.extract_text(
            [{"type": "text", "text": "hello"}], role="assistant"
        )
        self.assertEqual(out, "hello")

    def test_list_tool_use_formatted(self):
        out = mod.extract_text(
            [{"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}],
            role="assistant",
        )
        self.assertIn("🔧 `$ ls`", out)

    def test_list_tool_result_assistant_wraps_in_result_block(self):
        out = mod.extract_text(
            [{"type": "tool_result", "content": "output"}],
            role="assistant",
        )
        self.assertIn("```result\noutput\n```", out)

    def test_list_tool_result_user_role_skipped(self):
        """user ターンの tool_result はノイズなので除外"""
        out = mod.extract_text(
            [{"type": "tool_result", "content": "stuff"}], role="user"
        )
        self.assertEqual(out, "")

    def test_list_tool_result_with_list_content(self):
        """tool_result の content が list の場合は text 要素を結合"""
        out = mod.extract_text(
            [
                {
                    "type": "tool_result",
                    "content": [
                        {"type": "text", "text": "line1"},
                        {"type": "text", "text": "line2"},
                    ],
                }
            ],
            role="assistant",
        )
        self.assertIn("line1\nline2", out)

    def test_list_str_elements_user_role_stripped(self):
        out = mod.extract_text(
            ["<system-reminder>x</system-reminder>", "本文"], role="user"
        )
        self.assertEqual(out, "本文")

    def test_list_empty_text_block_skipped(self):
        out = mod.extract_text(
            [{"type": "text", "text": ""}, {"type": "text", "text": "real"}],
            role="assistant",
        )
        self.assertEqual(out, "real")

    def test_non_str_non_list_returns_empty(self):
        self.assertEqual(mod.extract_text(None), "")
        self.assertEqual(mod.extract_text(42), "")
        self.assertEqual(mod.extract_text({"x": 1}), "")


# ══════════════════════════════════════════════════════════════
# _format_post_tool_use_entry
# ══════════════════════════════════════════════════════════════
class TestFormatPostToolUseEntry(unittest.TestCase):
    """ローカルログ用エントリ整形 — ツール別分岐とフォールバック"""

    def _call(self, tool: str, inp: dict, result=""):
        return mod._format_post_tool_use_entry(
            {"tool_name": tool, "tool_input": inp, "tool_result": result},
            FIXED_NOW,
        )

    def test_bash_with_result_has_details_block(self):
        out = self._call("Bash", {"command": "ls", "description": "list"}, "a\nb")
        self.assertIn("### [12:34] `Bash` — list", out)
        self.assertIn("```bash\nls\n```", out)
        self.assertIn("<details><summary>result</summary>", out)
        self.assertIn("a\nb", out)

    def test_bash_no_command_skips_code_block(self):
        out = self._call("Bash", {})
        self.assertIn("### [12:34] `Bash`", out)
        self.assertNotIn("```bash", out)

    def test_edit_with_old_new_produces_diff(self):
        out = self._call("Edit", {
            "file_path": "/f.py",
            "old_string": "old1\nold2",
            "new_string": "new1\nnew2",
        })
        self.assertIn("### [12:34] `Edit` — `/f.py`", out)
        self.assertIn("```diff", out)
        self.assertIn("- old1", out)
        self.assertIn("- old2", out)
        self.assertIn("+ new1", out)
        self.assertIn("+ new2", out)

    def test_edit_without_old_new_skips_diff(self):
        out = self._call("Edit", {"file_path": "/f.py"})
        self.assertIn("`Edit`", out)
        self.assertNotIn("```diff", out)

    def test_glob_with_path_and_result(self):
        out = self._call(
            "Glob", {"pattern": "*.py", "path": "/src"}, "a.py\nb.py"
        )
        self.assertIn("`Glob` — `*.py`", out)
        self.assertIn("in `/src`", out)
        self.assertIn("a.py\nb.py", out)

    def test_grep_with_glob_filter(self):
        out = self._call(
            "Grep",
            {"pattern": "TODO", "path": "/src", "glob": "*.py"},
            "match",
        )
        self.assertIn("`Grep` — `TODO`", out)
        self.assertIn("in `/src`", out)
        self.assertIn("(`*.py`)", out)

    def test_agent_long_prompt_truncated_at_five_lines(self):
        long_prompt = "\n".join(f"line{i}" for i in range(10))
        out = self._call(
            "Agent",
            {"description": "d", "subagent_type": "Explore", "prompt": long_prompt},
        )
        self.assertIn("`Agent` (Explore) — d", out)
        self.assertIn("> line0", out)
        self.assertIn("> line4", out)
        self.assertNotIn("line5", out)  # 5 行で切り詰め
        self.assertIn("> ...", out)

    def test_skill_with_args(self):
        out = self._call("Skill", {"skill": "wise", "args": "implement X"})
        self.assertIn("### [12:34] `Skill` — /wise implement X", out)

    def test_skill_without_args_no_trailing_space(self):
        out = self._call("Skill", {"skill": "wise"})
        self.assertIn("### [12:34] `Skill` — /wise", out)
        self.assertNotIn("/wise ", out)

    def test_unknown_tool_fallback_serializes_input_and_result(self):
        out = self._call("Custom", {"key": "val"}, "result data")
        self.assertIn("### [12:34] `Custom`", out)
        self.assertIn('"key": "val"', out)
        self.assertIn("result data", out)

    def test_non_dict_input_does_not_crash(self):
        out = mod._format_post_tool_use_entry(
            {"tool_name": "Bash", "tool_input": "not a dict"},
            FIXED_NOW,
        )
        self.assertIn("`Bash`", out)

    def test_long_tool_input_summary_truncated(self):
        big = {"key": "x" * 500}
        out = self._call("Custom", big)
        self.assertIn("...", out)  # 200 文字で切り詰め

    def test_dict_result_serialized_as_json(self):
        out = self._call("Bash", {"command": "x"}, {"a": 1, "b": [1, 2]})
        self.assertIn('"a": 1', out)


# ══════════════════════════════════════════════════════════════
# _safe_json_loads / _load_session_map
# ══════════════════════════════════════════════════════════════
class TestSafeJsonLoads(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(mod._safe_json_loads(""), {})

    def test_whitespace(self):
        self.assertEqual(mod._safe_json_loads("  \n  "), {})

    def test_malformed(self):
        self.assertEqual(mod._safe_json_loads("{not json"), {})

    def test_valid_dict(self):
        self.assertEqual(mod._safe_json_loads('{"a": 1}'), {"a": 1})

    def test_list_returns_empty_dict(self):
        """JSON 配列は dict ではないので {} を返す"""
        self.assertEqual(mod._safe_json_loads("[1, 2, 3]"), {})

    def test_scalar_returns_empty_dict(self):
        self.assertEqual(mod._safe_json_loads("42"), {})
        self.assertEqual(mod._safe_json_loads('"str"'), {})


class TestLoadSessionMap(unittest.TestCase):
    def test_nonexistent_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(
                mod._load_session_map(Path(tmpdir) / "missing"), {}
            )

    def test_valid_lines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sessions"
            path.write_text("s1=/log/a.md\ns2=/log/b.md\n", encoding="utf-8")
            self.assertEqual(
                mod._load_session_map(path),
                {"s1": "/log/a.md", "s2": "/log/b.md"},
            )

    def test_skips_malformed_lines(self):
        """`=` を含まない行、key/value が空の行はスキップ"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sessions"
            path.write_text(
                "valid=/log/a.md\n"
                "no_equal_sign\n"
                "=missing_key\n"
                "missing_value=\n"
                "\n"
                "another=/log/b.md\n",
                encoding="utf-8",
            )
            self.assertEqual(
                mod._load_session_map(path),
                {"valid": "/log/a.md", "another": "/log/b.md"},
            )

    def test_value_with_equals_sign_preserved(self):
        """値に '=' が含まれても split(1) なので最初の '=' で分割"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sessions"
            path.write_text("s1=/path/with=eq.md\n", encoding="utf-8")
            self.assertEqual(
                mod._load_session_map(path), {"s1": "/path/with=eq.md"}
            )


# ══════════════════════════════════════════════════════════════
# Local logging / main / Obsidian sync
# ══════════════════════════════════════════════════════════════
class TestLocalLogging(_EnvIsolatedTestCase):
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


class TestJsonlToMarkdown(unittest.TestCase):
    """jsonl → Markdown 変換 — 壊れた行はスキップして耐性を確保"""

    def _write(self, lines):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        )
        f.write("\n".join(lines) + "\n")
        f.close()
        path = Path(f.name)
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return path

    def test_user_and_assistant_entries(self):
        path = self._write([
            json.dumps({"type": "user", "message": {"content": "質問"}}),
            json.dumps({
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "回答"}]},
            }),
        ])
        out = mod.jsonl_to_markdown(path)
        self.assertIn("### 👤 User\n質問", out)
        self.assertIn("### 🤖 Claude\n回答", out)
        self.assertIn("---", out)  # エントリ間セパレータ

    def test_malformed_json_lines_skipped(self):
        path = self._write([
            "{not valid json",
            json.dumps({"type": "user", "message": {"content": "本文"}}),
            "another broken",
        ])
        out = mod.jsonl_to_markdown(path)
        self.assertIn("本文", out)

    def test_empty_lines_skipped(self):
        path = self._write([
            "",
            json.dumps({"type": "user", "message": {"content": "x"}}),
            "",
        ])
        self.assertIn("👤 User", mod.jsonl_to_markdown(path))

    def test_tool_result_only_user_message_filtered(self):
        """ツール結果だけの user エントリはスキップ"""
        path = self._write([
            json.dumps({
                "type": "user",
                "message": {
                    "content": [
                        {"type": "tool_result", "content": "tool output"}
                    ]
                },
            }),
        ])
        self.assertEqual(mod.jsonl_to_markdown(path), "")


class TestSyncToObsidian(_EnvIsolatedTestCase):
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


class TestMain(_EnvIsolatedTestCase):
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
            with mock.patch.dict(
                os.environ, {"CLAUDE_PROJECT_DIR": tmpdir}
            ), mock.patch.object(mod, "_now", return_value=FIXED_NOW):
                mod.main(["sync_to_obsidian.py", "PostToolUse"], "")
            self.assertFalse((Path(tmpdir) / ".claude" / "log").exists())


if __name__ == "__main__":
    unittest.main()
