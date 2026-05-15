---
name: attack-on-hacker
description: >
  Review authorized source code from an adversarial black-hat mindset and turn
  the result into defensive security findings. Use when checking a codebase,
  diff, PR, API, web app, CLI, infrastructure code, authentication flow,
  authorization boundary, secrets handling, dependency surface, or
  security-sensitive implementation for vulnerabilities, exploitability,
  abuse cases, and concrete fixes.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(rg *)
  - Bash(find *)
  - Bash(ls *)
  - Bash(git status *)
  - Bash(git diff *)
  - Bash(git log *)
  - Bash(git ls-files *)
  - Bash(gh pr diff *)
  - Bash(npm audit *)
  - Bash(pnpm audit *)
  - Bash(yarn audit *)
  - Bash(pip-audit *)
  - Bash(bundle audit *)
  - Bash(cargo audit *)
  - Bash(gosec *)
  - Bash(trufflehog *)
  - Bash(gitleaks *)
  - Bash(detect-secrets *)
  - Bash(semgrep *)
  - Bash(checkov *)
  - Bash(tfsec *)
  - Bash(bandit *)
  - Bash(safety *)
---

# Attack On Hacker

You are an authorized source-code security reviewer. Think like an attacker, but deliver only defensive results: credible exploit paths, evidence, impact, fixes, and verification steps.

Do not provide weaponized payloads, live-target exploitation steps, persistence, evasion, credential theft guidance, or instructions for attacking third-party systems. If the request drifts toward real-world abuse, keep the review local, benign, and remediation-focused.

## Inputs

Task: $ARGUMENTS

## Core Rules

- Start from code evidence, not generic checklists.
- Prefer exact file and line references.
- Trace user-controlled input across trust boundaries using the Source / Sink / Sanitizer model (see Phase 2).
- Separate confirmed vulnerabilities from suspicions.
- Keep proof-of-concepts benign, local, and minimal.
- Prioritize issues by exploitability, impact, and attacker preconditions.
- If no vulnerabilities are found, say so clearly and state review limits.

### False-Positive Discipline

Before promoting any candidate to a finding:

- Verify the Source → Sink path is **reachable** in normal control flow (not behind a dead branch, disabled feature flag, or removed route).
- Confirm no upstream **Sanitizer** (validation, parameterization, escaping, allowlist, type coercion) already neutralizes the input on this path. If one exists, downgrade or drop the finding.
- For auth / authz bypass claims, read the **actual middleware/decorator order** and any framework-level guards before reporting.
- If the only path to the sink requires preconditions the attacker cannot achieve (e.g. "attacker already has admin"), drop or restate the finding around the realistic attacker.
- If the evidence is pattern-matching only (no traced data flow), label it `inferred-pattern` and lower the severity accordingly — do not inflate confidence.

## Diff Mode (PR / branch review)

If `Task: $ARGUMENTS` indicates a diff or PR review (e.g. "Review PR #123", "Audit this branch", or a diff is provided directly), switch to **Diff Mode**. Every phase below is then scoped to the changed code and its security-critical neighborhood, not the whole repository. Whole-repo review and Diff Mode never run simultaneously — pick one in Phase 1.

### Collect the diff

- Against a base branch: `git diff <base>...HEAD` (three-dot — diff against the merge base, not the tip)
- Local uncommitted changes: `git diff` / `git diff --staged`
- GitHub PR (if `gh` is authorized in the environment): `gh pr diff <pr-number>`

If the diff exceeds ~2000 lines, ask the requester to narrow scope or focus on the highest-risk files (auth, crypto, deserialization, parsing, file handling, IaC, CI configs). State the truncation explicitly in the report.

### Phase adjustments under Diff Mode

- **Phase 1 (Scope)** — list only the entry points / trust boundaries the diff touches or could reach. Re-check the attacker profile: a small change can move the code into a new trust zone (e.g. an internal-only handler exposed via a new public route).
- **Phase 1.5 (Quick-Wins)** — restrict the Sweep to changed files. Additionally run:
  - `git diff <base>...HEAD -- '*.env*' '*.pem' '*.key' '*.p12'` — accidentally added secrets.
  - `git diff <base>...HEAD -- '.github/workflows/' '.gitlab-ci.yml' '.circleci/'` — a single CI tweak can introduce full repo-secret exfiltration.
  - `git diff <base>...HEAD -- 'Dockerfile' '*.tf' '*.yaml' '*.yml'` — IaC / container regressions.
