---
title: Workflow security
source: https://docs.github.com/en/actions/reference/security/secure-use
fetched: 2026-11-11
summary: Least-privilege tokens, script injection, the pull_request_target trap, secrets in logs, and pinning third-party actions.
group: Auditing and security
---

A workflow runs code with credentials: the automatic `GITHUB_TOKEN`, plus any secrets you add. Anything that can change what that code does can use those credentials. The main risks come from four mistakes: tokens with more permission than needed, untrusted text pasted into shell scripts (**script injection**), running a pull request's code under the privileged **`pull_request_target`** trigger, and third-party actions referenced by a tag that someone can move. Read this page before writing any workflow that handles pull requests from people outside your team, which includes every audit workflow on a public repository.

:::infobox
Default stance: `permissions: contents: read` at the top
Untrusted input: PR title, body, branch name, comments, commit messages
Safe for fork PRs: `pull_request`
Dangerous with PR code: `pull_request_target`, `workflow_run`
Pin actions to: full commit SHA, or a lockfile
Mask a value: `::add-mask::VALUE`
Main article: [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)
Related: [Auditing code and pull requests](pr-auditing.md)
:::

## How it works

Security in Actions comes down to one question per workflow: **whose code runs, and with which credentials?**

```stack Trust decreases downward; never let a lower row's input run with a higher row's credentials
^ more trusted
* Workflow file on the default branch : what `pull_request_target` and `schedule` run
Code in branches of your own repository : `push`, `pull_request` from same-repo branches
Pull request from a fork : `pull_request` runs it with a read-only token and no secrets
Text in events : titles, branch names, comments; anyone can write them
```

The `pull_request` trigger handles forks safely by default. For fork PRs, "the `GITHUB_TOKEN` has read-only permissions"[^fork-token] and other secrets "are not passed to the runner".[^fork] The fork's code runs, but it has nothing worth stealing.

The `pull_request_target` trigger is the opposite trade. It "runs in the context of the default branch of the base repository", so the workflow file comes from your trusted branch, and it can "label or comment on pull requests from forks."[^prt] It also gets a read/write token, "even when it is triggered from a public fork."[^prt-token] That is safe only as long as the workflow never runs the PR's code.

```sequence A "pwn request": pull_request_target plus checkout of the PR head
Attacker -> GitHub: fork PR with a malicious install script
GitHub -> Runner: start privileged run (secrets, write token)
Runner -> Runner: check out PR head, npm install
Runner --> Attacker: secrets and token sent out
note Runner: trusted workflow, untrusted code
```

GitHub's warning is direct: these triggers, "when used with the checkout of an untrusted pull request, expose the repository to security compromises" and "can be exploited to take over a repository."[^pwn]

## Least privilege for the token

Every job gets a `GITHUB_TOKEN`, and actions can read it from the `github.token` context "even if the workflow does not explicitly pass the `GITHUB_TOKEN` to the action."[^implicit] So every third-party action in a job holds whatever that job's token can do. GitHub recommends setting the default "to read access only for repository contents" and raising it per job.[^least]

```yaml
permissions:
  contents: read            # every job starts here

jobs:
  label:
    permissions:
      contents: read
      pull-requests: write  # only this job may label or comment
```

Listing any permission sets every unlisted one to `none`.[^perm-none] The token expires when the job finishes, or after 24 hours at most.[^expiry]

## Script injection

`${{ }}` expressions are replaced with text *before* the shell runs. If that text comes from an attacker, it becomes part of your script.

:::example Injection, and the fix
The following step is **vulnerable**. It pastes the PR title into the script text.

```yaml
# Vulnerable: do not copy
- run: echo "Checking title: ${{ github.event.pull_request.title }}"
```

A PR titled `"; echo INJECTED; echo "` closes the string. After substitution the shell sees three commands, and the middle one is the attacker's. Simulated locally in bash, standing in for the runner:

```console
$ bash -c 'echo "Checking title: "; echo INJECTED; echo ""'
Checking title: 
INJECTED

```

The fix is an intermediate environment variable. The value "is stored in memory and used as a variable, and doesn't interact with the script generation process."[^env-fix] Quote it in the script.

```yaml
- env:
    TITLE: ${{ github.event.pull_request.title }}
  run: echo "Checking title: $TITLE"
```

The same hostile title is now printed as text:

```console
$ TITLE='"; echo INJECTED; echo "' bash -c 'echo "Checking title: $TITLE"'
Checking title: "; echo INJECTED; echo "
```

GitHub's reference shows the same result in a real run log, for a title of `a"; ls $GITHUB_WORKSPACE"`.[^env-log]
:::

The same applies to Python and TypeScript scripts in `run:`: read untrusted values from `os.environ` or `process.env`, never from text spliced into the command line. Passing the value as an input to an action (`with:`) is also safe, because it is "passed to the action as an argument" rather than used to generate a shell script.[^action-arg]

## Secrets

