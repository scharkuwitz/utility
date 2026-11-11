---
title: How GitHub Actions works
source: https://docs.github.com/en/actions/get-started/understand-github-actions
fetched: 2026-11-11
summary: Events start workflows; workflows hold jobs; each job gets a fresh runner and runs its steps in order.
group: Basics
---

**GitHub Actions** is GitHub's built-in automation system. You commit a YAML file under `.github/workflows/`, and GitHub runs it on its own machines whenever something happens in the repository: a push, a pull request, a new issue, a schedule. GitHub describes it as "a continuous integration and continuous delivery (CI/CD) platform that allows you to automate your build, test, and deployment pipeline."[^what] Use it to test every pull request, deploy merged code, and automate repository chores such as labeling issues or auditing changes.

:::infobox
Kind: Hosted CI/CD and automation service
Config: YAML files in `.github/workflows/`
Runs on: GitHub-hosted Linux, Windows or macOS VMs, or your own machines
Unit of work: workflow, then job, then step
Reusable pieces: actions, such as `actions/checkout`
Results: Actions tab, and checks on commits and pull requests
## Limits
Job timeout default: 360 minutes[^timeout]
Matrix: 256 jobs per run[^matrix-max]
Schedule: at most every 5 minutes[^cron-min]
Related: [Writing workflows](workflows.md), [Workflow security](security.md)
:::

## How it works

Five nouns describe the whole system. GitHub's own summary: a **workflow** is triggered when an **event** occurs; it "contains one or more jobs which can run in sequential order or in parallel"; each **job** runs on its own **runner** and "has one or more steps that either run a script that you define or run an action."[^components]

```nest What contains what: a workflow file holds jobs; each job holds steps
Workflow : `.github/workflows/ci.yml`, started by an event
  Job `lint` : own runner (VM)
    Step : `uses: actions/checkout@v6`
    Step : `run: ruff check`
  Job `test` : own runner (VM)
    Step : `uses: actions/checkout@v6`
    Step : `run: pytest`
```

Event
: Something that happened, such as `push`, `pull_request` or `schedule`. "An event is a specific activity in a repository that triggers a workflow run."[^event]

Workflow
: One YAML file. A repository can have many, each with its own triggers. Workflows "will run when triggered by an event in your repository, or they can be triggered manually, or at a defined schedule."[^workflow]

Job
: A group of steps that share one machine. By default "jobs have no dependencies and run in parallel"; `needs:` makes one job wait for another.[^parallel]

Step
: One command (`run:`) or one action (`uses:`). Steps in a job run in order, and since they share the runner, "you can share data from one step to another."[^steps]

Action
: A packaged, reusable step written by GitHub or anyone else, referenced as `owner/repo@version`. Typical uses: check out the code, install a language, log in to a cloud.[^action]

Runner
: The machine. "Each runner can run a single job at a time" and "each workflow run executes in a fresh, newly-provisioned virtual machine."[^runner]

### The consequences that matter

The model predicts most of what surprises newcomers:

1. **A runner starts empty.** It does not have your code until a step checks it out. That is why almost every job starts with `actions/checkout`.
2. **Jobs don't share files.** Two jobs are two machines. To pass a build from `build` to `deploy`, upload it as an artifact or recompute it. Steps within one job share files freely.
3. **Steps don't share environment variables.** Each step "runs in its own process", so "changes to environment variables are not preserved between steps."[^own-process] Use the `GITHUB_ENV` and `GITHUB_OUTPUT` files instead ([Writing workflows](workflows.md#passing-data)).
4. **A failing step fails the job**, and a failing job fails the run. A job that `needs:` a failed job is skipped.[^needs]
5. **The workflow file is code in the repository.** It is reviewed in pull requests, versioned with the code, and can be changed by anyone who can push. This matters for security ([Workflow security](security.md)).

```sequence What happens when you open a pull request
You -> GitHub: open PR (event `pull_request`)
GitHub -> GitHub: find workflows with `on: pull_request`
GitHub -> Runner: start a fresh VM per job
Runner -> Runner: checkout, install, test
Runner --> GitHub: exit codes and logs
GitHub --> You: check passes or fails on the PR
```

## By example

:::example The quickstart workflow, annotated
This is GitHub's quickstart workflow with the emoji removed. Create the file in the repository. GitHub only looks in one directory: "you must save the workflow files in a directory called `.github/workflows`."[^dir] Any file name works if it ends in `.yml` or `.yaml`.

```yaml .github/workflows/github-actions-demo.yml
name: GitHub Actions Demo
run-name: ${{ github.actor }} is testing out GitHub Actions
on: [push]
jobs:
  Explore-GitHub-Actions:
    runs-on: ubuntu-latest
    steps:
      - run: echo "The job was automatically triggered by a ${{ github.event_name }} event."
      - run: echo "This job is now running on a ${{ runner.os }} server hosted by GitHub!"
      - run: echo "The name of your branch is ${{ github.ref }} and your repository is ${{ github.repository }}."
      - name: Check out repository code
        uses: actions/checkout@v6
      - name: List files in the repository
        run: |
          ls ${{ github.workspace }}
      - run: echo "This job's status is ${{ job.status }}."
```

Read it top down. `on: [push]` is the event. `jobs:` holds one job whose ID is `Explore-GitHub-Actions`. `runs-on: ubuntu-latest` asks for a GitHub-hosted Linux VM. Each `-` under `steps:` is one step: most are `run:` shell commands, one is `uses:` an action.

`${{ ... }}` is an **expression**. GitHub replaces it with a value before the shell sees the line. `github.actor`, `github.ref` and `runner.os` come from **contexts**, objects describing the run. The `ls` step runs after `actions/checkout`, so it lists your repository's files.

