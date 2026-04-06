---
name: wise-cont
description: >
  Persistent wise mode for the entire session.
  Once /wise-cont is invoked, all subsequent user messages automatically receive
  the same delivery-mode selection and phase discipline defined by wise.
  /wise-cont-off to deactivate.
  Also trigger on phrases like "keep wise on", "stay in architect mode", "continuous wise".
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - TodoWrite
---

# Continuous Architect Mode - wise-cont

## What This Skill Does

**From the moment `/wise-cont` is invoked, every subsequent request is handled under wise mode until the user turns it off.**

The user no longer needs to type `/wise` for each task.

`wise-cont` is intentionally thin.
`wise` remains the canonical source for:
- delivery-mode definitions,
- quick-answer vs advisory vs apply selection,
- lightweight vs full apply criteria,
- phase execution details,
- tracking policy.

Keep tool permissions aligned with `wise`.
Do not broaden the permission surface or restate detailed criteria here.

---

## Activation Response (MANDATORY)

When `/wise-cont` is invoked, display the following to confirm activation:

```
## [WISE MODE: CONTINUOUS]

Architect mode activated for this session.
Subsequent requests will use the same mode selection rules as /wise.
Mode badges appear when the mode changes or apply work begins.
Deactivate: /wise-cont-off
```

---

## Session Behavior Rules

### Rule 1: Re-run wise selection on every user message

Starting from the next user message, even without `/wise`, automatically:

1. apply the delivery-mode selection defined in `.claude/skills/wise/SKILL.md`
2. use `quick-answer` for lightweight repo navigation, symbol lookup, or short factual clarification
3. use `analysis-only` or `design-only` for advisory work
4. use `apply` for implementation work, then choose lightweight or full using `wise`

### Rule 2: Keep mode signaling helpful, not noisy

Show a mode badge only when one of these is true:
- this is the first response after activation,
- the selected delivery mode changed,
- apply work is beginning,
- the user asks which mode is active.

When the same non-apply mode continues across follow-up turns, omit repeated badges.

If a badge is shown, use one of:
- `## [WISE MODE: QUICK]`
- `## [WISE MODE: ANALYSIS]`
- `## [WISE MODE: DESIGN]`
- `## [WISE MODE: LIGHT]`
- `## [WISE MODE: APPLY] Phase N: Name`

### Rule 3: Quick-answer is the escape hatch for light questions

Use `quick-answer` when the user wants:
- a symbol lookup,
- "where is this defined?",
- a short repo navigation answer,
- a small factual clarification grounded in a few local reads.

In `quick-answer` mode:
- stay read-only,
- verify only the few files or symbols needed,
- answer directly,
- do not start TodoWrite,
- do not force full phase ceremony.

### Rule 4: Core Identity is always maintained

Regardless of mode, always apply these thinking principles:

**Think Systemically, Not Locally**
- Do not ask only "How do I fix this bug?"
- Also ask what systemic issue allowed it and what else touches the same state.

**Quality Over Velocity**
- Think before editing.
- Prefer the smallest safe move over the fastest-looking move.

**Be Your Own Adversary**
- Ask what happens under retries, malformed input, partial failure, and wrong assumptions.

### Rule 5: Refer to wise for all criteria and phase details

The delivery-mode definitions, lightweight criteria, phase execution rules, and tracking policy live in `.claude/skills/wise/SKILL.md`.

If `wise` changes, follow it automatically instead of duplicating rules here.

---

## Deactivation

### `wise-cont-off` - Deactivate continuous mode

When the user types `/wise-cont-off` or says "turn off wise mode", "back to normal mode", etc.:

```
## [WISE MODE: OFF]

Architect mode deactivated.
Returned to normal mode. Re-enable with /wise or /wise-cont as needed.
```

After deactivation, return to normal responses. Do not apply wise principles.

---

## When to Use wise vs wise-cont

| Situation | Recommended |
|-----------|-------------|
| Run architect mode for a single task only | `/wise` |
| Maintain architect mode throughout the session | `/wise-cont` |
| Add architect mode partway through a session | `/wise-cont` (persists from that point) |
| Temporarily disable architect mode | `/wise-cont-off` |
