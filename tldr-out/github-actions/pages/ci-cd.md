---
title: CI/CD from zero
source: https://docs.github.com/en/actions/get-started/continuous-integration
fetched: 2026-11-11
summary: What continuous integration and continuous deployment are, what problem they solve, and what a pipeline does on every push.
group: Basics
---

**Continuous integration** (CI) means that every change pushed to a shared repository is built and tested automatically, so a mistake shows up minutes after it is made, not weeks later. **Continuous deployment** (CD) extends the same automation past the tests: once a change passes, a machine publishes or deploys it. Together they are written CI/CD. A *pipeline* is the sequence of automated steps (install, lint, test, build, deploy) that runs on every change. GitHub Actions is one system that runs such pipelines, next to your code on GitHub.

:::infobox
Stands for: Continuous integration / continuous deployment (or delivery)
CI answers: "Does this change break anything?"
CD answers: "Can this change reach users without manual work?"
Runs on: A server (a *runner*), not your laptop
Triggered by: A push, a pull request, a schedule or a button
Result: A pass or fail mark on the commit or pull request
Next: [How GitHub Actions works](github-actions.md)
:::

## The problem CI solves

Picture a team of five working without CI. Each person works on a branch for two weeks, runs the tests they remember to run, and merges. On merge day, the branches conflict, the tests that nobody ran fail, and nobody knows which of 80 commits broke them. The fix is slow because the cause is buried.

CI shrinks the gap between making a mistake and learning about it. GitHub's definition puts it this way: committing code often "detects errors sooner and reduces the amount of code a developer needs to debug when finding the source of an error."[^ci-why] If the tests run on every push, a failure points at one small change.

The second idea is that the checks run on a neutral machine. "Building and testing your code requires a server."[^server] A clean server has no leftover files, no globally installed tools you forgot about and no uncommitted changes, so "works on my machine" stops being an answer.

:::background Vocabulary used on every page
**Repository**: the project's Git history on GitHub. **Commit**: one saved change. **Branch**: a line of commits, such as `main` or `fix-login`. **Push**: sending commits to GitHub. **Pull request** (PR): a request to merge one branch into another, where teammates review the change. **Merge**: combining the branch into the target.

**Linter**: a program that checks style and common mistakes without running the code (Ruff for Python, ESLint for TypeScript). **Unit test**: code that calls your code and checks the result (pytest, Vitest, Jest). **Build**: turning source into what you ship, such as compiling TypeScript to JavaScript or making a Python wheel. **Artifact**: a file a pipeline produces and keeps, such as a test report or a built package.

**Exit code**: the number a program returns when it ends. `0` means success; anything else means failure. CI systems decide pass or fail from exit codes, so a test runner that exits `1` fails the pipeline.
:::

## What a pipeline does

```flow A typical pipeline: each stage runs only if the one before it passed
Push or pull request : the trigger
Install : dependencies from the lock file
Check : lint, type-check, tests, security scans
Build : package or bundle
Deploy : only on `main`, often with approval
```

The CI part is everything up to and including the checks. GitHub's CI page lists what those checks commonly include: "code linters (which check style formatting), security checks, code coverage, functional tests, and other custom checks."[^checks] The result is reported back where people are already looking: GitHub "provides the results of each test in the pull request, so you can see whether the change in your branch introduces an error."[^pr-results]

The CD part runs after the checks. GitHub defines continuous deployment as "the practice of using automation to publish and deploy software updates", with the code "automatically built and tested before deployment."[^cd] Most teams deploy only from the main branch, after a pull request is merged, while CI runs on every branch and every pull request.

### Delivery or deployment

The "D" is used two ways. *Continuous delivery* means every passing change is ready to release, and a person presses the button. *Continuous deployment* means the release happens automatically. GitHub Actions supports both: environments can "require approval for a job to proceed", which turns automatic deployment into delivery with a human gate.[^approval]

## Where GitHub Actions fits

Without a hosted service, you would run your own CI server (Jenkins is a common example) and connect it to GitHub with webhooks. GitHub Actions removes that setup: the pipeline definition is a YAML file in your repository, and GitHub supplies the machines. Workflows "can run on GitHub-hosted virtual machines, or on machines that you host yourself."[^runners]