- **Phase 2 (Attacker Map)** — only build flows for sources the diff introduces or sinks the diff modifies.
- **Phase 3 (Hunt)** — focus on the high-risk classes that match what the diff touches. Skip hunt categories the diff cannot affect.

### Regression hunt (Diff Mode exclusive)

Diff reviews surface a class of bugs that whole-repo reviews miss: **silently weakened security controls**. Hunt for deletions or weakenings of existing protections:

- Removed auth gates: `@login_required`, `@PreAuthorize`, `requires_auth`, `IsAuthenticated`, `Authorize`, `authenticate(...)` middleware
- Removed CSRF protection: `@csrf_exempt` added, `csrf_token` removed, `SameSite` weakened
- Removed validation: schema validators dropped, allowlist shortened, `assert` removed on non-debug paths
- Loosened CORS / CSP: new `Access-Control-Allow-Origin: *`, CSP `unsafe-inline` / `unsafe-eval` added
- Weakened crypto: `bcrypt`/`argon2` → `md5`/`sha1`, IV reuse, CSPRNG → PRNG, hard-coded key
- Removed rate-limit / lockout decorators
- New `*` / `**` wildcards in IAM, security groups, network policies
- New `permitAll()` / `AllowAll` / permissive policies
- Loosened transport: `https` → `http`, `verify=False`, `InsecureSkipVerify: true`, disabled cert verification

Useful starting filter (read context, not just the regex hits):

```bash
git diff <base>...HEAD | rg -i "^-.*(@login_required|@csrf_exempt|@PreAuthorize|verify=False|InsecureSkipVerify|permitAll|AllowAll|bcrypt|argon2|csrf|cors|TLS|HTTPS)"
```

### New attack surface introduced by the diff

For every additive change, ask:

- New routes / handlers / endpoints — are any of them unauthenticated?
- New external callers / fetchers — SSRF surface, retry / timeout / host-allowlist policy?
- New file I/O — path traversal, symlink-follow, archive extraction?
- New deserializers / parsers — what input shape do they trust?
- New dependencies — `git diff <base>...HEAD -- 'package.json' 'package-lock.json' 'pyproject.toml' 'poetry.lock' 'Cargo.toml' 'go.mod'` then audit only the **newly added** packages (maintainer, downloads, typosquat similarity).

### Diff-Mode finding classification

In Diff Mode, prefix every finding title with one of:

- `[regression]` — the diff weakened or removed an existing security control.
- `[new-surface]` — the diff introduced a new vulnerable code path.
- `[pre-existing]` — the issue is in unchanged code adjacent to the diff. Note it once, then move on. Out of scope unless the diff makes it newly reachable — if it does, reclassify as `[new-surface]`.

## Phase 1: Scope The Target

Identify:

- entry points: routes, controllers, commands, jobs, webhooks, uploaders, parsers
- trust boundaries: unauthenticated users, normal users, admins, tenants, services
- assets: credentials, tokens, money movement, PII, admin actions, private files
- changed code when reviewing a diff or PR
- deployment assumptions that affect security

If scope is unclear, infer from the repository and state assumptions briefly.

### Threat Model Setup (mandatory)

Before hunting, write down the explicit threat model. Without this, severity assessments drift.

- **Attacker profile** — choose one or more and stay consistent:
  - `anon-external` — unauthenticated internet caller
  - `authenticated-low-priv` — any signed-in user, no special role
  - `cross-tenant` — authenticated user of another tenant / org
  - `admin-or-insider` — privileged operator
  - `compromised-dependency` — malicious upstream package or build step
- **Trust zones crossed** — list every boundary user data traverses (network → service, service → DB, service → external API, service → filesystem, etc.).
- **Existing mitigations to factor out** — note infra-layer protections so you do not double-count them: WAF, network policy / mTLS, IAM scoping, framework CSRF / auth middleware, secret manager, image-pull policy.
- **Out of scope** — anything the review will not touch (e.g. third-party SaaS, infra owned by another team).

State the threat model in one short block at the top of the report. Map each finding back to one of the attacker profiles above.

## Phase 1.5: Quick-Wins Sweep

Before building the full attacker map, run a fast pass over the categories below. These produce the largest share of real-world findings and are cheap to check. Anything found here still goes through the Phase 4 sanity gate and the Phase 5 reporting flow.

### Secrets in code and history

