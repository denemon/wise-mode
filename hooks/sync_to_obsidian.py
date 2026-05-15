#!/usr/bin/env python3
"""Unified Claude Code hook: local session logging + optional Obsidian sync."""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Obsidian vault path — set your vault path to enable sync, leave empty to disable
VAULT_DIR = ""

LOG_DIRNAME = ".claude/log"
SESSION_MAP_NAME = ".sessions"
SESSION_MARKER_PREFIX = "**Session:** "

# ── システムタグ除去 ──────────────────────────────────────────
_SYSTEM_TAGS = re.compile(
    r"<(?:system-reminder|command-message|command-name)>.*?</(?:system-reminder|command-message|command-name)>",
    re.DOTALL,
)

# Skill 注入パターン（"Base directory for this skill:" で始まるブロック）
_SKILL_INJECTION = re.compile(
    r"^Base directory for this skill:.*",
    re.DOTALL,
)


def _now() -> datetime:
    return datetime.now()


def _safe_json_loads(raw: str) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _project_root(payload: dict[str, Any]) -> Path:
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        return Path(env_root)
    cwd = payload.get("cwd")
    if isinstance(cwd, str) and cwd:
        return Path(cwd)
    return Path(os.getcwd())


def _extract_session_id(payload: dict[str, Any]) -> str:
    session_id = payload.get("session_id", "")
    return session_id if isinstance(session_id, str) else ""


def _detect_event_type(payload: dict[str, Any], argv: list[str]) -> str:
    if len(argv) > 1 and argv[1]:
        return argv[1]

    for key in ("hook_event_name", "event_name", "event_type", "hook_event"):
        value = payload.get(key, "")
        if isinstance(value, str) and value:
            return value

    return ""


def _log_dir(payload: dict[str, Any]) -> Path:
    return _project_root(payload) / LOG_DIRNAME


def _session_map_path(log_dir: Path) -> Path:
    return log_dir / SESSION_MAP_NAME