- **Anyone with write access can read every secret.** "Any user with write access to your repository has read access to all secrets configured in your repository."[^write-read] Keep secrets narrow in scope.
- **Redaction is best effort.** Logs hide exact secret values, so "automatic redaction is not guaranteed" once a value is transformed.[^redaction] Don't store JSON or YAML blobs as one secret: structured data "can cause secret redaction within logs to fail".[^structured] Register derived values (a JWT, a Base64 form) as secrets too, or mask them with `::add-mask::`.[^mask]
- **If a secret reaches a log, rotate it.** Delete the log and rotate the secret.[^rotate]
- **Gate deployment secrets.** Environment secrets with required reviewers are unavailable "until approval is granted by a reviewer."[^env-review]

## Third-party actions

A compromised action "would have access to all secrets configured on your repository, and may be able to use the `GITHUB_TOKEN` to write to the repository."[^third-party] A tag such as `@v3` can be moved to new code by whoever controls the action's repository. In order of strength:

| Method | Looks like | Protection |
|---|---|---|
| Workflow dependency lockfile | lockfile committed with workflows | "the strongest protection available"[^lockfile] |
| Full commit SHA | `uses: actions/checkout@8f4b7f84864484a7bf31766abe9204da3cbe65b3` | Can't be moved; verify the SHA is from the original repository, not a fork[^sha] |
| Tag from a trusted creator | `uses: actions/checkout@v6` | Tag "can be moved or deleted if a bad actor gains access"[^tag] |
| Branch | `uses: some/action@main` | None; changes with every push |

Whatever you pin, "always audit the source code of the action".[^audit-src] Dependabot can keep SHA-pinned actions up to date.

:::recipes
- Make every job read-only unless it opts in:
  ```yaml
  permissions:
    contents: read
  ```

- Use an untrusted value in a script safely:
  ```yaml
  env:
    TITLE: ${{ github.event.pull_request.title }}
  run: echo "$TITLE"
  ```

- Hide a generated credential from logs:
  `echo "::add-mask::$TOKEN_VALUE"`

- Pin an action to a commit:
  `uses: {{owner}}/{{action}}@{{full_40_character_sha}}`

- Find workflows that use `pull_request_target`:
  `grep -rn "pull_request_target" .github/workflows/`

- Find expressions pasted into `run:` scripts (review each hit):
  `grep -rn 'run:.*\${{ *github\.event' .github/workflows/`
:::

## Pull request triggers

| Trigger | Code that runs | Token on fork PRs | Secrets on fork PRs | Use for |
|---|---|---|---|---|
| `pull_request` | Merge of PR into base | Read-only | No | Building, testing and auditing PR code |
| `pull_request_target` | Base branch's workflow | Read/write | Yes | Labeling or commenting, never building the PR |
| `workflow_run` | Default branch's workflow, after another workflow | May be read/write | May have access | Acting on results of a `pull_request` run |

GitHub's guidance: avoid `pull_request_target` unless necessary; "For privilege separation between workflows, `workflow_run` is a better trigger."[^workflow-run] Workflows on either trigger "must not explicitly check out untrusted code", and `workflow_run` workflows should treat artifacts from other workflows with caution.[^no-checkout]

The safe pattern for "audit a fork PR and comment the result": run the audit under `pull_request` (no secrets, read-only), upload the report as an artifact, then post it from a separate `workflow_run` workflow that reads the artifact as data and never executes it.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Audit can't comment on fork PRs, so someone switches it to `pull_request_target` and checks out the PR | Trading safety for write access | Keep the audit on `pull_request`; post from `workflow_run`, or use annotations |
| Secret visible in a log | Value was transformed (Base64, JSON) so redaction didn't match | Rotate it; register derived values as secrets |
| A third-party action updated and broke or changed behavior | Referenced by a tag or branch | Pin to a commit SHA |
| Workflow change by a contributor exfiltrates secrets | Anyone who can push can edit `.github/workflows/` | Protect `.github/workflows/` with `CODEOWNERS` review[^codeowners] |
| `actions/checkout` refuses in a `pull_request_target` workflow | Its built-in protection against checking out untrusted code[^checkout-guard] | Don't opt out; restructure the workflow (see Not covered) |

## Not covered