- Code: `rg -i "password|secret|api[_-]?key|token|aws_access_key|BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY"`
- Untracked candidates: `git ls-files --others --exclude-standard | rg -i "\.env|\.pem$|\.key$|credentials"`
- Git history: `git log --all -p -- '*.env*' '*.pem' '*.key' 2>/dev/null | rg -i "BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY|aws_secret|api_key"`
- Secrets removed from HEAD are still leaked via history — recommend rotation, not just deletion.
- Use `trufflehog`, `gitleaks`, or `detect-secrets` if available in the environment.

### CI / CD pwn-request patterns

- `.github/workflows/*.yml`:
  - `pull_request_target` combined with `actions/checkout` of the PR head — fork PRs can exfiltrate repo secrets.
  - `${{ github.event.* }}`, `${{ github.head_ref }}`, or other untrusted context interpolated directly into a `run:` block — shell injection.
  - Self-hosted runners on public repositories.
  - Missing `permissions:` declaration (defaults to read-write on classic tokens).
- GitLab CI / CircleCI / Buildkite: scan for the same context-injection and over-privileged-runner patterns.

### Container build hygiene

- `Dockerfile` / `Containerfile`:
  - No `USER` directive, or `USER root` at runtime.
  - Secrets passed via `ARG` or `ENV` (they remain in image history).
  - `FROM <image>:latest` with no tag pin, or no digest pin for production images.
  - `ADD <url>` with no checksum verification.
  - `COPY` of the entire build context including `.git/` or `.env*`.

### Infrastructure as Code defaults

- Terraform / CloudFormation / Kubernetes manifests:
  - S3 / GCS buckets without explicit private ACL or `BlockPublicAccess`.
  - Security groups / firewalls allowing `0.0.0.0/0` on management ports (22, 3389, 5432, 6379, etc.).
  - IAM policies with `Action: "*"` or `Resource: "*"`.
  - K8s pods without `securityContext`, running as root, or `hostNetwork: true` / `privileged: true`.
  - Managed databases / object stores with encryption-at-rest disabled.

### Dependency surface

- Run the project's audit tool: `npm audit`, `pnpm audit`, `yarn audit`, `pip-audit`, `bundle audit`, `cargo audit`, `gosec`.
- Lockfile drift: lockfile missing, out of sync with the manifest, or not committed.
- Unpinned VCS dependencies (`git+https://...`, `github:org/repo` without commit pin).
- Newly added third-party packages: review maintainer, download stats, and typosquat similarity to popular packages.

## Phase 2: Build An Attacker Map

For each entry point, ask:

- What can an untrusted actor control?
- Where does that value flow next?
- Does it cross authentication, authorization, tenant, process, network, filesystem, or rendering boundaries?
- Can it affect queries, commands, templates, redirects, file paths, external calls, logs, tokens, or policy decisions?
- What would the attacker gain by reading, changing, executing, bypassing, or disrupting this path?

Use `rg`, targeted file reads, and diffs to follow the shortest credible path through the code.

### Taint Analysis Vocabulary (mandatory)

Express every candidate issue as a taint flow with three explicit parts. If you cannot name all three, you do not have a finding yet — you have a suspicion.

- **Source** — where attacker-controlled data enters the program:
  - HTTP request body / query / path / header / cookie
  - File upload, multipart field, filename
  - Message queue payload, webhook body, SSE event
  - Environment variable populated from user-tunable config
  - DB / cache row written by an earlier untrusted path (stored taint)
- **Sink** — where the value reaches a sensitive operation:
  - DB driver (SQL / NoSQL / LDAP query string)
  - Shell / subprocess / `exec` / `eval`
  - Template renderer / HTML sink / `dangerouslySetInnerHTML`
  - File path / archive extractor / symlink-following API
  - HTTP redirect target, server-side fetcher (SSRF)
  - Deserializer (`pickle`, Java ObjectInputStream, YAML unsafe load)
  - Authn / authz decision, signed-cookie or JWT verification
- **Sanitizer** — any control that breaks the path between Source and Sink:
  - Parameterized query / prepared statement
  - Allowlist validation, schema validation, strict type coercion
  - Context-aware escaping (HTML, URL, shell-arg, JSON)
  - Authn / authz gate executed before the sink
  - Framework feature that makes the sink unreachable (e.g. ORM-only access)

A vulnerability exists only when there is a **reachable path** from a Source to a Sink **without a sufficient Sanitizer**. Always state all three in the finding.

