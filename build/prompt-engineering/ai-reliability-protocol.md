[中文](ai-reliability-protocol.zh.md) | **English**

# AI Reliability Protocol: Preventing Hallucinations in ChatGPT and Codex

> Karpathy check: treat the model as a probabilistic executor, not a source of truth. Reliability comes from evidence, constraints, validation, and rollback.

---

## Core Judgment

You do not prevent hallucination by asking an AI to be honest. You prevent hallucination by designing the workflow so that unsupported claims are visible, costly, and blocked before they become decisions.

The goal is not:

```text
Please do not hallucinate.
```

The goal is:

```text
No evidence, no conclusion.
No execution, no pass claim.
No diff, no change claim.
No validation, no completion claim.
No rollback, no production change.
```

---

## Why AI Hallucinates

Most hallucinations come from four failure modes:

| Failure mode | What happens | Typical symptom |
|---|---|---|
| Missing context | The model fills gaps with common patterns | It mentions files, APIs, versions, or causes you never provided |
| Plausibility bias | A reasonable answer is treated as a true answer | Commands and config keys look realistic but do not exist |
| No execution boundary | The model speaks as if it tested something | It says tests passed without command output |
| Vague task definition | The model optimizes for a complete-looking answer | Long answer, weak evidence, no verification path |

The practical fix is to force the model to separate **facts**, **inferences**, **assumptions**, and **unknowns** before giving a conclusion.

---

## Reliability Stack

Use this stack for important ChatGPT or Codex work:

| Layer | Purpose | Minimum control |
|---|---|---|
| Evidence | Prevent unsupported claims | Require source, file, log, command output, or official docs |
| Uncertainty | Prevent false confidence | Label fact / inference / assumption / unknown |
| Scope | Prevent unrelated changes | Define exact task boundary and forbidden actions |
| Execution | Prevent fake verification | Require command output for tests, build, lint, dry-run |
| Diff | Prevent invisible edits | Review changed files and changed intent |
| Rollback | Prevent irreversible damage | State recovery path before production-impacting action |

---

## ChatGPT Protocol

Use ChatGPT as an analysis and decision assistant, not as a final authority.

### Default prompt for high-accuracy work

```text
Before answering, classify information into four groups:

A. Verified facts: only from my provided content, files, logs, screenshots, official docs, accessible web pages, or actual command output.
B. Reasonable inferences: derived from facts, but not directly proven.
C. Assumptions: temporary conditions used to continue the analysis.
D. Unknowns: information that cannot be confirmed from the current context.

Rules:
1. Do not invent commands, APIs, versions, paths, config keys, references, GitHub repositories, or official conclusions.
2. If context is insufficient, say what is missing.
3. For technical issues, answer with: symptom → evidence → judgment → validation → risk → rollback or fix.
4. For current product behavior, pricing, releases, laws, security advisories, or official documentation, search and cite primary sources.
5. If you did not run a test, do not say it passed.
6. End with confidence: high / medium / low, with the reason.
```

### Better question pattern

Weak:

```text
How do I fix this?
```

Strong:

```text
Based on the logs, config, version, and command output below, identify the root cause.
Use only the evidence I provide.
If you need an assumption, label it explicitly.
Every conclusion must map to evidence.
Give me the smallest validation path before suggesting a fix.
```

### Self-audit prompt

Use this when an answer feels too confident:

```text
Audit your previous answer.
List:
1. Which claims are directly supported by evidence?
2. Which claims are only inferences?
3. Which claims may be hallucinated?
4. What is the smallest action needed to verify the conclusion?
```

---

## Codex Protocol

Codex needs stronger controls because it can read files, edit code, run commands, and affect the repository.

The safe default is a two-phase workflow:

1. **Read-only analysis**: inspect files, summarize evidence, propose minimal change.
2. **Scoped execution**: change only approved files, show diff, run validation, report risk.

### Phase 1: read-only analysis prompt

```text
Enter read-only analysis mode.
Do not modify files.
Do not run destructive commands.
Do not produce a final implementation yet.

Do this first:
1. Identify relevant files and configs.
2. List verified facts from the repository.
3. List unknowns and assumptions.
4. Propose the smallest safe change.
5. Wait for confirmation before editing.
```

### Phase 2: scoped execution prompt

```text
Implement only the approved change.
Requirements:
1. Modify only necessary files.
2. Do not refactor unrelated code.
3. Show the diff summary.
4. Run the smallest relevant validation command.
5. If validation fails, stop and explain before expanding the change.
```

---

