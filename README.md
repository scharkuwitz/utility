# tldr

A [Claude Code](https://claude.com/claude-code) skill, `tldr-docs`, that turns long technical documentation into short, practical, light-theme HTML summary pages.

Each page sorts the source into: key concepts (with verbatim, verifiable quotes), exercises, common pitfalls, lower-priority topics, a quick reference, and review questions. Diagrams are drawn in plain HTML/CSS (flow, layers, tree), with no scripts or external diagram libraries.

## Usage

In Claude Code, from this directory:

```
/tldr-docs https://code.claude.com/docs/en/skills
```

The skill fetches the page, saves the source text, writes content JSON, and renders HTML:

```
tldr-out/src/<slug>.txt     fetched source text (used to verify quotes)
tldr-out/data/<slug>.json   content
tldr-out/<slug>.html        rendered page
```

To re-render manually (Python 3, standard library only):

```
python3 .claude/skills/tldr-docs/scripts/build.py tldr-out/data tldr-out
```

The build validates the JSON and warns when a quote is not found verbatim in the source.

## Layout

- `.claude/skills/tldr-docs/SKILL.md` skill instructions
- `.claude/skills/tldr-docs/references/schema.md` content JSON schema
- `.claude/skills/tldr-docs/scripts/build.py` renderer
- `tldr-out/` example output (`skills.html`); fetched source text is not committed

## License

[MIT](LICENSE)
