---
title: Auditing code and pull requests
source: https://docs.github.com/en/code-security/concepts/code-scanning/code-scanning
fetched: 2026-11-11
summary: Turn checks on every pull request into annotations, summaries, comments and merge gates, with your own Python or TypeScript audit scripts plus GitHub's scanners.
group: Auditing and security
---

An **audit job** is an ordinary workflow job that runs on `pull_request`, inspects the change, and reports what it found. The report can be a failed check, which can block merging, *annotations* pinned to lines in the diff, a Markdown *job summary*, a comment on the pull request, or *code scanning alerts* in the repository's Security tab. GitHub supplies two scanners, code scanning (CodeQL) and dependency review. Any linter or script that prints in the right format can join them. Use audit jobs for rules your team keeps repeating in review: no debugger calls, no unreviewed dependencies, no secrets, no dangerous workflow changes.

:::infobox
Trigger: `pull_request` (not `pull_request_target`)
Fail a check: exit with a non-zero code
Annotate a line: `::error file=F,line=N::message`
Summary: append Markdown to `$GITHUB_STEP_SUMMARY`
Comment: `gh pr comment` with `pull-requests: write`
GitHub scanners: CodeQL code scanning, dependency review
Third-party scanners: upload SARIF
Related: [Workflow security](security.md), [Writing workflows](workflows.md)
:::

## How it works

Every audit, built-in or homemade, has the same shape: read the change, apply rules, report through one or more channels. What differs is where the report lands and who can see it.

```flow From a pull request to a merge decision
PR opened or updated : `pull_request` event
Audit jobs run : linters, your scripts, scanners
-> report through
Annotations | Summary | Comment | Alerts : where reviewers see findings
Check passes or fails : exit code
-> if required
Merge allowed or blocked
```

### The reporting channels

| Channel | How a job produces it | Where it shows | Works on fork PRs |
|---|---|---|---|
| Check status | Any step exits non-zero | PR checks list; blocks merge if required | Yes |
| Annotation | Print `::error`, `::warning` or `::notice` lines | On the file and line in the diff, and the run page | Yes |
| Job summary | Append Markdown to `$GITHUB_STEP_SUMMARY` | The run's summary page | Yes |
| PR comment | `gh pr comment` or the REST API with `GITHUB_TOKEN` | PR conversation | No: the token is read-only for forks[^fork-token] |
| Code scanning alert | CodeQL, or upload a SARIF file | Security tab and the PR | Depends on setup |

**Annotations** are the most useful channel for a homemade audit. An error command "will create an annotation, which can associate the message with a particular file in your repository" and can point at a line.[^annotation] The format is one line on standard output:

```text
::error file={name},line={line},endLine={endLine},title={title}::{message}
```