## Recommended Codex `AGENTS.md`

Put global rules in `~/.codex/AGENTS.md` and project-specific rules in the repository root.

```md
# Codex Working Rules

## Truth and Evidence

- Do not claim something is true unless it is verified from repository files, command output, tests, official documentation, or user-provided context.
- If you did not read a file, do not describe its contents.
- If you did not run a command, do not say the result passed.
- If information is uncertain, mark it as uncertain.
- Never invent APIs, package names, config keys, file paths, environment variables, or test results.

## Change Discipline

Before making changes:
1. Inspect relevant files.
2. Summarize current evidence.
3. Propose a minimal change plan.
4. State risks and rollback path.

When making changes:
1. Keep diffs minimal.
2. Do not refactor unrelated code.
3. Do not add dependencies without approval.
4. Do not modify secrets, credentials, production configs, or deployment files unless explicitly requested.

After changes:
1. Show changed files.
2. Run the smallest relevant test, lint, typecheck, build, or dry-run.
3. If validation cannot run, explain why.
4. Mark the result as Verified, Partially verified, or Not verified.
```

---

## Recommended Codex `config.toml`

Conservative default:

```toml
# ~/.codex/config.toml
model = "gpt-5.5"
approval_policy = "on-request"
sandbox_mode = "workspace-write"
```

More conservative for production, infrastructure, or secret-heavy repositories:

```toml
approval_policy = "on-request"
sandbox_mode = "read-only"
```

Avoid this as a daily default:

```toml
approval_policy = "never"
sandbox_mode = "danger-full-access"
```

Use full access only inside a disposable, isolated environment.

---

## Recommended Codex Rules

Use rules for commands that should always be blocked or reviewed.

```text
# ~/.codex/rules/default.rules

prefix_rule(
  pattern = ["git", "reset", "--hard"],
  decision = "forbidden",
  justification = "Do not discard local changes. Show diff and ask the user instead."
)

prefix_rule(
  pattern = ["git", "clean"],
  decision = "forbidden",
  justification = "Do not delete untracked files automatically."
)

prefix_rule(
  pattern = ["rm", "-rf"],
  decision = "prompt",
  justification = "Destructive deletion requires explicit review."
)

prefix_rule(
  pattern = ["kubectl", "delete"],
  decision = "prompt",
  justification = "Kubernetes deletion may affect running services."
)

prefix_rule(
  pattern = ["helm", "upgrade"],
  decision = "prompt",
  justification = "Helm upgrades must be reviewed before applying."
)

prefix_rule(
  pattern = ["docker", "compose", "down", "-v"],
  decision = "forbidden",
  justification = "Volume deletion may cause data loss."
)
```

---

## Decision Checklist

Before accepting an AI answer, check:

```text
□ Did it separate facts, inferences, assumptions, and unknowns?
□ Does every strong conclusion have evidence?
□ Are current/version-sensitive claims backed by search or official docs?
□ Did it avoid describing files it did not read?
□ Did it avoid claiming tests passed without command output?
□ Is the suggested change minimal?
□ Is there a validation command?
□ Is there a rollback path for risky changes?
```

---

## Definition of Done

For ChatGPT:

```text
A useful answer is not finished until it gives evidence, uncertainty, validation, and confidence.
```

For Codex:

```text
A task is not done until the repository was inspected, the diff is minimal, validation was run or explicitly skipped, and remaining risk is listed.
```

---

## Official References

- OpenAI Help Center: ChatGPT can produce incorrect or misleading outputs, including fabricated citations and overconfident answers. Important information should be verified from reliable sources.
  - https://help.openai.com/en/articles/8313428-does-chatgpt-tell-the-truth
- OpenAI Help Center: ChatGPT Search can provide timely answers with links and inline citations when search is used.
  - https://help.openai.com/en/articles/9237897-chatgpt-search
- OpenAI Developers: Codex reads `AGENTS.md` files before work and supports global and project-level guidance.
  - https://developers.openai.com/codex/guides/agents-md
- OpenAI Developers: Codex configuration supports model, approval policy, and sandbox settings through `config.toml`.
  - https://developers.openai.com/codex/config-basic
- OpenAI Developers: Codex sandboxing and approvals define what Codex can do autonomously and when it must ask.
  - https://developers.openai.com/codex/concepts/sandboxing
- OpenAI Developers: Codex rules can allow, prompt, or forbid command prefixes outside the sandbox.
  - https://developers.openai.com/codex/rules

---

*[中文版 (Chinese)](ai-reliability-protocol.zh.md)*