Commit the file. "Committing the workflow file to a branch in your repository triggers the `push` event and runs your workflow."[^commit] Open the **Actions** tab, pick the workflow, then the run, then the job, and expand each step to read its log.
:::

:::exercise Run your first workflow
1. In any repository you own, create `.github/workflows/github-actions-demo.yml` with the content above (use **Add file**, **Create new file** in the GitHub web UI).
2. Commit it to a new branch.
3. Open the **Actions** tab and click the run.

Check: the job log shows `The job was automatically triggered by a push event.` and the `ls` step lists your files.

Variation: change `on: [push]` to `on: [pull_request]`, open a pull request from the branch, and find the run under the pull request's **Checks** tab.
:::

## Reference

| Concept | Where it lives | Scope |
|---|---|---|
| Workflow | `.github/workflows/*.yml` | One per file |
| Event | `on:` | Starts the workflow |
| Job | `jobs.<job_id>` | One runner each; parallel unless `needs:` |
| Step | `jobs.<job_id>.steps[*]` | Sequential; shares files with the job's other steps |
| Action | `uses: owner/repo@ref` | One step |
| Runner | `runs-on:` | `ubuntu-latest`, `windows-latest`, `macos-latest`, or a self-hosted label |
| Expression | `${{ ... }}` | Evaluated by GitHub before the step runs |

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Workflow never runs | File is not in `.github/workflows/`, or the extension is not `.yml`/`.yaml` | Move or rename it |
| Step can't find your files | No checkout step; the runner starts empty | Add `- uses: actions/checkout@v6` first |
| `deploy` job can't find the `dist/` folder built in `build` | Jobs run on separate machines | Upload and download an artifact, or build in the same job |
| `export FOO=1` in one step, empty in the next | Each step is a new process | Write `FOO=1` to `$GITHUB_ENV` |
| No **Actions** tab | Actions is disabled for the repository[^disabled] | Enable it in the repository settings |

## Not covered

- Self-hosted and larger runners: [Self-hosted runners](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners).
- Writing your own actions: [Custom actions](https://docs.github.com/en/actions/concepts/workflows-and-actions/custom-actions).
- Agentic workflows written in natural language: [Creating GitHub Agentic Workflows](https://docs.github.com/en/copilot/how-tos/github-agentic-workflows/creating-github-agentic-workflows).
- Billing and minute limits: [Billing and usage](https://docs.github.com/en/actions/concepts/billing-and-usage).

## Check yourself

:::recall
Two jobs in the same workflow both need the source code. How many checkout steps do you need, and why?
: Two. Each job runs on its own fresh runner, which starts empty.[^runner]
Jobs `lint` and `test` have no `needs:`. In what order do they run?
: In parallel; jobs have no dependencies by default.[^parallel]
A step runs `export TOKEN=abc`. Why is `$TOKEN` empty in the next step?
: Each step runs in its own process, so environment changes don't carry over.[^own-process]
What is the difference between `run:` and `uses:`?
: `run:` executes a shell command; `uses:` runs a packaged action.
When does `${{ github.ref }}` get its value?
: GitHub evaluates the expression before the step's shell runs, and substitutes the text.
:::

[^what]: "GitHub Actions is a continuous integration and continuous delivery (CI/CD) platform that allows you to automate your build, test, and deployment pipeline." https://docs.github.com/en/actions/get-started/understand-github-actions#overview
[^components]: "Your workflow contains one or more jobs which can run in sequential order or in parallel. Each job will run inside its own virtual machine runner, or inside a container" https://docs.github.com/en/actions/get-started/understand-github-actions#the-components-of-github-actions
[^event]: "An event is a specific activity in a repository that triggers a workflow run." https://docs.github.com/en/actions/get-started/understand-github-actions#events
[^workflow]: "will run when triggered by an event in your repository, or they can be triggered manually, or at a defined schedule."  https://docs.github.com/en/actions/get-started/understand-github-actions#workflows
[^parallel]: "by default, jobs have no dependencies and run in parallel. When a job takes a dependency on another job, it waits for the dependent job to complete before running." https://docs.github.com/en/actions/get-started/understand-github-actions#jobs
[^steps]: "Since each step is executed on the same runner, you can share data from one step to another." https://docs.github.com/en/actions/get-started/understand-github-actions#jobs
[^action]: "An action is a pre-defined, reusable set of jobs or code that performs specific tasks within a workflow" https://docs.github.com/en/actions/get-started/understand-github-actions#actions
[^runner]: "Each runner can run a single job at a time." https://docs.github.com/en/actions/get-started/understand-github-actions#runners
[^own-process]: "Because steps run in their own process, changes to environment variables are not preserved between steps." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idsteps
[^needs]: "If a job fails or is skipped, all jobs that need it are skipped unless the jobs use a conditional expression that causes the job to continue." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idneeds
[^dir]: "For GitHub to discover any GitHub Actions workflows in your repository, you must save the workflow files in a directory called `.github/workflows`." https://docs.github.com/en/actions/get-started/quickstart#creating-your-first-workflow
[^commit]: "Committing the workflow file to a branch in your repository triggers the `push` event and runs your workflow." https://docs.github.com/en/actions/get-started/quickstart#creating-your-first-workflow
[^disabled]: "it may be because Actions is disabled for the repository." https://docs.github.com/en/actions/get-started/quickstart#prerequisites
[^timeout]: "The maximum number of minutes to let a job run before GitHub automatically cancels it. Default: 360" https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idtimeout-minutes
[^matrix-max]: "A matrix will generate a maximum of 256 jobs per workflow run." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idstrategymatrix
[^cron-min]: "The shortest interval you can run scheduled workflows is once every 5 minutes." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onschedule
