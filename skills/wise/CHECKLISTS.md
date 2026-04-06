# Quick Reference Checklists

Use this file as a compact companion to `SKILL.md`.

The main skill defines the workflow.
This file is for fast verification when you are:
- planning a change,
- reviewing implementation,
- checking test quality,
- preparing a final handoff.

---

## 1) Intake Checklist

Before touching code, confirm:

- [ ] I understand the requested outcome in concrete terms
- [ ] I can state what will change
- [ ] I can state what will not change
- [ ] I identified acceptance criteria
- [ ] I selected the correct delivery mode: `quick-answer`, `analysis-only`, `design-only`, or `apply`
- [ ] If this is `apply`, I classified it as lightweight or full path
- [ ] I created a todo list with concrete steps
- [ ] I checked repository guidance (`CLAUDE.md`, `CONTRIBUTING.md`, `README.md`, PR template, docs)
- [ ] I know whether GitHub issue or PR tracking is actually in use here
- [ ] If GitHub is unavailable, I have a non-GitHub tracking fallback (todo list + final summary)

If any of these are false, you are not ready to implement.

---

## 2) Exploration Checklist

Before proposing a design, confirm:

- [ ] I verified relevant files, functions, methods, classes, constants, and flags actually exist
- [ ] I identified local code patterns for logging, errors, validation, config, and tests
- [ ] I checked migration or rollout conventions if data shape or deployment order matters
- [ ] I checked auth, permission, and validation boundaries if the change crosses trust boundaries
- [ ] I mapped callers and dependents of the code I may change
- [ ] I understand data touched by the change
- [ ] I identified external side effects
- [ ] I checked whether shared mutable state is involved
- [ ] I identified invariants that must remain true
- [ ] I chose the smallest safe design that matches repository conventions

Warning signs:
- You are relying on memory instead of search
- You are inventing abstractions before understanding current ones
- You are planning unrelated cleanup "while you are here"

---

## 3) Read-Only Path Checklist

For `quick-answer`, `analysis-only`, or `design-only` work, confirm:

- [ ] I did not silently turn a factual lookup or investigation request into code edits
- [ ] I gathered direct evidence from the repository before concluding
- [ ] If this is `quick-answer`, I kept the answer short, read-only, and grounded in a few targeted checks
- [ ] I can explain why I am recommending this design or root cause
- [ ] I listed the risks, assumptions, and next step clearly
- [ ] If this is `design-only`, I produced a validation plan rather than pretending design alone is proof

---

## 4) Lightweight Apply Path Checklist

Use the lightweight path only if all are true:

- [ ] Single file or very tightly localized
- [ ] Small change
- [ ] No public API or interface change
- [ ] No schema or migration implications
- [ ] No concurrency or shared-state concern
- [ ] Low regression risk
- [ ] Test impact is obvious

For lightweight tasks, confirm:

- [ ] I still did a short understanding pass
- [ ] I still verified symbols and patterns
- [ ] I still ran focused validation or tests
- [ ] I still performed adversarial review before finishing
- [ ] I only skipped docs or tracking if nothing user-visible changed

If unsure, do not use the lightweight path.

---

## 5) TDD / Test Strategy Checklist

For non-trivial changes:

- [ ] RED: I wrote or updated a test before implementation
- [ ] The test failed for the correct reason
- [ ] GREEN: I implemented the minimum needed behavior
- [ ] The test now passes
- [ ] REFACTOR: I only cleaned structure while tests stayed green

Quality of tests:

- [ ] Assertions check specific values, not vague truthiness
- [ ] Boundary cases are covered where relevant
- [ ] Error paths are covered where relevant
- [ ] Important side effects are asserted
- [ ] Repeated execution or idempotency is checked where relevant
- [ ] Tests would catch subtle operator or condition regressions
- [ ] Tests are isolated from unrelated external dependencies where possible

Ask:
- Would this test catch `>` changing to `>=`?
- Would it catch a duplicate side effect?
- Would it catch missing persistence?
- Would it catch a partial update?

---

## 6) Legacy / Weakly-Tested Area Checklist

If the area has weak or no tests:

- [ ] I wrote characterization tests for current behavior first
- [ ] I ran them on the unmodified code
- [ ] I captured representative inputs, not just one happy path
- [ ] I only changed behavior intentionally
- [ ] If characterization tests broke, I verified whether that break was intended

Characterization tests are not the end state.
They are the safety net that lets you change code responsibly.

---

## 7) Implementation Checklist

While coding, confirm:

- [ ] I am using existing constants, enums, and config where appropriate
- [ ] I am following local naming and module boundaries
- [ ] Input validation happens at the correct boundary
- [ ] Error handling is coherent with the repository style
- [ ] Logging or metrics follow existing patterns
- [ ] I did not introduce unnecessary scope creep
- [ ] I did not hard-code values that should be centralized

If shared state, async work, or transactions are involved:

- [ ] I identified all actors that can mutate the state
- [ ] I checked race and repeated-execution scenarios
- [ ] I defined invariants that must hold before and after execution
- [ ] I considered locking, serialization, or atomicity needs
- [ ] I considered rollback behavior
- [ ] I considered which side effects must persist even on failure

---

## 8) Migration / Irreversible Change Checklist

Use this whenever data shape, deployment order, or rollback complexity matters.

- [ ] I identified whether the change needs expand/contract, backfill, dual-write, or compatibility shims
- [ ] I know whether old and new readers or writers can coexist during rollout
- [ ] I have a dry-run, no-op, or preview path where feasible
- [ ] I separated code rollback from data rollback in the plan
- [ ] I know which steps are irreversible and how they will be communicated
- [ ] I have a reconciliation plan, metric, or audit query for silent drift
- [ ] I considered feature flags or staged rollout guards where useful
- [ ] I checked deployment ordering across services, workers, and jobs

---

## 9) Security Checklist

Use this whenever the change crosses a trust boundary or touches sensitive data.

- [ ] Authentication behavior is explicit and still correct
- [ ] Authorization checks happen at the trusted boundary, not only in the UI
- [ ] Inputs are validated and canonicalized before use
- [ ] Query or command construction avoids injection risks
- [ ] Secrets, tokens, and credentials are not hard-coded or logged
- [ ] Logs, errors, and tests redact sensitive data where needed
- [ ] File paths, URLs, or remote fetches resist traversal or SSRF where relevant
- [ ] Replay, idempotency, and rate-limit concerns are handled for externally triggered work

---

## 10) Design Reset Checklist

If implementation reveals the design is wrong:

- [ ] Stop patching around the flawed design
- [ ] Update the todo list to reflect the new understanding
- [ ] Revisit exploration and impact analysis
- [ ] Revise tests if the target behavior changed
- [ ] Continue only after the new design is explicit

Do not keep layering fixes onto a design you no longer trust.

---

## 11) Verification Checklist

Before declaring success:

- [ ] I ran the smallest credible test scope
- [ ] All relevant tests passed
- [ ] I did not ignore failing relevant tests
- [ ] I checked nearby behavior that could regress
- [ ] I verified docs, config, migrations, or examples if they were affected
- [ ] I reviewed the diff, not just the final files

Suggested test scope:
- Tiny isolated change: related tests
- Feature-local change: feature or module suite
- Cross-cutting change: all affected modules
- Schema, auth, migration, rollout, or concurrency change: broaden validation accordingly

---

## 12) Docs and Tracking Checklist

If the change affected behavior, usage, config, conventions, or rollout steps:

- [ ] I updated docs accordingly
- [ ] I updated examples if needed
- [ ] I removed dead code instead of commenting it out
- [ ] I recorded migration or rollout instructions if operators need them

Tracking:

- [ ] If GitHub issue or PR workflow exists, I updated it
- [ ] If not, the final summary records the same information
- [ ] Open follow-up work is explicit, not implied

---

## 13) Final Handoff Checklist

My final output includes:

- [ ] The selected delivery mode
- [ ] What changed or what I found
- [ ] Why this approach
- [ ] Files changed or evidence checked
- [ ] Tests added, updated, planned, or run
- [ ] Risks checked
- [ ] Docs or tracking updated
- [ ] Open questions or next steps

A good handoff should let a reviewer answer:
"What changed, why, how was it validated, and what remains?"

---

## Quick Commands (Optional, Repo-Dependent)

Use these only if they fit the repository and environment.

```bash
# verify symbols / usages
grep -rn "symbol_name" .

# review changed code
git diff
git diff --staged

# compare against main branch
git diff main...HEAD

# run focused tests (example placeholders)
npm test -- path/to/test
pytest path/to/test_file.py
go test ./path/to/package
cargo test package_name
```

---

## Optional GitHub Commands

Only use these if the repository actually uses GitHub issues and `gh` is available.

```bash
# search issues
gh issue list --search "keyword"

# create issue
gh issue create --title "Title" --body "Body"

# update issue body
gh issue edit <issue-number> --body "Updated body"

# add a progress comment
gh issue comment <issue-number> --body "Progress update"

# add labels
gh issue edit <issue-number> --add-label "in-progress"

# close issue
gh issue close <issue-number> --comment "Completed"
```