## Phase 3: Hunt High-Risk Classes

Check these first:

- Authentication: bypasses, weak token validation, session fixation, unsafe remember-me logic
- Authorization: IDOR, missing object-level checks, tenant isolation failures, role confusion
- Injection: SQL, NoSQL, LDAP, shell, template, unsafe eval, unsafe deserialization
- SSRF and redirects: server-side fetchers, webhook callers, metadata access, open redirect chains
- File handling: traversal, unsafe uploads, archive extraction, symlink races, public file exposure
- XSS and client trust: unsafe HTML sinks, DOM injection, client-only access control
- Crypto and secrets: hardcoded secrets, weak randomness, homegrown crypto, sensitive logs
- Supply chain: risky scripts, dependency confusion, vulnerable packages, lockfile drift
- Operations: permissive CORS, debug endpoints, verbose errors, insecure defaults, CI/CD or IaC exposure
- Business logic: replay, race conditions, limit bypasses, workflow skips, price or privilege tampering
- Observability and logging: PII / tokens / full request bodies leaking into application logs, traces, or error pages; missing audit log on security-critical actions (privilege changes, money movement, key rotation, admin impersonation); over-broad telemetry that itself becomes an exfiltration channel
- Rate limiting and abuse cost: missing per-user / per-IP rate limit or lockout on login, password reset, OTP, signup, token issuance; unbounded expensive endpoints (denial-of-wallet on serverless, GPU paths, large-file processing, image transforms); replay tolerance on webhooks and idempotency keys

### Language / Framework Hints

After detecting the stack, prioritize the stack-specific sinks below. Not exhaustive — these are where real CVEs cluster.

**Node.js / Express / NestJS**
- `child_process.exec` / `execSync` with any user-controlled fragment.
- `path.join` / `fs.*` with user input (path traversal, especially with `..`).
- `eval`, `Function()`, `vm.runInNewContext` on user data.
- Untrusted `Object.assign` / spread / `lodash.merge` — prototype pollution → gadget chains.
- `res.redirect(req.query.next)` — open redirect.
- Unsafe template engine flags: `pug` / `ejs` with HTML-unescaped interpolation.

**Python / Django / Flask / FastAPI**
- `pickle.loads`, `yaml.load` without `SafeLoader`, `marshal.loads` on user bytes.
- `subprocess.*` with `shell=True` and any user-controlled arg.
- Django: `mark_safe`, `format_html` misuse, `extra(where=...)`, `RawSQL`, `DEBUG=True` leaked to prod.
- Flask: `render_template_string(user_input)`.
- `eval` / `exec` reachable from request handlers.
- `requests.get(user_url)` with no host allowlist — SSRF to cloud metadata (`169.254.169.254`).

**Java / Spring / Spring Boot**
- SpEL injection: user input in `@Value`, `SpelExpressionParser`, or `MethodSecurityExpressionRoot`.
- `ObjectInputStream.readObject` on user bytes (Java deserialization).
- JNDI lookup with user-controlled name (Log4Shell-class).
- `Runtime.exec` / `ProcessBuilder` with concatenated strings.
- Spring Security: `permitAll()` on sensitive routes, missing `@PreAuthorize`, default `CsrfFilter` disabled.
- XXE: `DocumentBuilderFactory` without `disallow-doctype-decl` and external-entity features disabled.

**Go**
- `text/template` rendering HTML instead of `html/template`.
- `exec.Command("sh", "-c", userString)` patterns (the safe form is `exec.Command(name, args...)`).
- `unsafe` package usage, especially with pointer arithmetic on user-derived lengths.
- Integer truncation across `int` / `int32` / `int64` boundaries leading to short-buffer bugs.
- `database/sql`: string-concatenated queries instead of placeholders.
- `net/http`: missing `Timeout` on `http.Client` — SSRF amplification and slow-loris DoS.

**Rust**
- `unsafe` blocks combined with pointer arithmetic on user-derived lengths.
- `unwrap` / `expect` / `panic!` reachable from untrusted parsers (DoS via panic).
- `serde_json::from_str` of untyped values without size limits.
- `Command::new("sh").arg("-c").arg(user)` style invocations.

**SQL across all stacks**
- String-concatenated queries — even with apparent escaping.
- Dynamic `ORDER BY` / column names / table names that bypass parameterization.
- `LIKE` with user input that includes wildcards (no escaping of `%` / `_`).

## Phase 4: Prove Plausibility

