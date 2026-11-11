# Page format

Each page is a Markdown file at `<bundle>/pages/<slug>.md`. It uses ordinary Markdown plus a few `:::` blocks and diagram fences. `build.py` turns every page into one HTML document. Raw HTML is not supported; it is escaped and shown as text. Write pages with the Write tool, because shell heredocs break on backticks.

## Front matter

```markdown
---
title: Agent skills
source: https://code.claude.com/docs/en/skills
fetched: 2026-11-11
summary: Folders of instructions Claude loads when their description matches the task.
group: Extending Claude Code
---
```

| Key | Required | Use |
|---|---|---|
| `title` | yes | Page title, shown as the H1. Never write `# Title` in the body. |
| `source` | yes | The main page condensed. It appears under the title as "From ...". |
| `summary` | yes | One line, used in the start page's contents table. Inline code allowed. |
| `fetched` | no | ISO date. Defaults to the start page's date, then to today. |
| `group` | no | Navbox row that this page belongs to, such as "Basics" or "Extending". |

`pages/index.md` is the **start page** of a bundle of two or more pages. Its front matter takes `title`, `source`, `fetched` and `order` (comma-separated slugs in reading order). Its body is ordinary Markdown: who the bundle is for, what to know first, a map diagram, and reading paths. Place `:::pages` followed by `:::` where the contents table should appear; without it, the table goes at the end.

## Body

The **lead** is everything before the first `##`. Use `##` for sections and `###` and `####` below them; `##` and `###` appear in the contents sidebar with numbers.

Supported Markdown: paragraphs, `**bold**`, `*italic*`, `` `code` ``, `[links](url "title")`, `<https://autolinks>`, `-` and `1.` lists (nested by indenting two or more spaces), `>` quotes, `---` rules, pipe tables with an alignment row, `![alt](url "caption")` images on their own line, and definition lists:

```markdown
Term
: Definition, which may span lines indented by two spaces.
```

Straight quotes become curly quotes in prose, and `...` becomes an ellipsis. Code is never changed.

**Links between pages**: `[Plugins](plugins.md)`, `[Plugin manifest](plugins.md#manifest)`, or `[a section here](#how-it-works)`, where the anchor is the heading text in lowercase with spaces as hyphens. The build warns about links that point nowhere.

## Citations

Write `[^key]` after a claim and define the key anywhere on the page, usually at the bottom:

```markdown
Claude reads every skill's description to decide when to load it.[^desc]

[^desc]: "Claude uses this to decide when to apply the skill." https://code.claude.com/docs/en/skills#frontmatter-reference
```

- **Quote form**: `"verbatim text" URL`, optionally followed by `(label)`. The text must appear in the fetched copy of that URL; matching ignores case, Markdown markup, link syntax and the difference between straight and curly quotes. Use `...` to skip words. Keep quotes to one claim and at most 30 words.
- **Link form**: `URL (label)` with no quote, for pointing at a page without quoting it.
- **Note form**: free text, for a short aside. Use it rarely.

Without `(label)`, the reference list shows the fetched page title and the section heading the anchor points to, such as "Extend Claude with skills § Frontmatter reference". Citations are numbered in order of first use, Wikipedia style; reusing a key reuses its number.

## Blocks

A block opens with `:::name` and closes with a line holding only `:::`. Blocks can contain any Markdown, including other blocks.

### `:::infobox [title]`

Facts the reader looks up first. Lines are `Label: value`, `## Group heading`, or an image. Place it right after the front matter. The build floats it beside the lead and adds a "This summary" group with the cited pages and the quote check.

```markdown
:::infobox
Kind: Instruction file for Claude Code
Lives in: `.claude/skills/<name>/SKILL.md`
Loads when: its description matches the task, or you type `/name`
Related: [Subagents](sub-agents.md), [Plugins](plugins.md)
## Limits
Listing cap: 1,536 characters per skill[^cap]
:::
```

### Hatnotes (one line, no closing `:::`)

```markdown
:::main [Frontmatter reference](https://code.claude.com/docs/en/skills#frontmatter-reference)
:::see [Subagents](sub-agents.md), [Hooks](https://code.claude.com/docs/en/hooks)
:::hatnote This page covers project and personal skills. For plugin skills, see [Plugins](plugins.md).
```

`:::main` goes under a heading whose section condenses one docs section. It renders as "Main article: ...", the way Wikipedia points to the full treatment. `:::hatnote` goes at the top of a page for scope or disambiguation.

### `:::note`, `:::tip`, `:::warning` [title]

Use **note** for information that isn't obvious, **tip** for optional but useful information, and **warning** for loss of data or work, security problems, or anything hard to undo. Use them sparingly: three callouts in a row means the content belongs in the body.

### `:::background [title]`

Context that does not come from the source: terms the docs assume, or how the thing relates to general concepts. It is labeled "General knowledge, not from the source documentation." Keep it to standard, stable facts.

### `:::example [title]`

A worked example in the Go by Example style. Prose and fenced code alternate. Each prose chunk sits beside the code that follows it, and an `output` fence directly after a code fence joins the same row.

