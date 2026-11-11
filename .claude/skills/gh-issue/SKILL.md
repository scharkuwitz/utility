---
name: gh-issue
description: Turn a user's complaint, bug observation or request into a well-formed GitHub issue and file it with the gh CLI. Use when the user wants to file, open, create, report or raise an issue, bug report, feature request or docs problem on a GitHub repository, including "report this upstream" or "open an issue on X about Y". Finds the right repository, checks for duplicates and the security policy, fills the repository's own issue template, gathers evidence instead of inventing it, and verifies the posted result.
argument-hint: "[owner/repo | repo URL] <complaint in your own words> [--type bug|feature|docs|question] [--label NAME] [--image PATH] [--dry-run]"
---

# gh-issue

Rewrite the user's complaint into an issue that a maintainer can triage in one read: what is wrong, how to see it, what was expected, and the environment. The user's words are input, not the issue text. `<skill>` is this skill's base directory.

## Arguments

`$ARGUMENTS` is free text. Extract:

| Input | Source if not given |
|---|---|
| Target repository (`owner/repo` or URL) | The tool the complaint is about (confirm its upstream repo with `gh repo view`), else the current directory's repo. Ask only if still ambiguous. |
| The complaint | Required. If empty, use the problem discussed in this conversation; if there is none, ask. |
| `--type` | Inferred: bug, regression, feature, docs or question. |
| `--label`, `--image PATH` | Optional. Labels need triage permission; images are attached with `--attach`. |
| `--dry-run` | Write the draft and stop before posting. |

## Workflow

1. **Context in one call**: `python3 <skill>/scripts/issue_context.py <repo> --search "<3-5 distinctive terms>"`. It prints the viewer's permission, the security policy location, the issue templates with their title prefixes and labels, the template chooser config (`contact_links`, `blank_issues_enabled`), live labels when the viewer may apply them, and matching issues in all states. Run a second search with different terms (the exact error text, the command name) if the first finds nothing.
2. **Gates.** Stop and tell the user, without posting, when:
   - the repository is archived or has issues disabled;
   - the complaint is a security vulnerability: point to the security policy the script printed;
   - `contact_links` route this kind of request elsewhere (questions to a forum, a sub-tool to another repo): say where, and ask whether to continue;
   - an existing issue already describes the same symptom: show it with one line on why it matches, and ask whether to comment on it (with `gh issue comment`, using the same rules for evidence), file anyway, or stop. Related but different issues are linked from the new issue instead.
3. **Gather evidence, never invent it.** Collect what the template asks for from the environment: tool version (`<tool> --version`), OS (`uname -sr`, `sw_vers`), exact error output, and a minimal reproduction. Re-run the failing command when it is cheap and harmless. Ask the user, in one `AskUserQuestion` batch, only for facts that are both required and unobtainable (for example, the last working version of a regression). Unknown optional facts are left out, not guessed.
4. **Choose the template** that matches the type (prefer a YAML form over a Markdown template when both fit) and print it: `issue_context.py <repo> --template <name>` (use `owner/.github:<name>` for an inherited one). Fill it as described in `references/bodies.md`. Without a template, use the matching skeleton from the same file.
5. **Title**: the template's prefix, then the symptom and its condition, at most about 70 characters. Name the command, component or page. Example: `[BUG] /plugin install fails when the marketplace URL has a trailing slash`. Not: "Bug with plugins", "Please fix", "Feature request: improvements".
6. **Write the body** to `<scratchpad>/issue-<slug>.md` with the Write tool (shell heredocs break on backticks), then run the disclosure review below.
7. **Labels**: when the viewer has triage permission, use the template's labels plus at most two live labels that clearly match; never invent one, and skip maintainer workflow labels (`duplicate`, `good first issue`, `needs triage`, `wontfix`). With READ permission pass no `--label`, `--assignee`, `--type` or `--milestone`: the repository's automation applies template labels.
8. **Post.**
   - `--dry-run`: show the title and body path and stop.
   - Repository owned by the viewer, or viewer permission WRITE or higher: post directly.
   - Anyone else's repository: show the title and full body in chat, then ask one confirmation question (post / edit / cancel). Posting there is public and is made under the user's name.
   - Command: `gh issue create -R <owner/repo> --title "<title>" --body-file <file>` plus permitted `--label` and `--attach '<path>#<alt text>'` flags. Do not combine `--template` with `--body-file`.
9. **Verify and report**: `gh issue view <url> --json number,url,title,labels`. Report the URL, the template used, labels applied or skipped, and any fact you could not verify. On a timeout or non-zero exit, do not retry: first search for the issue (`gh issue list -R <repo> --state all --author @me --search "<title>"`), since creation can succeed before a later step fails.

## Writing rules

- **Lead with the point.** The first sentence states the problem and where it happens. No greeting, thanks, apology or backstory.
- **One problem per issue.** Split a complaint that contains two bugs and say you did.
- **Observed, then expected.** Facts first; the suspected cause, if any, goes last under its own heading and is labeled as a guess.
- **Exact over descriptive.** Commands, error text and output go in fenced code blocks, copied verbatim and trimmed to the relevant lines. Long logs go in `<details><summary>Log</summary> ... </details>`.
- **Minimal reproduction.** Numbered steps from a clean state that anyone can follow. If you could not reproduce it, say so.
- **Neutral and specific.** Turn frustration into facts: "the command exits 0 but writes nothing", not "this is completely broken". No emoji, exclamation marks, "please fix ASAP", or filler such as "seamlessly", "robust" or "it's worth noting".
- **Mirror the repository.** Use its template headings, terminology and register.
- **Disclose honestly.** If the template or contributing guide asks whether AI was used, answer truthfully (drafted by an AI agent from the user's report). If it asks a question only the user can answer, ask the user.

## Disclosure review (before every post)

Read the final title, body and attachments as a stranger would. Remove or redact: tokens, keys, passwords, cookies and auth headers; email addresses and usernames that are not needed; home-directory paths (`/home/<name>/...` becomes `~/...`); private repository, company or customer names; unrelated conversation text. Re-check after any edit.
