# CLAUDE.md

This repository ("utility") is a set of Claude Code skills, not an application. There is no package, build system or test suite. Each skill lives in `.claude/skills/<name>/` and is self-contained:

```
SKILL.md          frontmatter (name, description, argument-hint) + the workflow Claude follows
scripts/*.py      helper scripts the workflow calls
references/*.md   detail loaded on demand (page format, writing craft, issue body skeletons)
assets/           files a script inlines into its output (tldr only: style.css, app.js)
```

| Skill | Scripts | Needs |
|---|---|---|
| `tldr` | `fetch.py` (download docs to `src/`, print outline + ranked links), `build.py` (parse `pages/*.md`, verify quotes against `src/`, render one `index.html`) | network |
| `gh-issue` | `issue_context.py` (repo facts, templates, labels, duplicate search) | authenticated `gh` |
| `gh-pr` | `pr_context.py` (branch state, diffstat, PR template, title convention) | `git`, authenticated `gh` |

`tldr-out/claude-code/` is committed example output of the `tldr` skill: `pages/*.md` (the written pages) and `index.html` (the build). Its `src/` (fetched source text) is gitignored, so on a fresh clone the build warns that quotes were not verified; re-fetch the pages listed in each page's citations with `fetch.py` to verify them.

### tldr internals

- Pages are Markdown plus `:::` blocks and diagram fences, specified in `references/format.md`. `build.py` implements that spec with its own stdlib parser; a syntax change touches both files.
- `references/craft.md` is the writing method (what to keep, cut and add; how to explain). SKILL.md is only the workflow and links to both references.
- All styling lives in `assets/style.css` as CSS variables, with light and dark tokens; `app.js` is progressive enhancement (one page at a time, contents highlighting, copy buttons, appearance settings). The document must stay readable with JavaScript off.
- Design rules for the output: Wikipedia-like typography (serif headings over a hairline rule, sans body, infobox, hatnotes, numbered citations, navbox). No shadows, gradients, hero sections, card grids or emoji.

## Conventions

- **Python 3 standard library only.** No third-party imports, no requirements file. Scripts use `argparse`, have a module docstring with a `Usage:` line, and exit via `sys.exit("!! message")` on fatal errors.
- **Context scripts gather everything in one call** and print plain text for Claude to read; they never post or modify anything. Posting (`gh issue create`, `gh pr create`) happens in the SKILL.md workflow, after a confirmation step for repositories the user does not own.
- **SKILL.md style**: neutral, imperative, compact. Tables for arguments, numbered workflow steps, a "Writing rules" section. No emoji, exclamation marks or filler ("robust", "seamlessly"). `<skill>` means the skill's base directory; `$ARGUMENTS` is the user's input.
- The `description` frontmatter drives when a skill triggers: keep the trigger phrases in it when editing.
- When a script's output or flags change, update the matching SKILL.md step (and `references/format.md` for `build.py` syntax or check changes) in the same commit.
- README is a one-screen overview with a skill table; details belong in each SKILL.md, not the README.

## Checking changes

```bash
python3 -m py_compile .claude/skills/*/scripts/*.py
# tldr: rebuild the example bundle (no errors; the only expected WARN is "no fetched sources" when src/ is absent)
python3 .claude/skills/tldr/scripts/build.py tldr-out/claude-code
```

`build.py` exits non-zero on ERROR lines (broken syntax, undefined citations, missing title) and prints `WARN` lines for quality problems (quote not found or over 30 words, missing lead, infobox or self-check, oversized diagrams, emoji) and `NOTE` lines for information. For visual changes, open the built `index.html` in light and dark mode and at phone width. Run it on a copy of the bundle if you don't want to touch the committed `index.html`. The `gh-*` scripts can be smoke-tested read-only, e.g. `python3 .claude/skills/gh-issue/scripts/issue_context.py cli/cli --search "foo"` and `python3 .claude/skills/gh-pr/scripts/pr_context.py` on a topic branch.

## Git

- Commit subjects: sentence-case imperative ("Add gh-issue and gh-pr skills"), optional bullet body; reference issues with `Closes #N`.
- Work on a topic branch; `main` is the PR base.