def _load_session_map(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    mapping: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        session_id, log_path = line.split("=", 1)
        if session_id and log_path:
            mapping[session_id] = log_path
    return mapping


def _save_session_map(path: Path, mapping: dict[str, str]) -> None:
    lines = [f"{session_id}={log_path}" for session_id, log_path in sorted(mapping.items())]
    text = "\n".join(lines)
    if text:
        text += "\n"
    path.write_text(text, encoding="utf-8")


def _find_log_file_by_session_id(log_dir: Path, session_id: str) -> Path | None:
    marker = f"{SESSION_MARKER_PREFIX}{session_id}"
    for path in sorted(log_dir.glob("*.md")):
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip() == marker:
                    return path
        except OSError:
            continue
    return None


def _create_session_log_file(
    log_dir: Path, session_id: str, project_name: str, now: datetime
) -> Path:
    date_part = now.strftime("%Y-%m-%d")
    time_part = now.strftime("%H%M%S")
    candidate = log_dir / f"{date_part}_{time_part}.md"
    suffix = 1

    while candidate.exists():
        candidate = log_dir / f"{date_part}_{time_part}_{suffix}.md"
        suffix += 1

    header = (
        "# Claude Code Session Log\n"
        f"**Date:** {date_part}\n"
        f"**Start:** {now.strftime('%H:%M:%S')}\n"
        f"**Project:** {project_name}\n"
        f"{SESSION_MARKER_PREFIX}{session_id}\n\n"
        "---\n"
    )
    candidate.write_text(header, encoding="utf-8")
    return candidate


def _resolve_log_file(payload: dict[str, Any], now: datetime) -> Path | None:
    session_id = _extract_session_id(payload)
    if not session_id:
        return None

    log_dir = _log_dir(payload)
    log_dir.mkdir(parents=True, exist_ok=True)

    session_map_path = _session_map_path(log_dir)
    session_map = _load_session_map(session_map_path)
    existing_path = session_map.get(session_id)
    if existing_path:
        existing = Path(existing_path)
        if existing.exists():
            return existing

    reconstructed = _find_log_file_by_session_id(log_dir, session_id)
    if reconstructed is not None:
        session_map[session_id] = str(reconstructed)
        _save_session_map(session_map_path, session_map)
        return reconstructed

    project_name = _project_root(payload).name
    created = _create_session_log_file(log_dir, session_id, project_name, now)
    session_map[session_id] = str(created)
    _save_session_map(session_map_path, session_map)
    return created


def _stringify_tool_result(raw_result: Any) -> str:
    if isinstance(raw_result, (dict, list)):
        return json.dumps(raw_result, ensure_ascii=False, indent=2)
    return str(raw_result) if raw_result else ""


def _format_tool_input_summary(inp: Any) -> str:
    if not inp:
        return ""
    try:
        summary = json.dumps(inp, ensure_ascii=False)
    except TypeError:
        summary = str(inp)
    if len(summary) > 200:
        summary = summary[:200] + "..."
    return summary


def _format_quote_block(text: str) -> str:
    return "\n".join("> " + line if line else ">" for line in text.splitlines())


def _format_post_tool_use_entry(payload: dict[str, Any], now: datetime) -> str:
    ts = now.strftime("%H:%M")
    tool = payload.get("tool_name", "")
    inp = payload.get("tool_input", {})
    raw_result = payload.get("tool_result", "")
    result = _stringify_tool_result(raw_result)
    lines: list[str] = []

    if not isinstance(inp, dict):
        inp = {}

    if tool == "Bash":
        cmd = inp.get("command", "")
        desc = inp.get("description", "")
        header = f"### [{ts}] `Bash`"
        if desc:
            header += f" — {desc}"
        lines.append(header)
        if cmd:
            lines.append(f"```bash\n{cmd}\n```")
        if result:
            lines.append(
                f"<details><summary>result</summary>\n\n```\n{result}\n```\n</details>"
            )

    elif tool == "Read":
        fp = inp.get("file_path", "")
        lines.append(f"### [{ts}] `Read` — `{fp}`")

    elif tool == "Write":
        fp = inp.get("file_path", "")
        lines.append(f"### [{ts}] `Write` — `{fp}`")

    elif tool == "Edit":
        fp = inp.get("file_path", "")
        old = inp.get("old_string", "")
        new = inp.get("new_string", "")
        lines.append(f"### [{ts}] `Edit` — `{fp}`")
        if old or new:
            lines.append("```diff")
            for line in str(old).splitlines():
                lines.append(f"- {line}")
            for line in str(new).splitlines():
                lines.append(f"+ {line}")
            lines.append("```")

    elif tool == "Glob":
        pattern = inp.get("pattern", "")
        path = inp.get("path", "")
        header = f"### [{ts}] `Glob` — `{pattern}`"
        if path:
            header += f" in `{path}`"
        lines.append(header)
        if result:
            lines.append(f"```\n{result}\n```")

    elif tool == "Grep":
        pattern = inp.get("pattern", "")
        path = inp.get("path", "")
        glob_filter = inp.get("glob", "")
        header = f"### [{ts}] `Grep` — `{pattern}`"
        if path:
            header += f" in `{path}`"
        if glob_filter:
            header += f" (`{glob_filter}`)"
        lines.append(header)
        if result:
            lines.append(f"```\n{result}\n```")

    elif tool == "Agent":
        desc = inp.get("description", "")
        prompt = inp.get("prompt", "")
        agent_type = inp.get("subagent_type", "")
        header = f"### [{ts}] `Agent`"
        if agent_type:
            header += f" ({agent_type})"
        if desc:
            header += f" — {desc}"
        lines.append(header)
        if prompt:
            prompt_lines = prompt.splitlines()
            if len(prompt_lines) > 5:
                prompt = "\n".join(prompt_lines[:5]) + "\n..."
            lines.append(_format_quote_block(prompt))

    elif tool == "Skill":
        skill = inp.get("skill", "")
        args = inp.get("args", "")
        header = f"### [{ts}] `Skill` — /{skill}"
        if args:
            header += f" {args}"
        lines.append(header)

    else:
        lines.append(f"### [{ts}] `{tool}`")
        summary = _format_tool_input_summary(inp)
        if summary:
            lines.append(f"```json\n{summary}\n```")
        if result:
            lines.append(
                f"<details><summary>result</summary>\n\n```\n{result}\n```\n</details>"
            )

    return "\n".join(lines)


def write_local_log(
    payload: dict[str, Any], event_type: str, *, now: datetime | None = None
) -> Path | None:
    if event_type not in {"PostToolUse", "Stop"}:
        return None

    current_time = now or _now()
    log_file = _resolve_log_file(payload, current_time)
    if log_file is None:
        return None

    with log_file.open("a", encoding="utf-8") as f:
        if event_type == "PostToolUse":
            entry = _format_post_tool_use_entry(payload, current_time)
            if entry:
                f.write(f"\n{entry}\n")
        elif event_type == "Stop":
            f.write(f"\n---\n> Turn ended at {current_time.strftime('%H:%M:%S')}\n")

    return log_file


def _strip_system_content(text: str) -> str:
    """システムタグと Skill 注入コンテンツを除去"""
    text = _SYSTEM_TAGS.sub("", text)
    text = text.strip()
    # Skill 注入判定: 残ったテキストが "Base directory for this skill:" で始まる場合
    if _SKILL_INJECTION.match(text):
        return ""
    return text


def get_transcript_path(session_id: str) -> Path | None:
    pattern = str(Path.home() / ".claude/projects/**/*.jsonl")
    for f in glob.glob(pattern, recursive=True):
        if session_id in f:
            return Path(f)
    return None


# ── ユーザーメッセージが「本物のユーザー入力」か判定 ──────────────────
def _is_real_user_input(content) -> bool:
    """
    content が tool_result ブロック *だけ* で構成されている場合は
    ツール実行の返送であり、ユーザーが実際に書いた入力ではない。
    """
    if isinstance(content, str):
        cleaned = _strip_system_content(content)
        return bool(cleaned.strip())
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text = block.get("text", "")
                    cleaned = _strip_system_content(text)
                    if cleaned.strip():
                        return True
            elif isinstance(block, str):
                cleaned = _strip_system_content(block)
                if cleaned.strip():
                    return True
        return False
    return False


# ── テキスト抽出（user / assistant 共通） ─────────────────────────
def extract_text(content, *, role: str = "assistant") -> str:
    if isinstance(content, str):
        if role == "user":
            return _strip_system_content(content)
        return content.strip()

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                text = block.strip()
                if role == "user":
                    text = _strip_system_content(text)
                if text:
                    parts.append(text)
                continue
            if not isinstance(block, dict):
                continue

            t = block.get("type", "")

            if t == "text":
                text = block.get("text", "").strip()
                if role == "user":
                    text = _strip_system_content(text)
                if text:
                    parts.append(text)

            elif t == "tool_use":
                name = block.get("name", "tool")
                inp = block.get("input", {})
                # ツール呼び出しをコンパクトに表示
                summary = _format_tool_call(name, inp)
                parts.append(summary)

            elif t == "tool_result":
                # ユーザーターンでは tool_result は除外
                if role == "user":
                    continue
                res = block.get("content", "")
                if isinstance(res, list):
                    res = "\n".join(
                        r.get("text", "") for r in res if isinstance(r, dict)
                    )
                if isinstance(res, str) and res.strip():
                    parts.append(f"```result\n{res.strip()}\n```")

        return "\n\n".join(parts)

    return ""


def _format_tool_call(name: str, inp: dict) -> str:
    """ツール呼び出しを読みやすい1行〜数行に整形"""
    if name == "Bash":
        cmd = inp.get("command", "")
        desc = inp.get("description", "")
        label = f"🔧 `$ {cmd}`"
        if desc:
            label += f" — {desc}"
        return label

    if name == "Read":
        fp = inp.get("file_path", "")
        return f"🔧 `Read {fp}`"

    if name == "Write":
        fp = inp.get("file_path", "")
        return f"🔧 `Write {fp}`"

    if name == "Edit":
        fp = inp.get("file_path", "")
        return f"🔧 `Edit {fp}`"

    if name == "Glob":
        pattern = inp.get("pattern", "")
        path = inp.get("path", "")
        s = f"🔧 `Glob {pattern}`"
        if path:
            s += f" in `{path}`"
        return s

    if name == "Grep":
        pattern = inp.get("pattern", "")
        path = inp.get("path", "")
        s = f"🔧 `Grep {pattern}`"
        if path:
            s += f" in `{path}`"
        return s

    if name == "Agent":
        desc = inp.get("description", "")
        return f"🔧 `Agent` — {desc}"

    if name == "Skill":
        skill = inp.get("skill", "")
        args = inp.get("args", "")
        s = f"🔧 `/{skill}`"
        if args:
            s += f" {args}"
        return s

    # フォールバック
    return f"🔧 `{name}`"


# ── JSONL → Markdown 変換 ─────────────────────────────────────
def jsonl_to_markdown(jsonl_path: Path) -> str:
    lines: list[str] = []

    with open(jsonl_path, encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type")
            msg = entry.get("message", {})
            content_raw = msg.get("content", "")

            if entry_type == "user":
                if not _is_real_user_input(content_raw):
                    continue
                content = extract_text(content_raw, role="user")
                if content:
                    lines.append(f"### 👤 User\n{content}")

            elif entry_type == "assistant":
                content = extract_text(content_raw, role="assistant")
                if content:
                    lines.append(f"### 🤖 Claude\n{content}")

    return "\n\n---\n\n".join(lines)


def sync_session_to_obsidian(
    payload: dict[str, Any], *, now: datetime | None = None
) -> Path | None:
    if not VAULT_DIR:
        return None

    vault = Path(VAULT_DIR)
    if not vault.exists():
        return None

    session_id = _extract_session_id(payload)
    if not session_id:
        return None

    transcript_path = get_transcript_path(session_id)
    if not transcript_path:
        return None

    current_time = now or _now()
    project_path = _project_root(payload)
    project_name = project_path.name
    date_str = current_time.strftime("%Y-%m-%d")
    note_path = vault / f"{date_str} {project_name}.md"

    body = jsonl_to_markdown(transcript_path)
    header = f"""---
project: {project_name}
session: {session_id[:8]}
date: {date_str}
updated: {current_time.strftime("%H:%M:%S")}
---

# {project_name} - {date_str}

"""
    note_path.write_text(header + body, encoding="utf-8")
    return note_path


def main(argv: list[str] | None = None, stdin_text: str | None = None) -> None:
    argv = list(sys.argv if argv is None else argv)
    stdin_text = sys.stdin.read() if stdin_text is None else stdin_text

    payload = _safe_json_loads(stdin_text)
    if not payload:
        return

    current_time = _now()
    event_type = _detect_event_type(payload, argv)
    if event_type:
        write_local_log(payload, event_type, now=current_time)

    sync_session_to_obsidian(payload, now=current_time)


if __name__ == "__main__":
    main()
