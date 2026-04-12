#!/bin/bash
# cclog-hook.sh — Claude Code セッション自動ロガー（フック版）
# PostToolUse / Stop イベントで自動的にログを記録する
set -euo pipefail

EVENT_TYPE="${1:-}"
LOG_DIR="$(pwd)/.claude/log"
SESSION_MAP="$LOG_DIR/.sessions"

mkdir -p "$LOG_DIR"

# stdin から JSON を読み取る
INPUT=$(cat)

# python3 で JSON パース（macOS 標準で利用可能）
parse_field() {
  python3 -c "
import json, sys
d = json.load(sys.stdin)
keys = '$1'.split('.')
for k in keys:
    if isinstance(d, dict):
        d = d.get(k, '')
    else:
        d = ''
        break
print(d if d else '')
" <<< "$INPUT"
}

SESSION_ID=$(parse_field "session_id")

# セッションIDがなければ何もしない
if [ -z "$SESSION_ID" ]; then
  exit 0
fi

# セッションに対応するログファイルを取得/作成
LOG_FILE=""
if [ -f "$SESSION_MAP" ]; then
  LOG_FILE=$(grep "^${SESSION_ID}=" "$SESSION_MAP" 2>/dev/null | head -1 | cut -d= -f2 || true)
fi

if [ -z "$LOG_FILE" ]; then
  # 新しいセッション → ログファイル作成
  DATE_PART=$(date '+%Y-%m-%d')
  TIME_PART=$(date '+%H%M%S')
  LOG_FILE="$LOG_DIR/${DATE_PART}_${TIME_PART}.md"
  echo "${SESSION_ID}=${LOG_FILE}" >> "$SESSION_MAP"

  PROJECT_NAME=$(basename "$(pwd)")
  cat > "$LOG_FILE" << EOF
# Claude Code Session Log
**Date:** ${DATE_PART}
**Start:** $(date '+%H:%M:%S')
**Project:** ${PROJECT_NAME}

---
EOF
fi

case "$EVENT_TYPE" in
  PostToolUse)
    # 1回の python3 呼び出しで全フィールドをフォーマットしてログエントリを生成
    ENTRY=$(python3 -c "
import json, sys, datetime

d = json.load(sys.stdin)
ts = datetime.datetime.now().strftime('%H:%M')
tool = d.get('tool_name', '')
inp = d.get('tool_input', {})
raw_result = d.get('tool_result', '')

# tool_result を文字列化
if isinstance(raw_result, dict):
    result = json.dumps(raw_result, ensure_ascii=False, indent=2)
elif isinstance(raw_result, list):
    result = json.dumps(raw_result, ensure_ascii=False, indent=2)
else:
    result = str(raw_result) if raw_result else ''

lines = []

if tool == 'Bash':
    cmd = inp.get('command', '')
    desc = inp.get('description', '')
    header = f'### [{ts}] \`Bash\`'
    if desc:
        header += f' — {desc}'
    lines.append(header)
    if cmd:
        lines.append(f'\`\`\`bash\n{cmd}\n\`\`\`')
    if result:
        lines.append(f'<details><summary>result</summary>\n\n\`\`\`\n{result}\n\`\`\`\n</details>')

elif tool == 'Read':
    fp = inp.get('file_path', '')
    lines.append(f'### [{ts}] \`Read\` — \`{fp}\`')

elif tool == 'Write':
    fp = inp.get('file_path', '')
    lines.append(f'### [{ts}] \`Write\` — \`{fp}\`')

elif tool == 'Edit':
    fp = inp.get('file_path', '')
    old = inp.get('old_string', '')
    new = inp.get('new_string', '')
    lines.append(f'### [{ts}] \`Edit\` — \`{fp}\`')
    if old or new:
        lines.append(f'\`\`\`diff')
        for l in old.splitlines():
            lines.append(f'- {l}')
        for l in new.splitlines():
            lines.append(f'+ {l}')
        lines.append(f'\`\`\`')

elif tool == 'Glob':
    pattern = inp.get('pattern', '')
    path = inp.get('path', '')
    header = f'### [{ts}] \`Glob\` — \`{pattern}\`'
    if path:
        header += f' in \`{path}\`'
    lines.append(header)
    if result:
        lines.append(f'\`\`\`\n{result}\n\`\`\`')

elif tool == 'Grep':
    pattern = inp.get('pattern', '')
    path = inp.get('path', '')
    glob_filter = inp.get('glob', '')
    header = f'### [{ts}] \`Grep\` — \`{pattern}\`'
    if path:
        header += f' in \`{path}\`'
    if glob_filter:
        header += f' (\`{glob_filter}\`)'
    lines.append(header)
    if result:
        lines.append(f'\`\`\`\n{result}\n\`\`\`')

elif tool == 'Agent':
    desc = inp.get('description', '')
    prompt = inp.get('prompt', '')
    agent_type = inp.get('subagent_type', '')
    header = f'### [{ts}] \`Agent\`'
    if agent_type:
        header += f' ({agent_type})'
    header += f' — {desc}'
    lines.append(header)
    if prompt:
        prompt_lines = prompt.splitlines()
        if len(prompt_lines) > 5:
            prompt = '\n'.join(prompt_lines[:5]) + '\n...'
        lines.append(f'> {chr(10).join(\"> \" + l if i > 0 else l for i, l in enumerate(prompt.splitlines()))}')

elif tool == 'Skill':
    skill = inp.get('skill', '')
    args = inp.get('args', '')
    header = f'### [{ts}] \`Skill\` — /{skill}'
    if args:
        header += f' {args}'
    lines.append(header)

else:
    lines.append(f'### [{ts}] \`{tool}\`')
    if inp:
        summary = json.dumps(inp, ensure_ascii=False)
        if len(summary) > 200:
            summary = summary[:200] + '...'
        lines.append(f'\`\`\`json\n{summary}\n\`\`\`')
    if result:
        lines.append(f'<details><summary>result</summary>\n\n\`\`\`\n{result}\n\`\`\`\n</details>')

print('\n'.join(lines))
" <<< "$INPUT")

    printf '\n%s\n' "$ENTRY" >> "$LOG_FILE"
    ;;
  Stop)
    printf '\n---\n> Turn ended at %s\n' "$(date '+%H:%M:%S')" >> "$LOG_FILE"
    ;;
esac
