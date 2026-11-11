# utility

[Claude Code](https://claude.com/claude-code) skills for reading documentation and contributing on GitHub.

| Skill | What it does | Example |
|---|---|---|
| [`tldr`](.claude/skills/tldr/SKILL.md) | Condenses long docs into one wiki-style HTML study document: mental model and diagrams, worked examples, recipes, pitfalls, reference tables and self-check questions, with every quote checked against the source. | `/tldr https://code.claude.com/docs/en/skills` |
| [`gh-issue`](.claude/skills/gh-issue/SKILL.md) | Turns a complaint into a GitHub issue that follows the repository's template, after checking for duplicates. | `/gh-issue cli/cli <what went wrong>` |
| [`gh-pr`](.claude/skills/gh-pr/SKILL.md) | Opens a pull request for the current branch, written from the diff for the reviewer. | `/gh-pr <why the change exists> #12 --draft` |

## Install

Run Claude Code in a clone of this repository, or copy a skill folder from `.claude/skills/` into `~/.claude/skills/` to use it everywhere. Scripts need Python 3 (standard library only); the GitHub skills also need an authenticated [`gh`](https://cli.github.com).

The GitHub skills post directly to your own repositories and ask before posting to anyone else's. `--dry-run` drafts without posting.

Example output: [`tldr-out/claude-code/`](tldr-out/claude-code/) (open `index.html`; the page sources are in `pages/`).

## License

[MIT](LICENSE)
