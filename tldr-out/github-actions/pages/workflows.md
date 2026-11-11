---
title: Writing workflows
source: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
fetched: 2026-11-11
summary: The 20% of workflow syntax used in most files, covering triggers, job order, conditions, matrices, data passing, permissions and concurrency.
group: Basics
---

A **workflow file** is a YAML document with three top-level parts: `on` (when to run), `jobs` (what to run) and optional settings that apply to every job, such as `permissions`, `env` and `concurrency`. This page covers the keys found in nearly every CI file, and the rules that cause most surprises: how filters combine, when jobs are skipped, and how data moves between steps and jobs.

:::infobox
File: `.github/workflows/<name>.yml` or `.yaml`
Top-level keys: `name`, `on`, `permissions`, `env`, `concurrency`, `jobs`
Job keys: `runs-on`, `needs`, `if`, `strategy`, `steps`, `outputs`, `timeout-minutes`
Step keys: `name`, `id`, `uses`, `with`, `run`, `env`, `if`
Expression syntax: `${{ ... }}`
Main article: [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
:::

:::background YAML in one paragraph
YAML expresses nested data with indentation (spaces only, never tabs). `key: value` is a mapping entry; a line starting with `- ` is a list item. `[a, b]` is an inline list. `|` starts a multi-line string, used for multi-line shell scripts. Strings rarely need quotes, but quote values that look like numbers (`"3.10"`, otherwise read as `3.1`) or start with special characters such as `*`, `!` or `{`.
:::

## A complete CI file

Start with a realistic file. Every key in it is explained below.

```yaml .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]          # pushes to main only
  pull_request:               # every PR, any target branch
  workflow_dispatch:          # adds a "Run workflow" button

permissions:
  contents: read              # least privilege for every job

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true    # a new push cancels the old run

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'
      - run: pipx install ruff
      - run: ruff check --output-format=github

  test:
    needs: lint               # waits for lint to pass
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - run: pip install -r requirements.txt
      - run: pytest
```

```flow What this file runs on a pull request
`lint` : 1 job
-> passes
`test` × 3 : one per Python version, in parallel
-> all pass
Green check on the PR
```

## Triggers: `on`

`on` lists the events. Each event can take filters.

| Event | Fires when | Common filters |
|---|---|---|
| `push` | Commits are pushed | `branches`, `tags`, `paths` |
| `pull_request` | A PR is opened, updated or reopened | `branches` (the target), `paths`, `types` |
| `schedule` | A cron time is reached | `cron` |
| `workflow_dispatch` | Someone presses **Run workflow** | `inputs` |
| `pull_request_target` | Same as `pull_request`, but runs with the base repository's privileges | see [Workflow security](security.md) |

Defaults that matter:

- `pull_request` with no `types` runs only for `opened`, `synchronize` or `reopened`.[^pr-types] `synchronize` means new commits were pushed to the PR branch.
- A `pull_request` run tests the *merge* of your branch into the target, not your branch alone: "Your CI tests run against the merged result, not just the head branch alone."[^merge]
- `schedule` uses cron syntax in UTC, runs "on the latest commit on the default branch", and can't run more often than every 5 minutes.[^cron] In public repositories, scheduled workflows "are automatically disabled when no repository activity has occurred in 60 days."[^cron-60]
- `workflow_dispatch` "only receives events when the workflow file is on the default branch."[^dispatch] A manual button added on a feature branch does not appear until merged.

### Filters combine with AND

`branches` and `paths` on the same event must both match: "If you define both `branches`/`branches-ignore` and `paths`/`paths-ignore`, the workflow will only run when both filters are satisfied."[^and] You can't use `paths` and `paths-ignore` on the same event; to exclude inside an include list, prefix a pattern with `!`, and order matters.[^paths]

```yaml
on:
  pull_request:
    paths:
      - 'src/**'
      - '!src/**/*.md'     # excluded, because it comes after the include
```

:::warning Path filters and required checks
If a workflow is skipped by a `paths` or `branches` filter, its checks stay *Pending* and a pull request that requires them is blocked from merging.[^pending] Keep required checks unfiltered, or decide inside the job with `if:`.
:::

## Jobs: order, conditions, matrices

### `needs`

Jobs start in parallel. `needs: [a, b]` makes a job wait for both. If a needed job fails or is skipped, every job downstream is skipped too, "unless the jobs use a conditional expression that causes the job to continue", such as `if: ${{ always() }}`.[^needs]

### `if`

`if:` on a job or step skips it unless the expression is true. You can leave out `${{ }}` in `if`, except when the expression starts with `!`, because "`!` is reserved notation in YAML format."[^bang]

```yaml
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
if: ${{ ! startsWith(github.ref, 'refs/tags/') }}
if: failure()          # step runs only if an earlier step failed
```

### `strategy.matrix`

A matrix turns one job definition into one job per combination of values. Each combination's values are in the `matrix` context. With two lists of 3 and 2 values, you get 6 jobs; the cap is 256 per run.[^matrix-max] `exclude` drops combinations. `fail-fast` defaults to `true`, so "GitHub will cancel all in-progress and queued jobs in the matrix if any job in the matrix fails."[^fail-fast] Set `fail-fast: false` when you want to see every version's result.

```yaml
strategy:
  fail-fast: false
  matrix:
    os: [ubuntu-latest, windows-latest]
    node-version: [20, 22, 24]
    exclude:
      - os: windows-latest
        node-version: 20
runs-on: ${{ matrix.os }}
```

## Expressions and contexts

`${{ expr }}` is replaced with a value before the step runs. The values come from **contexts**:

| Context | Holds | Example |
|---|---|---|
| `github` | The event and repository | `github.ref`, `github.sha`, `github.event.pull_request.number` |
| `matrix` | The current matrix combination | `matrix.python-version` |
| `secrets` | Encrypted secrets | `secrets.GITHUB_TOKEN`, `secrets.PYPI_TOKEN` |
| `vars` | Plain configuration variables | `vars.DEPLOY_REGION` |
| `env` | Variables set with `env:` | `env.NODE_ENV` |
| `steps` | Outputs of earlier steps in this job | `steps.build.outputs.version` |
| `needs` | Outputs of jobs this job needs | `needs.build.outputs.version` |
| `inputs` | `workflow_dispatch` inputs | `inputs.environment` |

:::warning Expressions are pasted into the script
`${{ }}` substitutes text before the shell runs. If the value comes from a user (a PR title, a branch name, a comment), they can inject shell commands. Pass such values through `env:` and use `"$VAR"` in the script. See [Script injection](security.md#script-injection).
:::

## Passing data

Steps in one job share the file system but not environment variables. Jobs share neither. Use these files and keys:

| To pass | From | To | Use |
|---|---|---|---|
| Files | step | later step, same job | write to the workspace |
| Environment variable | step | later steps, same job | `echo "NAME=value" >> "$GITHUB_ENV"` |
| A value | step | later step | `echo "name=value" >> "$GITHUB_OUTPUT"`, then `steps.<id>.outputs.name` |
| A value | job | dependent job | `jobs.<id>.outputs`, then `needs.<id>.outputs.name` |
| Files | job | another job | `actions/upload-artifact` and `actions/download-artifact` |
| Markdown report | any step | the run's summary page | append to `$GITHUB_STEP_SUMMARY` |

With `GITHUB_ENV`, "the step that creates or updates the environment variable does not have access to the new value, but all subsequent steps in a job will have access."[^github-env] A step output needs an `id` on the step that writes it.[^output]

:::example Pass a value from one job to another
The first job writes a step output and maps it to a job output. The example is from the syntax reference.

```yaml
jobs:
  job1:
    runs-on: ubuntu-latest
    outputs:
      output1: ${{ steps.step1.outputs.test }}
    steps:
      - id: step1
        run: echo "test=hello" >> "$GITHUB_OUTPUT"
  job2:
    runs-on: ubuntu-latest
    needs: job1
    steps:
      - env:
          OUTPUT1: ${{ needs.job1.outputs.output1 }}
        run: echo "$OUTPUT1"
```

`job2` must list `job1` in `needs`, or the `needs` context is empty. Job outputs are capped at "1 MB per job" and 50 MB per run, and outputs containing secrets are dropped.[^out-limits]
:::

## Permissions and secrets

Every job gets an automatic token, `GITHUB_TOKEN`, scoped to the repository. `permissions:` sets what it may do. If you list any permission, "all of those that are not specified are set to `none`."[^perm-none] Set read-only at the top and raise it per job:

```yaml
permissions:
  contents: read
jobs:
  comment:
    permissions:
      contents: read
      pull-requests: write     # needed to comment on or label a PR
```

Secrets you add in the repository settings appear as `${{ secrets.NAME }}`. They are not available to workflows triggered from forks: "With the exception of `GITHUB_TOKEN`, secrets are not passed to the runner when a workflow is triggered from a forked repository."[^fork-secrets]

## Concurrency

`concurrency.group` names a lane; at most one run per lane. A new run waits as `pending`, and with `cancel-in-progress: true` it cancels the running one instead.[^concurrency] Group by `github.ref` for CI (only the latest push per branch matters). For deployments, use a fixed group such as `deploy-production` without `cancel-in-progress`, so a deployment is never cut off halfway.

:::recipes
- Run on pushes to `main` and on every pull request:
  ```yaml
  on:
    push:
      branches: [main]
    pull_request:
  ```

- Run every night at 03:00 UTC:
  ```yaml
  on:
    schedule:
      - cron: '0 3 * * *'
  ```

- Run only when Python files change:
  ```yaml
  on:
    pull_request:
      paths: ['**/*.py', 'requirements*.txt']
  ```

- Run a step only on `main`:
  `if: github.ref == 'refs/heads/main'`

- Always run a cleanup or report step, even after a failure:
  `if: always()`

- Let a step fail without failing the job:
  `continue-on-error: true`

- Stop a hung job after 15 minutes instead of the default 360:
  `timeout-minutes: 15`

- Cancel older runs of the same branch:
  ```yaml
  concurrency:
    group: ${{ github.workflow }}-${{ github.ref }}
    cancel-in-progress: true
  ```
:::

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Workflow doesn't run on a PR that changes only docs | `paths` filter excluded it | Expected; avoid filters on required checks |
| Workflow runs on `push` to a branch and again on its PR | Both `push` and `pull_request` with no branch filter | Limit `push` to `branches: [main]` |
| `python-version: 3.10` installs 3.1 | YAML reads `3.10` as a number | Quote it: `"3.10"` |
| Downstream job silently skipped | A job it `needs` failed or was skipped | Add `if: always()` (or `!cancelled()`) where a report must run anyway |
| `needs.build.outputs.x` is empty | `build` has no `outputs:` map, or the step lacks `id` | Map step output to job output |
| An API call with `GITHUB_TOKEN` fails with a permission error | `permissions` set some keys, so the rest became `none` | Add the specific permission the step needs |
| Manual **Run workflow** button missing | `workflow_dispatch` file is not on the default branch | Merge it to the default branch |
| `if: !contains(...)` is a YAML error | `!` at the start is YAML syntax | Wrap it: `if: ${{ !contains(...) }}` |

## Not covered

- Reusable workflows (`workflow_call`) and composite actions: [Reuse workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows).
- Full event list (issues, releases, comments, `workflow_run`): [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).
- Expression functions (`contains`, `startsWith`, `hashFiles`, `toJSON`): [Expressions](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions).
- Services (database containers for tests), `container:`, `defaults`: [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).
- Caching beyond `setup-*` actions: [Dependency caching reference](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching).

## Check yourself

:::recall
A workflow has `on: push: branches: [main]` and `paths: ['src/**']`. Does a push to `main` that only changes `README.md` run it?
: No. Branch and path filters must both match.[^and]
Which three `pull_request` activity types run a workflow by default?
: `opened`, `synchronize` and `reopened`.[^pr-types]
What code does a `pull_request` run test, by default?
: The merge of the PR branch into the target branch.[^merge]
A matrix has `os: [ubuntu, windows]` and `python: [3.11, 3.12, 3.13]`. How many jobs run, and what happens when one fails?
: Six. With the default `fail-fast: true`, the rest are cancelled.[^fail-fast]
A workflow sets `permissions: pull-requests: write`. Can it still read the repository contents?
: No. Listing any permission sets the unlisted ones to `none`; add `contents: read`.[^perm-none]
Step A writes `VERSION=1.2` to `$GITHUB_ENV`. Which steps can read `$VERSION`?
: Only later steps in the same job; not step A itself, and not other jobs.[^github-env]
Why can't a PR from a fork use your `PYPI_TOKEN` secret?
: Secrets other than `GITHUB_TOKEN` are not passed to runs triggered from forks.[^fork-secrets]
:::

[^pr-types]: "By default, a workflow only runs when a `pull_request` event's activity type is `opened`, `synchronize`, or `reopened`." https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request
[^merge]: "Your CI tests run against the merged result, not just the head branch alone" https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#how-the-merge-branch-affects-your-workflow
[^cron]: "Scheduled workflows run on the latest commit on the default branch. The shortest interval you can run scheduled workflows is once every 5 minutes." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onschedule
[^cron-60]: "In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days." https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
[^dispatch]: "This trigger only receives events when the workflow file is on the default branch." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onworkflow_dispatch
[^and]: "If you define both `branches`/`branches-ignore` and `paths`/`paths-ignore`, the workflow will only run when both filters are satisfied." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onpushpull_requestpull_request_targetpathspaths-ignore
[^paths]: "You cannot use both the `paths` and `paths-ignore` filters for the same event in a workflow." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onpushpull_requestpull_request_targetpathspaths-ignore
[^needs]: "If a job fails or is skipped, all jobs that need it are skipped unless the jobs use a conditional expression that causes the job to continue." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idneeds
[^bang]: "when the expression starts with `!`, since `!` is reserved notation in YAML format." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idif
[^matrix-max]: "A matrix will generate a maximum of 256 jobs per workflow run." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idstrategymatrix
[^fail-fast]: "GitHub will cancel all in-progress and queued jobs in the matrix if any job in the matrix fails. This property defaults to `true`." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idstrategyfail-fast
[^github-env]: "The step that creates or updates the environment variable does not have access to the new value, but all subsequent steps in a job will have access." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#setting-an-environment-variable
[^output]: "Note that the step will need an `id` to be defined to later retrieve the output value." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#setting-an-output-parameter
[^out-limits]: "Outputs can be a maximum of 1 MB per job. The total of all outputs in a workflow run can be a maximum of 50 MB." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idoutputs
[^perm-none]: "If you specify the access for any of these permissions, all of those that are not specified are set to `none`." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions
[^fork-secrets]: "With the exception of `GITHUB_TOKEN`, secrets are not passed to the runner when a workflow is triggered from a forked repository." https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request
[^concurrency]: "To also cancel any currently running job or workflow in the same concurrency group, specify `cancel-in-progress: true`." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency
[^pending]: "then checks associated with that workflow will remain in a ... state. A pull request that requires those checks to be successful will be blocked from merging." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onpushpull_requestpull_request_targetpathspaths-ignore