`::warning` and `::notice` use the same parameters. Anything a step prints in this form becomes an annotation, so a script in any language can produce them, and so can linters that support it (Ruff's `--output-format=github`).

**Job summaries** are for the overview: counts, tables, links. Summaries are meant to show results "so that someone viewing the result of a workflow run doesn't need to go into the logs".[^summary]

**Merge gates.** A check only blocks merging when the branch is protected with *required status checks*. GitHub's dependency review docs describe the pattern: "A failed check blocks a pull request from being merged when the repository owner requires the dependency review check to pass."[^required] The same setting works for any job name.

## By example

:::example A diff audit in Python
The script reads `git diff` between the PR's base and `HEAD`, looks only at added lines, and prints an annotation per finding. It exits `1` if any finding is an error, which fails the check. Standard library only.

```python scripts/audit_diff.py
"""Flag risky lines added by a pull request. Usage: python scripts/audit_diff.py BASE_SHA"""
import os, re, subprocess, sys

RULES = [  # (pattern, severity, message)
    (re.compile(r"\bbreakpoint\(\)|\bpdb\.set_trace\(\)"), "error", "Debugger call left in code"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "error", "Looks like an AWS access key"),
    (re.compile(r"\bTODO\b(?!\(#\d+\))"), "warning", "TODO without an issue number, e.g. TODO(#123)"),
]

base = sys.argv[1]
diff = subprocess.run(["git", "diff", "--unified=0", f"{base}...HEAD"],
                      capture_output=True, text=True, check=True).stdout

findings, path, line = [], None, 0
for raw in diff.splitlines():
    if raw.startswith("+++ "):
        path = raw[6:] if raw.startswith("+++ b/") else None
    elif raw.startswith("@@"):
        line = int(re.search(r"\+(\d+)", raw).group(1))   # first new line of the hunk
    elif raw.startswith("+") and path:
        for pattern, severity, message in RULES:
            if pattern.search(raw):
                findings.append((severity, path, line, message))
        line += 1

for severity, path, line, message in findings:
    print(f"::{severity} file={path},line={line}::{message}")   # becomes an annotation

summary = os.environ.get("GITHUB_STEP_SUMMARY")
if summary:
    with open(summary, "a") as f:
        f.write(f"### Diff audit\n{len(findings)} finding(s)\n")

sys.exit(1 if any(s == "error" for s, *_ in findings) else 0)
```

Run locally on a branch that adds a `breakpoint()` and a bare `TODO` to `app/cart.py`. Outside Actions the lines are plain text; inside a workflow, GitHub turns them into annotations.

```console
$ python scripts/audit_diff.py main
::warning file=app/cart.py,line=2::TODO without an issue number, e.g. TODO(#123)
::error file=app/cart.py,line=3::Debugger call left in code
$ echo $?
1
```
:::

:::example The same audit in TypeScript
Same structure, with rules for JavaScript and TypeScript code. Node.js 24 ran this `.ts` file directly, with no build step, when it was tested for this page.

```typescript scripts/audit-diff.ts
// Flag risky lines added by a pull request. Usage: node scripts/audit-diff.ts BASE_SHA
import { execFileSync } from "node:child_process";
import { appendFileSync } from "node:fs";

type Rule = { pattern: RegExp; severity: "error" | "warning"; message: string };
const rules: Rule[] = [
  { pattern: /\bdebugger\b/, severity: "error", message: "debugger statement left in code" },
  { pattern: /\b(it|test|describe)\.only\(/, severity: "error", message: ".only() skips the rest of the test suite" },
  { pattern: /console\.log\(/, severity: "warning", message: "console.log in committed code" },
];

const base = process.argv[2];
const diff = execFileSync("git", ["diff", "--unified=0", `${base}...HEAD`], { encoding: "utf8" });

const findings: { severity: string; path: string; line: number; message: string }[] = [];
let path: string | null = null;
let line = 0;
for (const raw of diff.split("\n")) {
  if (raw.startsWith("+++ ")) path = raw.startsWith("+++ b/") ? raw.slice(6) : null;
  else if (raw.startsWith("@@")) line = Number(/\+(\d+)/.exec(raw)![1]);
  else if (raw.startsWith("+") && path) {
    for (const r of rules) if (r.pattern.test(raw)) findings.push({ ...r, path, line });
    line++;
  }
}

for (const f of findings) console.log(`::${f.severity} file=${f.path},line=${f.line}::${f.message}`);
if (process.env.GITHUB_STEP_SUMMARY)
  appendFileSync(process.env.GITHUB_STEP_SUMMARY, `### Diff audit\n${findings.length} finding(s)\n`);
process.exit(findings.some((f) => f.severity === "error") ? 1 : 0);
```

```console
$ node scripts/audit-diff.ts main
::error file=src/cart.test.ts,line=2::.only() skips the rest of the test suite
::warning file=src/cart.ts,line=2::console.log in committed code
$ echo $?
1
```
:::

:::example The workflow that runs both, plus GitHub's dependency review
Two details make the diff work in CI. The checkout must include history, or the base commit isn't there to diff against. And the base SHA comes from the event payload, passed through `env:` rather than pasted into the script.

```yaml .github/workflows/pr-audit.yml
name: PR audit
on:
  pull_request:

permissions:
  contents: read

jobs:
  diff-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0               # full history, so the base commit exists
      - uses: actions/setup-python@v5
        with: { python-version: '3.x' }
      - uses: actions/setup-node@v7
        with: { node-version: '24' }
      - name: Python rules
        env:
          BASE_SHA: ${{ github.event.pull_request.base.sha }}
        run: python scripts/audit_diff.py "$BASE_SHA"
      - name: TypeScript rules
        if: ${{ !cancelled() }}        # run even if the Python rules failed
        env:
          BASE_SHA: ${{ github.event.pull_request.base.sha }}
        run: node scripts/audit-diff.ts "$BASE_SHA"

  dependency-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/dependency-review-action@v5
```

The dependency review action compares the manifests and lock files between base and head and "scans for vulnerable versions of dependencies introduced by package version changes in pull requests".[^dr-action] By default it fails the check "if it discovers any vulnerable packages."[^dr-fail] It works on public repositories, and on private ones only with GitHub Code Security or Advanced Security.[^dr-avail]
:::

:::background Checkout depth
`actions/checkout` fetches only the latest commit by default; `fetch-depth: 0` fetches all history. This comes from the [actions/checkout README](https://github.com/actions/checkout), not from the pages condensed here. On a `pull_request` run, `HEAD` is the temporary merge commit, so `base...HEAD` is exactly what the PR adds.
:::

## Built-in scanners

### Code scanning with CodeQL

Code scanning is GitHub's static analysis, "a feature that you use to analyze the code in a GitHub repository to find security vulnerabilities and coding errors". It shows alerts in the repository, and closes an alert when the code that triggered it is fixed.[^cs] It runs on Actions and uses Actions minutes. On private repositories it needs a GitHub Code Security license.[^cs-license]

Two ways to turn it on:

- **Default setup**: enable it in the repository's security settings. No workflow file to write. Start here.
- **Advanced setup**: a CodeQL workflow file you control, from GitHub's code scanning templates.[^cs-template]

CodeQL can also scan your workflow files themselves: it "can scan and detect potentially vulnerable GitHub Actions workflows" when Actions scanning is enabled in default setup.[^codeql-actions] That covers the injection and `pull_request_target` mistakes on [Workflow security](security.md).

### Third-party tools through SARIF

Any analyzer that writes SARIF can feed the same alert system: code scanning "is interoperable with third-party code scanning tools that output Static Analysis Results Interchange Format (SARIF) data."[^sarif] Many security tools can write SARIF. Upload the file, and its findings appear as alerts next to CodeQL's.

### Choosing the layer

| Need | Use |
|---|---|
| Style, unused imports, type errors | Linter and type checker in CI, with annotation output |
| A team rule no linter has | Your own script printing `::error` lines |
| New dependency with a known CVE | Dependency review action |
| Injection, unsafe deserialization, path traversal | CodeQL default setup |
| An existing security tool | Run it in a job and upload SARIF |
| Dangerous workflow files | CodeQL Actions scanning, OpenSSF Scorecard[^scorecard] |

:::recipes
- Annotate a line from any script:
  `echo "::error file={{path}},line={{line}}::{{message}}"`

- Add a section to the run's summary page:
  `echo "### Audit: {{n}} findings" >> "$GITHUB_STEP_SUMMARY"`

- Comment on the pull request (job needs `pull-requests: write`):
  ```yaml
  - run: gh pr comment "$PR" --body-file report.md
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      PR: ${{ github.event.pull_request.number }}
  ```

- Get the PR's base commit SHA inside a job:
  `${{ github.event.pull_request.base.sha }}`

- Get the PR's head commit instead of the merge commit:
  `${{ github.event.pull_request.head.sha }}`

- Report a finding without failing the check:
  `echo "::warning file={{path}},line={{line}}::{{message}}"`

- Block vulnerable dependencies on every PR:
  `- uses: actions/dependency-review-action@v5`
:::

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `fatal: Invalid symmetric difference expression <sha>...HEAD` | Shallow checkout; base commit not fetched | `fetch-depth: 0` on `actions/checkout` |
| Audit flags lines the PR didn't touch | Diffing the working tree, or against the wrong base | Diff `base.sha...HEAD`, added lines only |
| Comment step fails on PRs from forks | `GITHUB_TOKEN` is read-only for fork PRs[^fork-token] | Report with annotations and summaries; they need no write access |
| Audit "fixed" by switching to `pull_request_target` to get write access | That trigger runs with secrets and write access; checking out the PR's code there is the classic takeover | Don't. See [Workflow security](security.md#pull-request-triggers) |
| Failing audit doesn't block merging | Check isn't marked required | Add it under required status checks for the branch |
| Second audit step never runs after the first fails | Steps stop at the first failure | `if: ${{ !cancelled() }}` on later steps |
| Base SHA or PR title interpolated straight into `run:` | Script injection risk for titles and branch names | Pass through `env:` as in the example |

## Not covered

- AI review: [Copilot code review](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review) and [agentic workflows](https://docs.github.com/en/copilot/how-tos/github-agentic-workflows/creating-github-agentic-workflows), which take natural-language rules.
- Configuring the dependency review action (severity threshold, license allow and deny lists): [Configuring the dependency review action](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/configure-dependency-review-action).
- Secret scanning and push protection, which block secrets before they are pushed: [Secret scanning](https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning).
- Uploading SARIF: [Uploading a SARIF file to GitHub](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/integrate-with-existing-tools/upload-sarif-file).
- Dependabot alerts and updates for dependencies already merged: [Dependabot alerts](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-alerts).

## Check yourself

:::recall
What makes an audit job's failure block a merge?
: The job exits non-zero, and the branch requires that check to pass.[^required]
Your audit comments on PRs. Why does it fail for contributors who fork the repository, and what still works?
: The token is read-only for fork PRs, so commenting fails. Annotations, summaries and the check status still work.[^fork-token]
How does a Python or TypeScript script attach a finding to line 12 of `app.py`?
: It prints `::error file=app.py,line=12::message` to standard output.[^annotation]
Why does the audit workflow use `fetch-depth: 0`?
: The base commit must be in the local clone for `git diff base...HEAD` to work.
What does dependency review catch that a test suite doesn't?
: A PR that adds or upgrades a dependency to a version with a known vulnerability, including indirect ones in lock files.[^dr-action]
How do findings from a non-GitHub analyzer get into code scanning alerts?
: The tool outputs SARIF and the workflow uploads it.[^sarif]
:::

[^fork-token]: "The `GITHUB_TOKEN` has read-only permissions in pull requests from forked repositories." https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request
[^annotation]: "This message will create an annotation, which can associate the message with a particular file in your repository. Optionally, your message can specify a position within the file." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#setting-an-error-message
[^summary]: "so that someone viewing the result of a workflow run doesn't need to go into the logs to see important information related to the run" https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#adding-a-job-summary
[^required]: "A failed check blocks a pull request from being merged when the repository owner requires the dependency review check to pass." https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-review#about-the-dependency-review-action
[^dr-action]: "The action scans for vulnerable versions of dependencies introduced by package version changes in pull requests, and warns you about the associated security vulnerabilities." https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-review#about-the-dependency-review-action
[^dr-fail]: "By default, the dependency review action check will fail if it discovers any vulnerable packages." https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-review#about-the-dependency-review-action
[^dr-avail]: "The action is available for all public repositories, as well as private repositories that have GitHub Code Security or GitHub Advanced Security enabled." https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-review#about-the-dependency-review-action
[^cs]: "Code scanning is a feature that you use to analyze the code in a GitHub repository to find security vulnerabilities and coding errors." https://docs.github.com/en/code-security/concepts/code-scanning/code-scanning
[^cs-license]: "If you want to use code scanning on private repositories, you need a GitHub Code Security license." https://docs.github.com/en/code-security/concepts/code-scanning/code-scanning
[^cs-template]: "GitHub provides workflow templates for code scanning." https://docs.github.com/en/actions/reference/security/secure-use#using-workflow-templates-for-code-scanning
[^codeql-actions]: "CodeQL can scan and detect potentially vulnerable GitHub Actions workflows." https://docs.github.com/en/actions/reference/security/secure-use#good-practices
[^sarif]: "Code scanning is interoperable with third-party code scanning tools that output Static Analysis Results Interchange Format (SARIF) data." https://docs.github.com/en/code-security/concepts/code-scanning/code-scanning#about-third-party-code-scanning-tools
[^scorecard]: "OpenSSF Scorecards can help you identify potentially vulnerable workflows, along with other security risks when using GitHub Actions." https://docs.github.com/en/actions/reference/security/secure-use#good-practices
