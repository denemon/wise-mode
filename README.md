# wise-mode

A collection of [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills and hooks for disciplined development — **terse-mode** for brevity, **swarm** for parallel delegation plans, **wise** for architect-mode quality gates, **wise-cont** for persistent architect mode, **dev-with-review** for implementation with independent AI review, **attack-on-hacker** for adversarial source-code security review, and **cclog** for automatic session logging.

## Components

| Name | Type | Description |
|------|------|-------------|
| **terse-mode** | Skill (`/terse-mode`) | Brevity mode — fewer words, same technical substance, with lite/full/ultra intensity levels |
| **swarm** | Skill (`/swarm`) | Low-token subagent orchestration — creates scoped agent briefs plus runnable swarm files |
| **wise** | Skill (`/wise`) | Architect mode — systematic planning, TDD, adversarial self-review, and quality gates (single task) |
| **wise-cont** | Skill (`/wise-cont`) | Continuous architect mode — activate once, applies to all subsequent messages in the session |
| **dev-with-review** | Skill (`/dev-with-review`) | Implement + continuous self-review + independent AI review via separate Claude instance |
| **attack-on-hacker** | Skill (`/attack-on-hacker`) | Adversarial source-code security review — threat model, taint analysis (Source → Sink → Sanitizer), severity rubric, CWE/CVSS findings, Diff Mode for PRs |
| **cclog** | Hook | Auto-records all Claude Code sessions to `.claude/log/` — implemented by `sync_to_obsidian.py` |
| **sync_to_obsidian** | Hook | Optionally syncs session transcripts to Obsidian vault as Markdown notes |

## Quick install

Run this in your **project root** (where `.git/` lives):

```bash
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/install.sh | bash
```

This installs skills into `.claude/skills/`, the unified hook into `.claude/hooks/sync_to_obsidian.py`, and merges hook configuration into `.claude/settings.local.json`.

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

# dev-with-review
mkdir -p .claude/skills/dev-with-review/scripts .claude/skills/dev-with-review/references
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/dev-with-review/SKILL.md \
  -o .claude/skills/dev-with-review/SKILL.md
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/dev-with-review/scripts/ai_review.sh \
  -o .claude/skills/dev-with-review/scripts/ai_review.sh
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/dev-with-review/references/reviewer_prompt.md \
  -o .claude/skills/dev-with-review/references/reviewer_prompt.md
chmod +x .claude/skills/dev-with-review/scripts/ai_review.sh

# attack-on-hacker
mkdir -p .claude/skills/attack-on-hacker
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/attack-on-hacker/SKILL.md \
  -o .claude/skills/attack-on-hacker/SKILL.md

# hooks
mkdir -p .claude/hooks
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/hooks/sync_to_obsidian.py \
  -o .claude/hooks/sync_to_obsidian.py

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
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/sync_to_obsidian.py\" PostToolUse",
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
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/sync_to_obsidian.py\" Stop",
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

## dev-with-review — Implement + Independent Review

When you type `/dev-with-review`, the agent implements your task while continuously reviewing its own diffs. At the final gate, it invokes a **separate Claude instance** (`claude -p`) for an independent code review — free from development-context bias.

```
/dev-with-review add input validation to the signup form
```

| Phase | What happens |
|-------|-------------|
| 1. **Understand** | Restate task, identify files, risks, and validation strategy |
| 2. **Implement** | Small batches of changes |
| 3. **Self-review loop** | After each batch: `git diff`, adversarial review, fix issues |
| 4. **Validation** | Run lint, tests, typecheck (auto-detected per language) |
| 5. **Independent review** | Invoke `claude -p` with reviewer prompt — JSON score + findings |
| 6. **Final report** | Structured summary with score, findings, and remaining risks |

The independent reviewer scores the diff 0–100 and returns findings by severity (critical/high/medium/low/info). Critical and high findings must be fixed before completion.

### Skill files

| File | Purpose |
|------|---------|
| `SKILL.md` | Core skill definition — phases, rules, and behavioral constraints |
| `scripts/ai_review.sh` | Standalone script to run `claude -p` review from the command line |
| `references/reviewer_prompt.md` | System prompt for the independent reviewer instance |

### When to use dev-with-review vs wise

| Situation | Recommended |
|-----------|-------------|
| Emphasis on **planning, TDD, and architecture** — new features, multi-file refactors, schema changes | `/wise` or `/wise-cont` |
| Emphasis on **implementation quality and review** — bug fixes, feature work where you want a second opinion | `/dev-with-review` |
| Single task, full ceremony with GitHub issue tracking | `/wise` |
| Session-wide architect standards | `/wise-cont` |
| Need an independent, bias-free code review as a final gate | `/dev-with-review` |
| Simple low-risk change (single file, < 50 lines) | Either works — wise auto-scales to lightweight mode |

**Key difference**: wise focuses on *how you think and plan* (architect-first, TDD, 8 phases). dev-with-review focuses on *how you verify* (continuous diff review + independent AI reviewer). They complement each other — wise ensures you build the right thing, dev-with-review ensures you built it correctly.

## attack-on-hacker — Adversarial Security Review

When you type `/attack-on-hacker`, the agent reviews authorized source code from a black-hat mindset and turns the result into defensive findings: credible attack paths, evidence, impact, fixes, and verification steps. No weaponized payloads — output is always remediation-focused.

```
/attack-on-hacker review the auth flow in src/auth/
/attack-on-hacker audit this PR for security regressions
```

| Phase | What happens |
|-------|-------------|
| **Diff Mode** (optional) | If reviewing a PR or branch diff, scopes every phase to changed code and hunts silently-weakened controls (auth gates removed, `verify=False`, loosened CORS, etc.) |
| 1. **Scope + Threat Model** | Entry points, trust boundaries, attacker profile, mitigations to factor out |
| 1.5. **Quick-Wins Sweep** | High-signal pass: secrets in code & git history, CI pwn-request patterns, container hygiene, IaC defaults, dependency audit |
| 2. **Attacker Map** | Source → Sink → Sanitizer taint analysis required for every candidate |
| 3. **Hunt High-Risk Classes** | OWASP-style categories plus language/framework-specific sinks (Node, Django, Spring, Go, Rust, SQL) |
| 4. **Prove Plausibility** | Pre-Report Sanity Gate — reachability, sanitizer absence, realistic preconditions, evidence taxonomy |
| 5. **Report Findings** | Top-3 Fix-First, Severity Rubric, CWE + CVSS per finding |

### Key features

- **Threat model first** — explicit attacker profile (`anon-external`, `authenticated-low-priv`, `cross-tenant`, `admin-or-insider`, `compromised-dependency`); severity is grounded in it
- **Source → Sink → Sanitizer** — every finding must name all three; missing one means it's a suspicion, not a bug
- **Evidence taxonomy** — `confirmed-by-poc` (executed local PoC) / `confirmed-by-read` (full data-flow with `file:line`) / `inferred-pattern` (auto-downgraded severity)
- **False-positive discipline** — reachability, upstream sanitizer, realistic preconditions are mandatory before reporting
- **CWE + CVSS per finding** — for triage-tool integration; the Severity Rubric wins when CVSS disagrees
- **Diff Mode** — `[regression]` / `[new-surface]` / `[pre-existing]` classification for PR reviews
- **JSON output** — optional `--format=json` for tooling consumption

### When to use

| Situation | Recommended |
|-----------|-------------|
| Full security audit of a codebase or module | `/attack-on-hacker` |
| Security check on a PR / branch diff | `/attack-on-hacker review this PR` (auto-enters Diff Mode) |
| Auth, authz, crypto, deserialization, or parser changes | `/attack-on-hacker` |
| Dependency or IaC change | `/attack-on-hacker` (Quick-Wins Sweep covers both) |
| Non-security implementation work | `/wise` or `/dev-with-review` |

## cclog — Session Logger (Hook)

`sync_to_obsidian.py` now owns the local session log as well. It always records Claude Code tool usage to `.claude/log/` as Markdown files, and it optionally syncs the same session to Obsidian when `VAULT_DIR` is configured.

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
**Session:** abcdef1234567890

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

## sync_to_obsidian — Obsidian Vault Sync (Optional)

The same hook can also convert Claude Code session transcripts (JSONL) into Markdown and save them to your Obsidian vault.

> **Obsidian sync is disabled by default.** To enable it, edit `.claude/hooks/sync_to_obsidian.py` and set `VAULT_DIR` to your Obsidian vault path. If `VAULT_DIR` is empty or the path doesn't exist, only the local `.claude/log/` output runs.

```python
# .claude/hooks/sync_to_obsidian.py
VAULT_DIR = "/path/to/your/ObsidianVault/folder"
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
- `python3` (for the unified hook and installer config merge)
- `curl` or `wget` (for the installer)

## Uninstall

```bash
# All components
rm -rf .claude/skills/terse-mode .claude/skills/swarm .claude/skills/wise .claude/skills/wise-cont .claude/skills/dev-with-review .claude/skills/attack-on-hacker
rm -f .claude/hooks/sync_to_obsidian.py
# Older installs may also still have this deleted legacy file:
rm -f .claude/hooks/cclog-hook.sh

# Individual
rm -rf .claude/skills/terse-mode
rm -rf .claude/skills/swarm
rm -rf .claude/skills/wise
rm -rf .claude/skills/wise-cont
rm -rf .claude/skills/dev-with-review
rm -rf .claude/skills/attack-on-hacker
rm -f .claude/hooks/sync_to_obsidian.py
# Older installs only:
rm -f .claude/hooks/cclog-hook.sh
```

After removing the hook, also remove the `hooks` section from `.claude/settings.local.json`.

## License

MIT