- Detailed `pull_request_target` hardening and the `actions/checkout` opt-out: [Securely using pull_request_target](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target).
- Cloud credentials without stored secrets: [OpenID Connect](https://docs.github.com/en/actions/concepts/security/openid-connect).
- Self-hosted runner hardening: [Secure use reference § self-hosted runners](https://docs.github.com/en/actions/reference/security/secure-use#hardening-for-self-hosted-runners).
- Workflow lockfiles: [Workflow dependency lockfiles](https://docs.github.com/en/actions/concepts/security/workflow-dependency-lockfiles).
- Build provenance: [Artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations).

## Check yourself

:::recall
Why is `pull_request` safe for PRs from forks?
: The token is read-only and secrets other than `GITHUB_TOKEN` are not passed to the runner.[^fork]
What makes `pull_request_target` dangerous, and when is it still acceptable?
: It runs with a read/write token and secrets. It is acceptable only when it never checks out or runs the PR's code, for example for labeling.[^prt]
Why does moving `${{ github.event.pull_request.title }}` into `env:` stop injection?
: The value becomes a variable in memory instead of text inserted into the generated script.[^env-fix]
An action you use never receives `GITHUB_TOKEN` in `with:`. Can it still use the token?
: Yes, through the `github.token` context; limit the job's `permissions`.[^implicit]
Why is a full commit SHA safer than `@v3`?
: A tag can be moved to different code; a SHA identifies one exact commit.[^tag]
Your audit job needs to comment on fork PRs. What structure keeps it safe?
: Audit under `pull_request`, upload the result as an artifact, comment from a separate `workflow_run` workflow that treats the artifact as data.[^workflow-run]
:::

[^fork]: "With the exception of `GITHUB_TOKEN`, secrets are not passed to the runner when a workflow is triggered from a forked repository." https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request
[^prt]: "This event runs in the context of the default branch of the base repository ... allows your workflow to do things like label or comment on pull requests from forks." https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request_target
[^prt-token]: "the `GITHUB_TOKEN` is granted read/write repository permission, even when it is triggered from a public fork." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions
[^pwn]: "when used with the checkout of an untrusted pull request, expose the repository to security compromises" https://docs.github.com/en/actions/reference/security/secure-use#mitigating-the-risks-of-untrusted-code-checkout
[^implicit]: "An action can access the `GITHUB_TOKEN` through the `github.token` context even if the workflow does not explicitly pass the `GITHUB_TOKEN` to the action." https://docs.github.com/en/actions/tutorials/authenticate-with-github_token#using-the-github_token-in-a-workflow
[^least]: "It's good security practice to set the default permission for the `GITHUB_TOKEN` to read access only for repository contents." https://docs.github.com/en/actions/reference/security/secure-use#use-secrets-for-sensitive-information
[^perm-none]: "If you specify the access for any of these permissions, all of those that are not specified are set to `none`." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions
[^expiry]: "The `GITHUB_TOKEN` expires when a job finishes or after a maximum of 24 hours." https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idtimeout-minutes
[^env-fix]: "the value of the `${{ github.event.pull_request.title }}` expression is stored in memory and used as a variable, and doesn't interact with the script generation process." https://docs.github.com/en/actions/reference/security/secure-use#use-an-intermediate-environment-variable
[^env-log]: "In this example, the attempted script injection is unsuccessful, which is reflected by the following lines in the log" https://docs.github.com/en/actions/reference/security/secure-use#use-an-intermediate-environment-variable
[^action-arg]: "the context value is not used to generate a shell script, but is instead passed to the action as an argument" https://docs.github.com/en/actions/reference/security/secure-use#use-an-action-instead-of-an-inline-script
[^write-read]: "Any user with write access to your repository has read access to all secrets configured in your repository." https://docs.github.com/en/actions/reference/security/secure-use#use-secrets-for-sensitive-information
[^redaction]: "Because there are multiple ways a secret value can be transformed, automatic redaction is not guaranteed." https://docs.github.com/en/actions/reference/security/secure-use#use-secrets-for-sensitive-information
[^structured]: "Structured data can cause secret redaction within logs to fail, because redaction largely relies on finding an exact match for the specific secret value." https://docs.github.com/en/actions/reference/security/secure-use#use-secrets-for-sensitive-information
[^mask]: "Mask all sensitive information that is not a GitHub secret by using `::add-mask::VALUE`." https://docs.github.com/en/actions/reference/security/secure-use#use-secrets-for-sensitive-information
[^rotate]: "If an unredacted secret is sent to a workflow run log, you should delete the log and rotate the secret." https://docs.github.com/en/actions/reference/security/secure-use#use-secrets-for-sensitive-information
[^env-review]: "A workflow job cannot access environment secrets until approval is granted by a reviewer." https://docs.github.com/en/actions/reference/security/secure-use#use-secrets-for-sensitive-information
[^third-party]: "that compromised action would have access to all secrets configured on your repository, and may be able to use the `GITHUB_TOKEN` to write to the repository." https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions
[^lockfile]: "This is the strongest protection available, and supersedes SHA pinning for repositories that adopt it." https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions
[^sha]: "When selecting a SHA, you should verify it is from the action's repository and not a repository fork." https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions
[^tag]: "a tag can be moved or deleted if a bad actor gains access to the repository storing the action." https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions
[^audit-src]: "Regardless of your measures, always audit the source code of the action." https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions
[^workflow-run]: "For privilege separation between workflows, `workflow_run` is a better trigger." https://docs.github.com/en/actions/reference/security/secure-use#good-practices
[^no-checkout]: "Workflows that use these triggers must not explicitly check out untrusted code, including from pull request forks or from repositories that are not under your control." https://docs.github.com/en/actions/reference/security/secure-use#good-practices
[^checkout-guard]: "opting out of the `actions/checkout` protection" https://docs.github.com/en/actions/reference/security/secure-use#mitigating-the-risks-of-untrusted-code-checkout
[^codeowners]: https://docs.github.com/en/actions/reference/security/secure-use#using-codeowners-to-monitor-changes (Secure use reference § Using CODEOWNERS to monitor changes)
[^fork-token]: "The `GITHUB_TOKEN` has read-only permissions in pull requests from forked repositories." https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request
