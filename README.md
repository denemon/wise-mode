# wise-mode

A collection of [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills and hooks for disciplined development — **terse-mode** for brevity, **swarm** for parallel delegation plans, **wise** for architect-mode quality gates, **wise-cont** for persistent architect mode, and **cclog** for automatic session logging.

## Components

| Name | Type | Description |
|------|------|-------------|
| **terse-mode** | Skill (`/terse-mode`) | Brevity mode — fewer words, same technical substance, with lite/full/ultra intensity levels |
| **swarm** | Skill (`/swarm`) | Low-token subagent orchestration — creates scoped agent briefs plus runnable swarm files |
| **wise** | Skill (`/wise`) | Architect mode — systematic planning, TDD, adversarial self-review, and quality gates (single task) |
| **wise-cont** | Skill (`/wise-cont`) | Continuous architect mode — activate once, applies to all subsequent messages in the session |
| **cclog** | Hook | Auto-records all Claude Code sessions to `.claude/log/` — zero token consumption |
| **sync_to_obsidian** | Hook | Syncs session transcripts to Obsidian vault as Markdown notes |

## Quick install

Run this in your **project root** (where `.git/` lives):

```bash
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/install.sh | bash
```

This installs skills into `.claude/skills/`, the cclog hook into `.claude/hooks/`, and merges hook configuration into `.claude/settings.local.json`.

### Manual install

```bash
# terse-mode
mkdir -p .claude/skills/terse-mode
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/terse-mode/SKILL.md \
  -o .claude/skills/terse-mode/SKILL.md

# swarm
mkdir -p .claude/skills/swarm
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/swarm/SKILL.md \
  -o .claude/skills/swarm/SKILL.md

# wise
mkdir -p .claude/skills/wise
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/wise/SKILL.md \
  -o .claude/skills/wise/SKILL.md
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/wise/CHECKLISTS.md \
  -o .claude/skills/wise/CHECKLISTS.md
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/wise/PATTERNS.md \
  -o .claude/skills/wise/PATTERNS.md

# wise-cont
mkdir -p .claude/skills/wise-cont
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/wise-cont/SKILL.md \
  -o .claude/skills/wise-cont/SKILL.md

# hooks
mkdir -p .claude/hooks
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/hooks/cclog-hook.sh \
  -o .claude/hooks/cclog-hook.sh
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/hooks/sync_to_obsidian.py \
  -o .claude/hooks/sync_to_obsidian.py
chmod +x .claude/hooks/cclog-hook.sh

```

If you installed an older version of the brevity skill manually, remove that old skill directory before using `terse-mode`.

For cclog, add the following to `.claude/settings.local.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/cclog-hook.sh PostToolUse",
            "timeout": 5000
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/cclog-hook.sh Stop",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

## terse-mode — Brevity Mode

When you type `/terse-mode`, the agent switches into a brevity-first response style:

- **Same technical substance** — removes filler, keeps exact terms, commands, and errors
- **3 intensity levels** — `lite`, `full`, and `ultra`
- **Auto-clarity** — temporarily returns to normal wording for destructive actions and safety warnings
- **Language-preserving** — stays in the user's language unless asked to translate

```text
/terse-mode
/terse-mode lite
/terse-mode ultra
```

Use it when you want faster, tighter answers without losing the actual fix or reasoning.

## swarm — Parallel Delegation Mode

When you type `/swarm`, the agent builds a compact parallel-work plan for tasks you explicitly want delegated:

- **Low-token discovery** — reads only the files needed to set agent boundaries
- **Conflict-safe ownership** — each agent gets an explicit write scope
- **Runnable output** — generates human-readable `.swarm/plan.md` and executable `.swarm/run.sh`
- **Smallest useful swarm** — avoids over-fragmenting simple work

```text
/swarm build agents for this feature
/swarm break this task into parallel workers
```

Use it when you want subagents or parallel execution, not for ordinary single-agent coding.

## wise — Architect Mode

When you type `/wise` in Claude Code, the agent shifts into architect mode for a **single task**:

- **Think first, code second** — 70% understanding, 30% coding
- **8-phase workflow** — from planning through PR readiness
- **TDD enforcement** — RED / GREEN / REFACTOR cycle
- **Adversarial self-review** — "What if this runs twice concurrently?"
- **Lightweight mode** — auto-scales down for simple, low-risk changes

```
/wise implement user authentication with JWT
```

| Phase | What happens |
|-------|-------------|
| 1. **Understanding & Planning** | Reads project docs, assesses complexity, creates a plan |
| 2. **Codebase Exploration** | Maps existing patterns, verifies APIs exist, identifies impact zone |
| 3. **TDD** | Writes failing tests first, then minimal implementation, then refactors |
| 4. **Implementation** | Builds following existing patterns — constants, logging, error handling |
| 5. **Test Verification** | Runs the appropriate test suite, fixes regressions |
| 6. **Documentation** | Updates docs and GitHub issues |
| 7. **Pre-Commit Review** | Adversarial self-review checklist |
| 8. **PR Readiness** | Self-reviews the diff, opens a clean PR |

Simple changes (single file, < 50 lines, no interface changes) automatically skip the full ceremony — only phases 1, 4, and 7 run.

### Skill files

| File | Purpose |
|------|---------|
| `SKILL.md` | Core skill definition — phases, principles, and workflow |
| `CHECKLISTS.md` | Quick-reference checklists for each phase |
| `PATTERNS.md` | Concrete code examples for concurrency, testing, and implementation patterns |

## wise-cont — Continuous Architect Mode

Activate once, and **every subsequent message** in the session is handled with architect-mode standards — no need to type `/wise` each time.

```
/wise-cont
```

The agent automatically assesses each request and applies the appropriate level:

| Request type | Mode applied |
|-------------|--------------|
| Question / discussion (no code changes) | Q&A — architect thinking principles only |
| Single file, < 50 lines, low risk | Lightweight — phases 1, 4, 7 |
| Multi-file, clear scope | Full — phases 1–8 |
| Complex (4+ files, schema changes, etc.) | Full + GitHub issue required |

Deactivate with `/wise-cont-off` or "back to normal mode".

## cclog — Session Logger (Hook)

Automatically records all Claude Code tool usage to `.claude/log/` as Markdown files. Runs as a hook — **zero session token consumption**.

### How it works

- **PostToolUse hook** — logs every tool call with timestamps, input parameters, and execution results
- **Stop hook** — adds turn separators between Claude responses
- **Session detection** — groups entries by `session_id`, one file per session

### What gets recorded

| Tool | Recorded content |
|------|-----------------|
| **Bash** | Command, description, execution result (in `<details>` collapse) |
| **Edit** | File path, diff (`- old` / `+ new`) |
| **Grep** | Pattern, path, glob filter, match results |
| **Glob** | Pattern, path, matched files |
| **Read** | File path |
| **Write** | File path |
| **Agent** | Type, description, prompt |
| **Skill** | Skill name, arguments |
| **Others** | Tool name, input JSON, result |

### Log format

Logs are saved as `.claude/log/YYYY-MM-DD_HHMMSS.md`:

````markdown
# Claude Code Session Log
**Date:** 2026-03-20
**Start:** 14:30:22
**Project:** my-project

---

### [14:30] `Bash` — Run unit tests
```bash
npm test
```
<details><summary>result</summary>

```
PASS src/app.test.ts
  ✓ renders correctly (12ms)
Tests: 1 passed
```
</details>

### [14:31] `Edit` — `src/app.ts`
```diff
- const x = 1
+ const x = 2
```

### [14:32] `Grep` — `handleError` in `src/` (`*.ts`)
```
src/app.ts:42:  handleError(err)
src/utils.ts:10:export function handleError(e: Error) {
```

---
> Turn ended at 14:32:45
````

## sync_to_obsidian — Obsidian Vault Sync (Hook)

Converts Claude Code session transcripts (JSONL) into Markdown and saves them to your Obsidian vault.

> **You must update `VAULT_DIR`** — the default path is `/Documents/ObsidianVault/syc-ob-data`. Change `VAULT_DIR` in `.claude/hooks/sync_to_obsidian.py` to point to your own Obsidian vault.

```python
# .claude/hooks/sync_to_obsidian.py — line 6
VAULT_DIR = Path("/your/obsidian/vault/path")
```

### Managing logs

```bash
# List sessions
ls -lt .claude/log/*.md

# View a session
cat .claude/log/2026-03-20_143022.md

# Delete a session
rm .claude/log/2026-03-20_143022.md

# Delete all logs
rm -rf .claude/log/*
```

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- `python3` (for cclog hook JSON parsing and installer config merge)
- `curl` or `wget` (for the installer)

## Uninstall

```bash
# All components
rm -rf .claude/skills/terse-mode .claude/skills/swarm .claude/skills/wise .claude/skills/wise-cont
rm -f .claude/hooks/cclog-hook.sh .claude/hooks/sync_to_obsidian.py

# Individual
rm -rf .claude/skills/terse-mode
rm -rf .claude/skills/swarm
rm -rf .claude/skills/wise
rm -rf .claude/skills/wise-cont
rm -f .claude/hooks/cclog-hook.sh
rm -f .claude/hooks/sync_to_obsidian.py
```

After removing cclog, also remove the `hooks` section from `.claude/settings.local.json`.

## License

MIT