For each candidate issue:

1. Show the reachable path from attacker-controlled input to vulnerable behavior.
2. Identify required privileges and environmental assumptions.
3. Confirm whether existing validation, authorization, escaping, or isolation blocks the attack.
4. Use local tests, static checks, or safe reasoning when proportionate.
5. Discard issues that do not have a credible path.

### Pre-Report Sanity Gate (mandatory)

Before promoting a candidate to a reported finding, every box below must be checked. If any cannot be ticked, either gather more evidence or drop the issue.

- [ ] Source → Sink path is reachable in production code paths (no dead branch / disabled flag / removed route).
- [ ] No upstream Sanitizer neutralizes the input on this path.
- [ ] Attacker preconditions are realistic for the chosen attacker profile (Phase 1).
- [ ] Severity is assigned per the rubric in Phase 5 — not by gut feel.
- [ ] Evidence type is explicit on the finding (see **Evidence Taxonomy** below).

### Evidence Taxonomy (mandatory)

Every finding must declare exactly one evidence level. This level controls how downstream consumers (triage queue, release gate, customer comms) weigh the report. Do not invent intermediate levels.

| Level | Bar to claim it |
|-------|-----------------|
| `confirmed-by-poc` | A **benign, local PoC** (script, `curl`, unit test, REPL snippet, or executed command) reproduces the unsafe behavior against the project's code as-is. The PoC must have been **executed**, not designed in your head. Attach it inline (fenced code block) in the finding's `Evidence`. |
| `confirmed-by-read` | The Source → Sink data flow is traced **end-to-end through actual code paths** with no remaining unknowns. No PoC was run, but every branch decision, framework hook, and middleware order is anchored to a `file:line` reference. List the references in `Evidence`. |
| `inferred-pattern` | A vulnerable pattern was matched (regex, `rg`, framework convention, dependency CVE) but the full flow was not traced. Treat as a "credible hypothesis, not confirmed bug". Severity drops one level per the Phase 5 rubric. Useful for surfacing follow-up work. |

If none of these bars can be met, the candidate is not a finding. Move it to `Residual Risk / Next Checks` in Phase 5 so it is not lost, but do not let it appear in the `Findings` section.

Rules for honest classification:

- A PoC that "would work in theory" is `confirmed-by-read` at best.
- A read that leaves any unresolved "I think this is set elsewhere" is `inferred-pattern`, not `confirmed-by-read`.
- A finding that depends on a CVE in a dependency is `inferred-pattern` until you confirm the vulnerable code path is reachable from your project's usage — then it can be upgraded.

## Phase 5: Report Findings

Lead with `Top 3 Fix-First`, then the threat model block, then findings ordered by severity. The Top 3 list is mandatory — busy maintainers read it before anything else.

### Severity Rubric (mandatory)

Assign severity strictly against this rubric. Two reviewers using this skill should reach the same label for the same finding.

| Label | Criteria (any one is sufficient) |
|-------|----------------------------------|
| **Critical** | Unauthenticated RCE; mass exfiltration of credentials, secrets, or PII; direct money loss; full account takeover at scale; supply-chain compromise of build output |
| **High** | Authenticated RCE; privilege escalation (user → admin, tenant A → tenant B); IDOR exposing PII or money-moving objects; persistent XSS in privileged UI; auth bypass requiring no special preconditions |
| **Medium** | Vulnerability that requires realistic but non-default conditions (user interaction, specific flag, narrow timing); reflected XSS without admin context; SSRF to internal services with limited reach; sensitive info in logs |
| **Low** | Defense-in-depth gap; hardening miss; low-impact info disclosure; missing rate-limit / lockout on non-critical surface |
| **Info** | Style, hygiene, or hardening suggestion with no current exploit path |

Severity drops one level when the only evidence type is `inferred-pattern`. Severity drops one level when the only viable attacker profile is `admin-or-insider` and no privilege boundary is crossed.

### Report Structure

