# Issue bodies

## Filling a Markdown template (`.md`)

- Keep every heading and its order. Replace placeholder text (`<code>`, `*explanation*`, "A clear and concise description...") with real content.
- Delete the instructional HTML comments once followed. Keep functional ones, such as bot commands the template tells you to keep.
- A section with nothing true to say gets `N/A` or a short reason (for example, "Not reproducible on demand; seen twice"), never filler.
- Front-matter `title:` is the title prefix and `labels:` are the template's labels; neither goes into the body.

## Filling a YAML issue form (`.yml`)

`gh` cannot submit forms, so write the body exactly as GitHub renders a submitted form:

```
### <field label>

<answer>
```

- One block per `input`, `textarea`, `dropdown` and `checkboxes` field, in form order. `markdown` blocks produce no output.
- `dropdown`: copy one of the listed `options` verbatim. Never write a value that is not listed; prefer an option such as "Other" or "I don't know" over a wrong one.
- `checkboxes`: `- [X] <label>` for confirmed items, `- [ ] <label>` otherwise. Check a box only when it is true and verified (for example, "I searched existing issues" after step 1 searched them; "latest version" only after comparing versions). If a required box cannot honestly be checked, tell the user instead of checking it.
- `textarea` with `render: <lang>`: put the answer in a fence of that language.
- Empty optional field: `_No response_`. Empty required field: get the fact (workflow step 3) or ask.
- The form's top-level `title:` is the title prefix; `labels:`, `type:` and `projects:` are metadata, not body text.

## Skeletons when the repository has no template

Use only the sections that have content.

**Bug**

```markdown
<One or two sentences: what fails, where, and the visible effect.>

### Steps to reproduce
1. ...

### Expected
...

### Actual
...
(error output in a fenced block)

### Environment
- <tool> <version>
- <OS and version>

### Notes
<Workarounds, frequency, related issues (#N), suspected cause marked as a guess.>
```

**Regression**: the bug skeleton plus `### Last working version` (version or commit) and, if known, the first bad version.

**Feature request**

```markdown
### Problem
<What the user is trying to do and what blocks them today. Concrete case first.>

### Proposed solution
<The smallest change that solves it; example command, config or output.>

### Alternatives considered
<Current workaround and why it is not enough.>
```

**Documentation problem**: page URL (with anchor), the quoted text that is wrong or missing, what it should say, and the source of truth (code, behavior observed, changelog).

**Question**: only when the repository takes questions as issues (check `contact_links` first): the goal, what was tried, what happened.
