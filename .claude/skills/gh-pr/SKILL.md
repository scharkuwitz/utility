---
name: gh-pr
description: Open a GitHub pull request for the current branch with the gh CLI, written for the reviewer. Use when the user wants to open, create, submit or raise a PR or pull request, "send this upstream", or "push and open a PR", optionally with their own description of the problem the change solves. Checks branch state and existing PRs, reads the actual diff, follows the repository's PR template and title convention, links issues correctly, reports only testing that really happened, and verifies the result.
argument-hint: "[why / the problem it fixes, in your own words] [#issue] [--base BRANCH] [--draft] [--reviewer a,b] [--repo owner/repo] [--dry-run]"
---

# gh-pr

Open a pull request whose title and description let a reviewer who has never seen this code understand what changed, why, and how it was checked. The user's words explain the motivation; the diff is the source of truth for what changed. `<skill>` is this skill's base directory.

## Arguments

`$ARGUMENTS` is free text. Extract:

| Input | Default |
|---|---|
| Motivation: the complaint or problem the change addresses | This conversation, then commit messages. Never invented. |
| Linked issue: `#N`, `owner/repo#N` or an issue URL | Issue refs the context script finds in the branch name and commits |
| `--base BRANCH` | The target repository's default branch |
| `--repo owner/repo` | The upstream parent for a fork, else this repository |
| `--draft` | Ready for review. Also use draft when checks fail or the user says it is unfinished. |
| `--reviewer a,b`, `--label NAME` | None. GitHub requests CODEOWNERS reviews automatically; do not add them yourself. |
| `--dry-run` | Write the draft and stop before pushing |

## Workflow

1. **Context in one call**: `python3 <skill>/scripts/pr_context.py [--base B] [--repo R]`. It prints the branch, uncommitted files, the upstream, the target repository and base, commits ahead and behind, the diffstat, issue refs, any existing PR for the branch, recent merged PR titles, the PR template (read from the base branch), and where CONTRIBUTING and CODEOWNERS live.
2. **Resolve the branch state.** Fix what is safe; ask about the rest.
   - Existing **open** PR for this branch: stop and give its URL. Offer to update it (`gh pr edit`) instead.
   - Uncommitted changes: list them and ask once whether they belong in this PR. If yes, commit them in the repository's commit style (see `git log`), with the session's commit attribution trailer if one is configured.
   - On the base branch: create a topic branch (`git switch -c <type>/<short-slug>`, using the issue number when there is one). Leave the local base branch alone and mention it if it is now ahead of the remote.
   - No commits ahead of the base: stop. If the user described a problem but nothing was changed yet, say so and offer to implement the fix first.
   - Far behind the base, or the diffstat shows files the user did not touch: report it; do not rebase or force-push without being asked.
   - Check the diff for secrets, `.env` files, large binaries or local-only debug code before anything is pushed.
3. **Understand the change.** Read the commits, then the diff of the files that carry the behavior (`git diff <base-ref>...HEAD -- <path>`); read the full diff only when it is small. Generated files, lockfiles and snapshots need only a mention. Name the problem, the approach, and anything a reviewer would otherwise have to guess.
4. **Testing evidence.** Collect what was actually run in this session or reported by the user: commands and what was observed. If the project has a fast, relevant check (the test file for the changed module, the linter) and it was not run, run it now. Never present planned or expected results as testing. If nothing was exercised, write "Not tested" and why.
5. **Title**: copy the convention visible in the recent merged titles (Conventional Commits `fix(scope): ...`, or sentence-case imperative, or a component prefix). Imperative, specific, at most about 70 characters, describing the change rather than the files: `Fix base branch detection for forks`, not `Update create.go`.
6. **Body**, written to `<scratchpad>/pr-<branch>.md` with the Write tool (heredocs break on backticks).
   - **With a template**: keep its headings and order; answer each section; delete instructional comments once followed; keep functional markers (for example `<!-- homu-ignore:start -->`). Required checklists and disclosure questions get truthful answers: who wrote it (an AI agent under the user's direction, unless the user wrote the code), and anything only the user can answer (such as who will respond to review comments) is asked, never assumed.
   - **Without a template**:

     ```markdown
     <1-3 sentences: the problem, then what this PR does about it.>

     Closes #N

     ## Changes
     - <behavioral change, not a file list>

     ## Testing
     - I ran `<command>` and saw <result>.

     ## Notes for reviewers
     <Where to start, trade-offs, alternatives rejected, open questions. Omit if empty.>
     ```
   - **Issue links**: `Closes #N` (or `owner/repo#N`) only when merging fully resolves the issue; otherwise `Part of #N` or `Related to #N`. One keyword per issue, each on its own line.
   - End with the session's pull request attribution line if one is configured.
7. **Disclosure review**: read the title, body and branch name as a stranger would. Remove tokens, keys, internal hostnames, private repository or customer names, home-directory paths, and narration of how the PR was produced ("as discussed", "the agent first tried..."). Write as the author, inside the repository's context.
8. **Push and create.**
   - `--dry-run`: show the title and body path and stop.
   - Target repository owned by the viewer, or viewer permission WRITE or higher: proceed.
   - Anyone else's repository (including fork to upstream): show the title, body and diffstat in chat and ask one confirmation question (open / open as draft / edit / cancel). It is public and made under the user's name.
   - Push: `git push -u <remote> <branch>` (for a fork, the fork's remote, normally `origin`).
   - Create: `gh pr create -R <target> --base <base> --head <branch> --title "<title>" --body-file <file>` plus `--draft`, `--reviewer` and permitted `--label` when they apply. From a fork, `--head` is `<fork-owner>:<branch>` (the context script prints it). Never combine `--fill` or `--template` with `--body-file`.
9. **Verify and report**: `gh pr view <url> --json number,url,state,isDraft,baseRefName,headRefName`. Report the URL, base and head, draft state, linked issues, reviewers, and anything not verified (tests not run, template questions left to the user). On a timeout or non-zero exit, do not retry: check `gh pr list -R <target> --head <branch> --state all` first, since the PR may exist.

## Writing rules

- **Problem before solution.** The first lines say why the change exists; a reviewer should not reconstruct it from the diff.
- **Describe behavior, not files.** "Requests now retry on 429 with backoff", not "changed client.go".
- **Small and honest.** No restating the diff line by line, no filler such as "This PR aims to...", "comprehensive", "robust" or "seamlessly", no emoji, no exclamation marks.
- **Facts the reviewer cannot see**: why this approach over the obvious alternative, risk and rollback, follow-ups left out on purpose.
- **Self-contained.** The description may become the merge commit message; it must make sense without this conversation.