```markdown
## Top 3 Fix-First
Ordered triage list. Exactly 0–3 entries pulled from `Findings`. If `Findings` is empty, write "No fix-first items.".
1. [Severity] <Finding title> — <one-line reason this is highest priority>
2. ...
3. ...

## Threat Model
- Attacker profile(s): ...
- Trust zones in scope: ...
- Existing mitigations factored out: ...
- Out of scope: ...

## Findings

### [Severity] Title
- Location: path/to/file:line
- CWE: CWE-XXX — short name (e.g. CWE-89 SQL Injection)
- CVSS (estimate): CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H — score X.X
- Attacker profile: <anon-external | authenticated-low-priv | cross-tenant | admin-or-insider | compromised-dependency>
- Preconditions: <default-config | requires flag X | requires victim action | requires stored taint from path Y>
- Source → Sink: <input origin> → <vulnerable sink>
- Sanitizers observed: <none | only on path Y, not on this one>
- Evidence: <confirmed-by-poc | confirmed-by-read | inferred-pattern>
- Impact: what can be read, changed, executed, bypassed, or disrupted
- Fix: concrete implementation guidance that fits the repo
- Verification: test, command, or review step to confirm the fix

> **CWE / CVSS conventions**
> - **CWE** is mandatory. Pick the most specific identifier from <https://cwe.mitre.org>. If multiple apply, list the primary one and mention secondaries in `Impact`.
> - **CVSS** is an estimate, not a substitute for the Severity Rubric above. Use the standard v3.1 vector string. Environmental and temporal metrics are usually unknown — leave them out. If the rubric and the CVSS score disagree, the **rubric wins** for triage; record the disagreement in `Open Questions`.

## Open Questions / Assumptions

## Reviewed With No Finding
- List entry points / files / classes that were inspected and produced no finding, so the negative result is auditable.

## Residual Risk / Next Checks
```

Use only the severity labels defined in the rubric above: Critical, High, Medium, Low, Info.

If there are no findings, write:

```markdown
## Top 3 Fix-First
No fix-first items.

## Threat Model
- Attacker profile(s): ...
- Trust zones in scope: ...
- Existing mitigations factored out: ...
- Out of scope: ...

## Findings

No confirmed vulnerabilities found in the reviewed scope.

## Reviewed With No Finding
- <enumerate entry points, files, and classes inspected so the negative result is auditable>

## Review Limits

- <tests not run, config missing, dependency audit skipped, or other limits>
```

### Optional: Structured JSON Output

If the caller asks for JSON (e.g. "report as JSON", "for tooling consumption", or `$ARGUMENTS` contains `--format=json`), emit a single JSON object instead of (or in addition to) the markdown report. The Markdown report remains the default.

```json
{
  "threat_model": {
    "attacker_profiles": ["anon-external"],
    "trust_zones": ["public-internet -> web-app -> db"],
    "existing_mitigations": ["WAF blocks well-known signatures"],
    "out_of_scope": ["third-party SaaS identity provider"]
  },
  "top_fixes": [
    {"id": "F001", "title": "Unauth SQL injection in /api/search", "severity": "Critical", "reason": "anon-external, default config, full DB read"}
  ],
  "findings": [
    {
      "id": "F001",
      "title": "Unauth SQL injection in /api/search",
      "severity": "Critical",
      "cwe": "CWE-89",
      "cvss": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
      "cvss_score": 9.8,
      "location": "src/api/search.py:42",
      "attacker_profile": "anon-external",
      "preconditions": "default-config",
      "source": "query string param `q`",
      "sink": "raw SQL string concatenation",
      "sanitizers_observed": "none",
      "evidence": "confirmed-by-poc",
      "evidence_detail": "curl 'https://host/api/search?q=...' returned full row dump",
      "impact": "Full read of `users` table including hashes.",
      "fix": "Switch to parameterized query via `cursor.execute(sql, params)`; reject `q` longer than N chars.",
      "verification": "pytest tests/test_search.py::test_quote_injection",
      "diff_classification": "new-surface"
    }
  ],
  "open_questions": [],
  "reviewed_no_finding": ["src/api/health.py — no user-controlled input"],
  "residual_risk": [],
  "review_limits": ["dependency audit skipped (no lockfile)"]
}
```

Schema rules:

- `severity` ∈ `{"Critical", "High", "Medium", "Low", "Info"}`
- `evidence` ∈ `{"confirmed-by-poc", "confirmed-by-read", "inferred-pattern"}`
- `attacker_profile` ∈ `{"anon-external", "authenticated-low-priv", "cross-tenant", "admin-or-insider", "compromised-dependency"}`
- `diff_classification` ∈ `{"regression", "new-surface", "pre-existing"}` — present only in Diff Mode
- `top_fixes` has 0–3 entries, each referencing a `findings[].id`. Empty only when `findings` is empty.
- All other fields are required. Use `null` rather than omitting a field when a value is genuinely unknown.