CI and CD are practices, and GitHub Actions is a tool for them. The same YAML file that runs tests can also label issues, post comments on pull requests or audit dependencies, which is why the rest of this bundle treats Actions as a general automation system that happens to be good at CI.

| Practice | Runs when | Typical steps | Failure means |
|---|---|---|---|
| CI | Every push and pull request | install, lint, test, build | Don't merge yet |
| Continuous delivery | Merge to `main` | build, package, wait for approval | Release is blocked |
| Continuous deployment | Merge to `main` | build, deploy, smoke test | Production was not updated |
| PR audit | Every pull request | scan diff, dependencies, code | Reviewer sees annotations or a failed check |

:::exercise Read a real pipeline
1. Open any active open-source project you use on GitHub, such as your web framework or test runner.
2. Open the `.github/workflows/` directory and pick the file whose name mentions CI or test.
3. Find the `on:` line, the job names under `jobs:`, and the `run:` lines.

Check: you can name the event that starts it, the jobs it runs, and the test command each job calls.

Variation: open the project's **Actions** tab, pick a failed run, and find the step whose exit code failed it.
:::

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| CI is green but the app is broken | The tests don't cover what broke; CI only runs what you tell it to | Add a test for the bug before fixing it |
| Everyone ignores red builds | A test fails at random ("flaky") so failures stop meaning anything | Fix or quarantine flaky tests at once |
| Pipeline takes 30 minutes, people stop waiting for it | Everything reinstalls on every run, tests run one after another | Cache dependencies, run jobs in parallel ([Writing workflows](workflows.md)) |
| A deployment ran from a feature branch | The deploy job has no branch condition | Deploy only on `push` to `main`, or use an environment with protection |

## Not covered

- Deployment strategies (blue-green, canary, rollbacks) are outside GitHub's Actions docs; see [Deploying with GitHub Actions](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments).
- Environments and approval rules: [Managing environments for deployment](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).
- Deploying to cloud providers without stored passwords: [OpenID Connect](https://docs.github.com/en/actions/concepts/security/openid-connect).

## Check yourself

:::recall
Why does running tests on every push make bugs cheaper to fix?
: The failure points at one small change instead of weeks of commits, so there is little code to search.[^ci-why]
Why run the checks on a server instead of trusting a local test run?
: A fresh machine has no leftover state, so it catches missing dependencies and uncommitted files.
What decides whether a pipeline step passed?
: The exit code of the command: `0` passes, anything else fails.
What is the difference between continuous delivery and continuous deployment?
: Delivery keeps every passing change ready and a person releases it; deployment releases automatically.
Where does a developer see CI results on GitHub?
: On the pull request, as checks that pass or fail.[^pr-results]
:::

[^ci-why]: "Committing code more often detects errors sooner and reduces the amount of code a developer needs to debug when finding the source of an error." https://docs.github.com/en/actions/get-started/continuous-integration#about-continuous-integration
[^server]: "Building and testing your code requires a server." https://docs.github.com/en/actions/get-started/continuous-integration#about-continuous-integration
[^checks]: "Your tests can include code linters (which check style formatting), security checks, code coverage, functional tests, and other custom checks." https://docs.github.com/en/actions/get-started/continuous-integration#about-continuous-integration
[^pr-results]: "GitHub runs your CI tests and provides the results of each test in the pull request, so you can see whether the change in your branch introduces an error." https://docs.github.com/en/actions/get-started/continuous-integration#about-continuous-integration-using-github-actions
[^cd]: "the practice of using automation to publish and deploy software updates. As part of the typical CD process, the code is automatically built and tested before deployment." https://docs.github.com/en/actions/get-started/continuous-deployment#about-continuous-deployment
[^approval]: "you can use environments to require approval for a job to proceed, restrict which branches can trigger a workflow, or limit access to secrets." https://docs.github.com/en/actions/get-started/continuous-deployment#about-continuous-deployment-using-github-actions
[^runners]: "Workflows can run on GitHub-hosted virtual machines, or on machines that you host yourself." https://docs.github.com/en/actions/get-started/continuous-integration#about-continuous-integration-using-github-actions
