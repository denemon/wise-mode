# wise-mode

A collection of [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills and hooks for disciplined development: **caveman** for brevity, **swarm** for parallel delegation plans, **wise** for architect-mode quality gates, **wise-cont** for persistent architect mode, and **cclog** for automatic session logging.

## Components

| Name | Type | Description |
|------|------|-------------|
| **caveman** | Skill (`/caveman`) | Brevity mode: fewer words, same technical substance, with lite/full/ultra intensity levels |
| **swarm** | Skill (`/swarm`) | Low-token subagent orchestration: creates scoped agent briefs plus runnable swarm files |
| **wise** | Skill (`/wise`) | Architect mode for a single task: investigation, design, or implementation with planning, verification, and adversarial review |
| **wise-cont** | Skill (`/wise-cont`) | Continuous architect mode: activate once and keep wise standards active for the rest of the session |
| **cclog** | Hook | Auto-records all Claude Code sessions to `.claude/log/` with zero token consumption |

## Quick install

Run this in your **project root** (where `.git/` lives):

```bash
curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/install.sh | bash
```

This installs skills into `.claude/skills/`, the cclog hook into `.claude/hooks/`, and merges hook configuration into `.claude/settings.local.json`.

### Manual install

```bash
# caveman
mkdir -p .claude/skills/caveman
cd .claude/skills/caveman
curl -fsSLO https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/caveman/SKILL.md

# swarm
mkdir -p .claude/skills/swarm
cd .claude/skills/swarm
curl -fsSLO https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/swarm/SKILL.md

# wise
mkdir -p .claude/skills/wise
cd .claude/skills/wise
curl -fsSLO https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/wise/SKILL.md
curl -fsSLO https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/wise/CHECKLISTS.md
curl -fsSLO https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/wise/PATTERNS.md

# wise-cont
mkdir -p .claude/skills/wise-cont
cd .claude/skills/wise-cont
curl -fsSLO https://raw.githubusercontent.com/den-emon/wise-mode/main/skills/wise-cont/SKILL.md

# cclog (hook)
mkdir -p .claude/hooks
cd .claude/hooks
curl -fsSLO https://raw.githubusercontent.com/den-emon/wise-mode/main/hooks/cclog-hook.sh
chmod +x cclog-hook.sh
```

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

## caveman - Brevity Mode

When you type `/caveman`, the agent switches into a brevity-first response style:

- Same technical substance: removes filler, keeps exact terms, commands, and errors
- 3 intensity levels: `lite`, `full`, and `ultra`
- Auto-clarity: temporarily returns to normal wording for destructive actions and safety warnings
- Language-preserving: stays in the user's language unless asked to translate

```text
/caveman
/caveman lite
/caveman ultra
```

Use it when you want faster, tighter answers without losing the actual fix or reasoning.

## swarm - Parallel Delegation Mode

When you type `/swarm`, the agent builds a compact parallel-work plan for tasks you explicitly want delegated:

- Low-token discovery: reads only the files needed to set agent boundaries
- Conflict-safe ownership: each agent gets an explicit write scope
- Runnable output: generates human-readable `.swarm/plan.md` and executable `.swarm/run.sh`
- Smallest useful swarm: avoids over-fragmenting simple work

```text
/swarm build agents for this feature
/swarm break this task into parallel workers
```

Use it when you want subagents or parallel execution, not for ordinary single-agent coding.

## wise - Architect Mode

When you type `/wise` in Claude Code, the agent shifts into architect mode for a **single task**.

`skills/wise/SKILL.md` is the canonical source of truth for delivery modes, lightweight criteria, and tracking policy. This README and `/wise-cont` mirror it.

### Delivery modes

- `quick-answer`: handle lightweight repo navigation, symbol lookup, or short factual clarification with minimal verified reads
- `analysis-only`: investigate, gather evidence, and explain likely root cause without editing code
- `design-only`: compare options and produce a validation, migration, or rollout plan without editing code
- `apply` (default): implement and verify the change

### What wise optimizes for

- Think first, code second
- Reuse repository patterns instead of inventing local conventions
- Keep apply mode execution-friendly: read, edit, bash, and todo tools are pre-approved for the normal implementation flow
- Challenge the result adversarially before calling it done
- Auto-scale down for genuinely small, low-risk changes

```text
/wise implement user authentication with JWT
/wise investigate why job retries create duplicates
/wise design a safe rollout plan for this schema change
```

### Process selection

| Path | When used | Phases |
|------|-----------|--------|
| Quick-answer | Symbol lookup, repo navigation, short factual clarification | Minimal targeted verification, then direct answer |
| Analysis-only | Investigation, debugging discussion, root-cause analysis | 1 -> 2 -> 7 |
| Design-only | Design comparison, migration planning, rollout strategy | 1 -> 2 -> 3 (plan only) -> 7, plus 6 if docs/tracking should change |
| Apply (Lightweight) | Single file, small change, low risk | 1 (abbreviated) -> 4 -> 5 -> 7, plus 6 if docs/tracking changed |
| Apply (Full) | Multi-file or medium/high-risk implementation work | 1 -> 8, with phase 6 only when relevant |
| Apply (Full/Complex) | Schema, migration, auth, concurrency, or rollout-heavy work | 1 -> 8, plus issue/tracking updates only if the repo already uses them |

### Phase summary

| Phase | What happens |
|-------|--------------|
| 1. **Understanding & Planning** | Reads project docs, assesses complexity, chooses delivery mode, creates a plan |
| 2. **Codebase Exploration** | Maps existing patterns, verifies APIs exist, identifies impact zone |
| 3. **TDD / Validation Plan** | RED -> GREEN -> REFACTOR, or the equivalent validation plan for design work |
| 4. **Implementation** | Builds following existing patterns: constants, logging, validation, error handling |
| 5. **Test Verification** | Runs the appropriate test scope and fixes regressions |
| 6. **Documentation & Tracking** | Updates docs, examples, rollout notes, and tracking when relevant |
| 7. **Adversarial Review** | Hostile self-review against edge cases, retries, races, and hidden assumptions |
| 8. **Review Readiness** | Reviews the diff and leaves a clean handoff for humans or review bots |

### Skill files

| File | Purpose |
|------|---------|
| `SKILL.md` | Core skill definition: modes, phases, principles, and workflow |
| `CHECKLISTS.md` | Quick-reference checklists for planning, migration, security, and review |
| `PATTERNS.md` | Concrete patterns for concurrency, rollouts, migrations, testing, and implementation |

## wise-cont - Continuous Architect Mode

Activate once, and **every subsequent message** in the session is handled with wise standards. There is no need to type `/wise` each time.

```text
/wise-cont
```

`/wise-cont` is a thin wrapper around `/wise`.
On each new user message it re-runs `/wise` mode selection, including:

- `quick-answer` for lightweight repo navigation and factual lookups
- `analysis-only` and `design-only` for advisory work
- `apply` for implementation work, with lightweight vs full chosen by `/wise`

To reduce noise, mode badges are surfaced on activation, when the mode changes, or when apply work begins.

Deactivate with `/wise-cont-off` or "back to normal mode".

## cclog - Session Logger (Hook)

Automatically records Claude Code tool usage to `.claude/log/` as Markdown files. Runs as a hook, so it consumes **zero session tokens**.

### How it works

- `PostToolUse` hook: logs every tool call with timestamps, input parameters, and execution results
- `Stop` hook: adds turn separators between Claude responses
- Session detection: groups entries by `session_id`, one file per session

### What gets recorded

| Tool | Recorded content |
|------|------------------|
| **Bash** | Command, description, execution result |
| **Edit** | File path and diff |
| **Grep** | Pattern, path, glob filter, match results |
| **Glob** | Pattern, path, matched files |
| **Read** | File path |
| **Write** | File path |
| **Agent** | Type, description, prompt |
| **Skill** | Skill name and arguments |
| **Others** | Tool name, input JSON, result |

### Log format

Logs are saved as `.claude/log/YYYY-MM-DD_HHMMSS.md`.

````markdown
# Claude Code Session Log
**Date:** 2026-03-20
**Start:** 14:30:22
**Project:** my-project

---

### [14:30] `Bash` - Run unit tests
```bash
npm test
```
<details><summary>result</summary>

```
PASS src/app.test.ts
  - renders correctly (12ms)
Tests: 1 passed
```
</details>

### [14:31] `Edit` - `src/app.ts`
```diff
- const x = 1
+ const x = 2
```

### [14:32] `Grep` - `handleError` in `src/` (`*.ts`)
```
src/app.ts:42:  handleError(err)
src/utils.ts:10:export function handleError(e: Error) {
```

---
> Turn ended at 14:32:45
````

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
rm -rf .claude/skills/wise .claude/skills/wise-cont .claude/hooks/cclog-hook.sh

# Individual
rm -rf .claude/skills/wise
rm -rf .claude/skills/wise-cont
rm .claude/hooks/cclog-hook.sh
```

After removing cclog, also remove the `hooks` section from `.claude/settings.local.json`.

## License

MIT
