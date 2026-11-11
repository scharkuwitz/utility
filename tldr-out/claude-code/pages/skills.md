---
title: Skills
source: https://code.claude.com/docs/en/skills
fetched: 2026-11-11
summary: Folders of instructions that Claude loads when their `description` matches the task, or when you type `/name`.
group: Extending Claude Code
---

:::infobox
Kind: Markdown instructions that Claude Code loads on demand
File: `SKILL.md` in a folder named after the skill
Run it: `/skill-name`, or let Claude load it when relevant
Trigger: the `description` in the front matter[^desc]
Standard: [Agent Skills](https://agentskills.io), plus Claude Code extensions
Replaces: `.claude/commands/*.md` (still supported)
Related: [Plugins](plugins.md), CLAUDE.md, subagents, hooks
## Limits
Listing text: 1,536 characters per skill[^cap]
Listing budget: 1% of the context window[^budget]
After compaction: first 5,000 tokens of each skill, 25,000 in total[^compaction]
Body: under 500 lines (advice)[^500]
:::

:::hatnote This page covers writing and running skills. To package skills with agents, hooks and MCP servers for other people, see [Plugins](plugins.md).

A **skill** is a folder holding a `SKILL.md` file. The file has two parts: YAML front matter that says when to use the skill, and Markdown instructions that Claude follows when it runs.[^two-parts] You can run a skill yourself as `/skill-name`, or Claude can load it on its own when your request matches its description.

Create one when you keep pasting the same instructions, checklist or procedure into chat. Unlike CLAUDE.md, which is in context all the time, a skill's body loads only when it is used, so a long procedure costs almost nothing until you need it.[^cheap]

## How it works

:::main [Extend Claude with skills](https://code.claude.com/docs/en/skills)

Suppose you have thirty skills installed. On every turn, Claude sees a short **listing**: each skill's name and description. That is how it knows what exists. The body of a skill, which may be hundreds of lines, enters the conversation only when the skill is invoked.[^default-load] Everything else about skills follows from this two-stage design: what goes in the description, why bodies can be long, and why too many skills crowd each other out.

```flow A skill costs a line in the listing until it is used; then its whole body joins the conversation
Listing : name and `description` of every skill, on every turn
-> request matches a description
Claude invokes the skill | You type `/skill-name`
Body enters the conversation : arguments and `!` commands already filled in
Claude follows the instructions
```

The `description` is therefore the trigger. Claude uses it "to decide when to apply the skill",[^desc] so it has to contain the words people actually say when they need it. Put the main use case first: the listing truncates each skill's description at 1,536 characters,[^cap] and when you have many skills, Claude Code drops whole descriptions, starting with the skills you invoke least, to stay within a budget of 1% of the context window.[^budget]

### Who can invoke it

By default both you and Claude can invoke any skill. Two front matter fields narrow that, and each has a different effect on what sits in context:

| Front matter | You can run it | Claude can run it | In context before it runs |
|---|---|---|---|
| (neither field) | Yes | Yes | The description |
| `disable-model-invocation: true` | Yes | No | Nothing[^dmi-load] |
| `user-invocable: false` | No | Yes | The description |

Use `disable-model-invocation: true` for anything with side effects, such as deploying, committing or sending messages. The docs' reason: "You don't want Claude deciding to deploy because your code looks ready."[^deploy] Use `user-invocable: false` for background knowledge that makes no sense as a command, such as how a legacy system works.

Where you type the name matters too. `/deploy staging` at the **start** of a message runs the skill. Typed after other words, as in "go ahead and /deploy to staging", the name only gives Claude permission to run it.[^start]

### Once loaded, it stays

When a skill runs, Claude Code renders it and adds the result to the conversation "as a single message", where it stays across later turns.[^lifecycle] Claude Code "does not re-read the skill file on later turns".[^reread] Two consequences follow:

- **Write standing instructions, not one-time steps.** "Run the tests after every edit" keeps working; "Run the tests" is done once and forgotten.
- **Put the important rules first.** When the conversation is compacted, Claude Code re-attaches each invoked skill but keeps only its first 5,000 tokens, within 25,000 tokens for all skills together.[^compaction]

Permissions don't persist the way the text does. An `allowed-tools` grant clears when you send your next message,[^grant] and invoking the skill again grants it again.

### Before Claude reads it: arguments and live data

Claude Code processes the file before Claude sees it. It substitutes arguments, such as `$ARGUMENTS`, `$0` and `$1`, and it runs every line of the form `` !`command` ``, replacing the line with the command's output. "Claude receives actual data, not the command itself."[^inject]

```sequence What happens when you type /fix-issue 123
You -> Claude Code: /fix-issue 123
Claude Code -> Claude Code: $ARGUMENTS becomes 123
Claude Code -> Claude Code: run each !`command`, insert output
Claude Code -> Claude: rendered SKILL.md, one message
note Claude: stays in context; file not re-read
```

This preprocessing is all-or-nothing: "A failed command aborts the entire skill invocation, not just its own placeholder."[^abort] With the default bash shell, any non-zero exit code counts as a failure, except exit code 1 from search and comparison commands.

### Where it lives decides who gets it

The folder a skill sits in decides which sessions load it. Save it under your home directory for every project, commit it to a repository to share it with the team, or ship it in a plugin.

| Location | Path | Loads in |
|---|---|---|
| Personal | `~/.claude/skills/<name>/SKILL.md` | All your projects on this machine, but not Cowork or cloud sessions[^personal] |
| Project | `.claude/skills/<name>/SKILL.md` | Sessions in this repository; commit it for your team |
| Nested | `<subdir>/.claude/skills/<name>/SKILL.md` | Once Claude works on files in `<subdir>` |
| Enterprise | `.claude/skills/` in the managed settings directory | Every user your organization deploys it to |
| Plugin | `<plugin>/skills/<name>/SKILL.md` | Wherever the plugin is enabled, as `/plugin-name:skill-name` |

Claude Code also reads `.claude/skills/` in every parent directory up to the repository root,[^parents] so starting in `packages/frontend/` still picks up skills defined at the root. Skills in subdirectories below where you started load only the first time Claude reads or edits a file there.[^nested]

```stack When two skills share a name, the higher location wins
^ wins
Enterprise : managed settings directory
Personal : `~/.claude/skills/`
Project : `.claude/skills/`
Command file : `.claude/commands/<name>.md` loses to a skill of the same name
```

Plugin skills never collide with these: both load, "because plugin skills are namespaced as `/plugin-name:skill-name`".[^namespace] A skill with the same name as a bundled skill or a built-in command replaces that command, but not its aliases.

### Running in a subagent: `context: fork`

With `context: fork` in the front matter, the skill runs in a new subagent of the type named in `agent` (default `general-purpose`), with the skill's content as its task. "The subagent doesn't see your conversation history, so the skill's instructions have to stand on their own."[^fork] It runs in the background by default and posts its result when done; `background: false` makes the turn wait for it.

:::warning
Fork only skills that contain a task. A skill made of guidelines alone, such as "use these API conventions", gives the subagent nothing to do, and it "returns without meaningful output".[^fork-task]
:::

## By example

:::example A skill that reviews your uncommitted changes
This is the docs' first skill. Personal skills live under your home directory and work in every project.

```console
$ mkdir -p ~/.claude/skills/summarize-changes
```

The front matter holds only a `description`. It names the situations ("what changed", "a commit message", "review their diff") in the words a user would type, so Claude can match them.

The `` !`git diff HEAD` `` line runs before Claude reads the file. Claude receives your actual diff in its place.

```markdown ~/.claude/skills/summarize-changes/SKILL.md
---
description: Summarizes uncommitted changes and flags anything risky. Use when the user asks what changed, wants a commit message, or asks to review their diff.
---

## Current changes

!`git diff HEAD`

## Instructions

Summarize the changes above in two or three bullet points, then list any risks you notice such as missing error handling, hardcoded values, or tests that need updating. If the diff is empty, say there are no uncommitted changes.
```

Test both invocation paths in a git project with a small edit. The first prompt only matches the description; the second names the skill. Either way you should get a short summary of the edit and a list of risks.

```text
What did I change?
/summarize-changes
```
:::

The second example combines features the docs show separately: a task skill that only you can start, takes an argument, and runs its git commands without asking each time.

:::example A task skill: arguments, manual only, pre-approved tools
`disable-model-invocation: true` keeps Claude from committing on its own initiative. `argument-hint` shows in autocomplete. `allowed-tools` pre-approves these git commands for the turn that invokes the skill.

```markdown .claude/skills/commit/SKILL.md
---
name: commit
description: Stage and commit the current changes
disable-model-invocation: true
argument-hint: [message]
allowed-tools: Bash(git add *) Bash(git commit *) Bash(git status *)
---

Commit the current changes.

- Current status: !`git status --short`
- Use "$ARGUMENTS" as the commit message. If it is empty, write one from the diff.
```

Running it puts the argument in place of `$ARGUMENTS`. With no placeholder in the body, Claude Code would append the text as `ARGUMENTS: ...` instead.[^append]

```text
/commit fix the null check in parser
```
:::

## Recipes

:::recipes
- Create a personal skill, available in all your projects:
  `mkdir -p ~/.claude/skills/{{skill_name}}`

- Create a project skill that your team gets through git:
  `mkdir -p .claude/skills/{{skill_name}}`

- Run a skill with arguments:
  `/{{skill_name}} {{arguments}}`

- List the skills Claude can see, by asking it:
  `What skills are available?`

- Find `SKILL.md` files whose front matter doesn't parse:
  `claude plugin validate {{.claude/skills|~/.claude/skills}}`

- Load a new top-level skills directory created during the session:
  `/reload-skills`

- See front matter parse errors and refused skill names:
  `claude --debug`
:::

## Reference

### Front matter you will use

All fields are optional; only `description` is recommended.[^optional] Field names must match exactly, because Claude Code "ignores a field it doesn't recognize without reporting an error."[^unknown]

| Field | What it does | Default |
|---|---|---|
| `name` | The command name in the `/` menu | the folder name |
| `description` | What the skill does and when to use it; the trigger | first paragraph of the body |
| `when_to_use` | Extra trigger phrases, appended to the description and counted in its 1,536 characters | none |
| `argument-hint` | Autocomplete hint, such as `[issue-number]` | none |
| `arguments` | Names for positional arguments, used as `$name` | none |
| `disable-model-invocation` | `true`: only you can run it | `false` |
| `user-invocable` | `false`: only Claude can run it | `true` |
| `allowed-tools` | Tools usable without a prompt during the invoking turn | none |
| `context`, `agent` | `fork` runs the skill in a subagent of type `agent` | inline, `general-purpose` |
| `model`, `effort` | Override for the rest of the current turn | the session's |
| `paths` | Globs; Claude loads the skill on its own only for matching files | all files |

### Substitutions

| Write | Becomes |
|---|---|
| `$ARGUMENTS` | Everything typed after the skill name |
| `$0`, `$1` or `$ARGUMENTS[0]` | One argument, counted from 0; quote multi-word values |
| `$issue` | A named argument declared in `arguments` |
| `${CLAUDE_SKILL_DIR}` | The folder that contains this `SKILL.md`[^skill-dir] |
| `${CLAUDE_PROJECT_DIR}` | The project root |
| `${CLAUDE_SESSION_ID}` | The current session ID |
| `` !`command` `` at the start of a line or after a space | The command's output[^inline-rule] |

Write `\$1.00` to keep a literal dollar sign before a digit.

### Supporting files

A skill folder can hold more than `SKILL.md`. Claude reads the extra files only when the instructions point to them, so detailed material costs nothing until needed. Keep `SKILL.md` itself under 500 lines.[^500]

```tree Only SKILL.md is required; link the other files from it so Claude knows when to read them
my-skill/
  SKILL.md          # overview and navigation
  reference.md      # detailed docs, read when needed
  examples.md       # read when needed
  scripts/
    helper.py       # run, not read into context
```

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Claude never uses the skill on its own | The description lacks the words people use, or the YAML is malformed and loads as empty metadata[^malformed] | Rewrite the description around user phrasing; check for parse errors with `claude --debug` |
| Claude uses the skill when you don't want it | The description is too broad | Narrow it, or add `disable-model-invocation: true` |
| Claude follows the skill at first, then stops | The file is not re-read, and compaction keeps only the start | Word rules as standing instructions, put them first, invoke the skill again after compaction |
| A rule must hold every time but sometimes doesn't | Skills are guidance that Claude applies with judgment | Use a hook: it runs "every time its event occurs"[^hook] |
| Some skills stop triggering as you add more | Their descriptions were dropped from the listing to fit the budget | Lead with the main use case; mark rarely used skills `name-only` in `skillOverrides` |
| A front matter setting has no effect | The field name is misspelled and silently ignored | Copy field names from the reference table |
| The `!` command text reaches Claude unrun | `!` is not at the start of a line or after whitespace | Move it, or put the commands in a block opened with ```` ```! ```` |
| The skill fails with `Shell command failed` | An injected command exited non-zero | Fix the command, or append `\|\| true` when non-zero is expected[^or-true] |

:::warning Review `allowed-tools` in repositories you clone
`allowed-tools` grants permissions; it does not restrict tools, since every tool "remains callable".[^not-restrict] Workspace trust doesn't gate the field,[^trust] so a project skill can pre-approve broad commands for itself. Read the skills in a repository before you run Claude Code there.
:::

## Not covered

- **Bundled skills** such as `/doctor`, `/run`, `/verify` and `/claude-api`: see the [commands reference](https://code.claude.com/docs/en/commands).
- **Skills synced from claude.ai** and skills in Cowork and cloud sessions: [Skills synced from claude.ai](https://code.claude.com/docs/en/skills#skills-synced-from-claudeai).
- **Restricting Claude's access to skills** with permission rules and `skillOverrides`: [Restrict Claude's skill access](https://code.claude.com/docs/en/skills#restrict-claudes-skill-access).
- **Evaluating skills** with skill-creator and `claude plugin eval`: [Evaluate and iterate on a skill](https://code.claude.com/docs/en/skills#evaluate-and-iterate-on-a-skill).
- **Administrator settings** such as `disableSkillShellExecution`, `strictPluginOnlyCustomization` and `allowManagedPermissionRulesOnly`.
- **Edge cases**: `shell: powershell`, stacking several skills in one message, nested and added-directory name prefixes, reserved names, and visual output.

## Check yourself

:::recall
What does Claude see about a skill before the skill runs, and why does it matter?
: Only its name and `description`, in the skill listing. The description is the sole basis for Claude choosing the skill, so it must contain the words users actually say.[^desc]

You want Claude never to deploy on its own initiative. Which field do you set, and what else changes?
: `disable-model-invocation: true`. The description also leaves Claude's context, so the skill costs nothing until you run it.[^dmi-load]

A skill tells Claude to run the tests. Ten turns later Claude has stopped running them. Why?
: The skill was added once as a message and the file is not re-read, so a one-time step stays done. Word it as a standing rule ("after every edit"), or use a hook if it must always happen.[^reread]

You have `deploy` in both `~/.claude/skills/` and the project's `.claude/skills/`. Which runs for `/deploy`?
: The personal one: enterprise beats personal, and personal beats project.[^precedence]

Your skill's `` !`npm test` `` fails. What does Claude see?
: Nothing from the skill. A failed command aborts the whole invocation.[^abort]

When is `context: fork` the wrong choice?
: When the skill is guidelines rather than a task, or when the task needs the current conversation. The forked subagent sees neither your history nor an actionable prompt.[^fork]
:::

[^two-parts]: "Every skill needs a `SKILL.md` file with two parts: YAML frontmatter between `---` markers that tells Claude when to use the skill, and markdown content with the instructions Claude follows" https://code.claude.com/docs/en/skills#create-your-first-skill
[^cheap]: "Unlike CLAUDE.md content, a skill's body loads only when it's used, so long reference material costs almost nothing until you need it." https://code.claude.com/docs/en/skills
[^desc]: "Claude uses this to decide when to apply the skill." https://code.claude.com/docs/en/skills#frontmatter-reference
[^cap]: "the combined `description` and `when_to_use` text is truncated at 1,536 characters in the skill listing" https://code.claude.com/docs/en/skills#frontmatter-reference
[^budget]: "The budget scales at 1% of the model's context window." https://code.claude.com/docs/en/skills#skill-descriptions-are-cut-short
[^compaction]: "keeping the first 5,000 tokens of each. Re-attached skills share a combined budget of 25,000 tokens." https://code.claude.com/docs/en/skills#skill-content-lifecycle
[^500]: "Keep `SKILL.md` under 500 lines." https://code.claude.com/docs/en/skills#add-supporting-files
[^default-load]: "Description always in context, full skill loads when invoked" https://code.claude.com/docs/en/skills#control-who-invokes-a-skill
[^dmi-load]: "Description not in context, full skill loads when invoked" https://code.claude.com/docs/en/skills#control-who-invokes-a-skill
[^deploy]: "You don't want Claude deciding to deploy because your code looks ready." https://code.claude.com/docs/en/skills#control-who-invokes-a-skill
[^start]: "To run a skill directly, put its name at the start of your message." https://code.claude.com/docs/en/skills#where-you-write-the-skills-name
[^lifecycle]: "the rendered `SKILL.md` content enters the conversation as a single message and stays there across later turns" https://code.claude.com/docs/en/skills#skill-content-lifecycle
[^reread]: "Claude Code does not re-read the skill file on later turns" https://code.claude.com/docs/en/skills#skill-content-lifecycle
[^grant]: "an `allowed-tools` grant clears when you send your next message" https://code.claude.com/docs/en/skills#skill-content-lifecycle
[^inject]: "The command output replaces the placeholder, so Claude receives actual data, not the command itself." https://code.claude.com/docs/en/skills#inject-dynamic-context
[^abort]: "A failed command aborts the entire skill invocation, not just its own placeholder." https://code.claude.com/docs/en/skills#when-an-injected-command-fails
[^personal]: "All your projects on this machine, but not Cowork or cloud sessions" https://code.claude.com/docs/en/skills#choose-where-skills-load
[^parents]: "Claude Code loads project skills from `.claude/skills/` in the directory where you start it and in every parent directory up to the repository root" https://code.claude.com/docs/en/skills#load-skills-in-monorepos-and-subdirectories
[^nested]: "Skills in a `.claude/skills/` directory below where you started don't load at startup." https://code.claude.com/docs/en/skills#load-skills-in-monorepos-and-subdirectories
[^precedence]: "Enterprise over personal, and personal over project." https://code.claude.com/docs/en/skills#resolve-skills-that-share-a-name
[^namespace]: "Both load, because plugin skills are namespaced as `/plugin-name:skill-name`" https://code.claude.com/docs/en/skills#resolve-skills-that-share-a-name
[^fork]: "The subagent doesn't see your conversation history, so the skill's instructions have to stand on their own." https://code.claude.com/docs/en/skills#run-skills-in-a-subagent
[^fork-task]: "the subagent receives the guidelines but no actionable prompt, and returns without meaningful output" https://code.claude.com/docs/en/skills#run-skills-in-a-subagent
[^append]: "Claude Code appends `ARGUMENTS: <your input>` to the end of the skill content" https://code.claude.com/docs/en/skills#pass-arguments-to-skills
[^optional]: "All fields are optional. Only `description` is recommended so Claude knows when to use the skill." https://code.claude.com/docs/en/skills#frontmatter-reference
[^unknown]: "Claude Code ignores a field it doesn't recognize without reporting an error." https://code.claude.com/docs/en/skills#frontmatter-reference
[^skill-dir]: "The directory containing the skill's `SKILL.md` file." https://code.claude.com/docs/en/skills#available-string-substitutions
[^inline-rule]: "The inline form is only recognized when `!` appears at the start of a line or immediately after whitespace." https://code.claude.com/docs/en/skills#inject-dynamic-context
[^malformed]: "If the frontmatter YAML is malformed, Claude Code loads the skill body with empty metadata" https://code.claude.com/docs/en/skills#skill-not-triggering
[^hook]: "Claude Code runs a hook every time its event occurs, such as before each file edit, whether or not Claude is following the skill." https://code.claude.com/docs/en/skills#claude-stops-following-a-skill
[^or-true]: "append `|| true` to any other command you expect to exit non-zero" https://code.claude.com/docs/en/skills#when-an-injected-command-fails
[^not-restrict]: "It does not restrict which tools are available: every tool remains callable" https://code.claude.com/docs/en/skills#pre-approve-tools-for-a-skill
[^trust]: "Workspace trust doesn't gate this field." https://code.claude.com/docs/en/skills#pre-approve-tools-for-a-skill