````markdown
:::example A skill that triggers on its own
Create the folder. Project skills live under `.claude/skills/`.

```console
$ mkdir -p .claude/skills/explain-code
```

Write the instructions. The `description` is what Claude matches against your request.

```markdown .claude/skills/explain-code/SKILL.md
---
description: Explains code with a diagram and an analogy. Use when the user asks how code works.
---

When explaining code, start with an ASCII diagram of the flow.
```
:::
````

### `:::recipes`

Common tasks in the tldr-pages style. Each item is `- Description ending in a colon:` followed by a line holding one inline-code command or by a fenced block. `{{placeholder}}` marks a part the reader replaces. Keep at most 8.

```markdown
:::recipes
- Create a personal skill available in every project:
  `mkdir -p ~/.claude/skills/{{skill_name}}`

- Run a skill with arguments:
  `/{{skill_name}} {{arguments}}`
:::
```

### `:::exercise [title]`

A hands-on drill of under 10 minutes. Include a line starting with `Check:` (or `**Check:**`) that says what the reader should observe; the build warns without one. Optionally add `Variation:`.

### `:::recall`

Self-check questions. Write each question on one line and its answer on the next line, starting with `: `. Answers stay hidden until the reader opens them.

```markdown
:::recall
What decides whether Claude loads a skill without being asked?
: Its `description`, matched against the request.[^desc]
:::
```

### `:::pages`

Start page only. Close it with `:::` on the next line. It marks where the contents table goes.

## Code fences

` ```lang label ` adds a caption bar with the label, such as a file path. Highlighting is deliberately small: comments, keys in YAML, TOML and JSON, `$ ` prompts (not copied), `+` and `-` lines in `diff`, and front matter in `markdown`. In a `console` or `bash` fence that has `$ ` lines, the other lines show as output. An `output` fence shows program output, dashed and muted, and has no copy button.

## Diagrams

Diagram fences render as HTML, CSS or inline SVG that follows the light and dark themes. Text after the kind is the caption; write one that says what to notice. Lines starting with `//` are ignored. Labels accept inline code. Keep diagrams to 8 nodes.

### `flow`: steps, decisions, loops

````markdown
```flow How a skill reaches Claude
Skill descriptions in context : loaded at session start
-> request matches
Claude loads SKILL.md | You type `/name`
Claude follows the instructions
loop: next matching request
```
````

Each line is a box, with `label : note`. A `-> text` line labels the next arrow. Use `a | b` for alternatives within one step, and `loop: text` for a return arrow. Flows run left to right and switch to top to bottom when there are more than 5 boxes, when the text is long, or on phones. Force a direction with `flow:v` or `flow:h`.

### `sequence`: who talks to whom over time

````markdown
```sequence What happens when a skill runs in a subagent
You -> Claude: /deep-research auth flow
Claude -> Subagent: skill content as the task
Subagent -> Subagent: reads files
Subagent --> Claude: summary
note Subagent: own context window
```
````

`A -> B: message` draws a solid arrow and `A --> B: reply` a dashed one. A message from a participant to itself draws a loop. `note A: text` or `note A, B: text` adds a note. Participants appear in order of first mention; `participant Name` lines set the order explicitly. Keep labels under about 50 characters.

### `stack`: precedence and layers

````markdown
```stack When two skills share a name, the higher one wins
^ wins
* Enterprise : managed settings
Personal : `~/.claude/skills/`
Project : `.claude/skills/`
```
````

The first item is drawn on top. `^ label` or `v label` adds an axis arrow, and `* ` highlights an item.

### `tree`: directory layout

````markdown
```tree A skill with supporting files
my-skill/
  SKILL.md          # required: instructions and front matter
  reference.md      # read only when needed
  scripts/
    validate.sh     # run, not loaded into context
```
````

Indentation sets depth. Text after ` # ` is a muted comment, aligned in a column. Names that end in `/` are shown as directories.

### `nest`: containment

````markdown
```nest What a plugin bundles
Plugin : `my-plugin/`
  Skills : `skills/<name>/SKILL.md`
  Agents : `agents/<name>.md`
  Hooks : `hooks/hooks.json`
  MCP servers : `.mcp.json`
```
````

Indentation sets containment, and children sit side by side inside their parent.

### `svg`: last resort

A fence holding one hand-written `<svg>` element. Scripts and event handlers are stripped. Use `currentColor` so it works in both themes.

## What the build checks

**ERROR** (exit status 1): missing title, unclosed fences or blocks, unknown blocks, citations with no definition, `#` used as a heading.

**WARN**:
- quotes not found in the fetched source or longer than 30 words;
- no lead, or a lead over 160 words;
- no infobox, fewer than 3 recall questions, nothing hands-on, or no citations;
- diagrams with no caption or too many items;
- more than 8 recipes, or exercises without `Check:`;
- unused footnotes, links that point nowhere, emoji.

**NOTE**: sections without citations, and pages that read in over 20 minutes.

Fix every ERROR and WARN before reporting. Read each NOTE and decide whether it needs a fix.
