# tldr

A [Claude Code](https://claude.com/claude-code) skill, `tldr-docs`, that turns long technical documentation into a short, practical, light-theme HTML study document.

Each page sorts its source into key concepts (backed by verbatim, checkable quotes), exercises, common pitfalls, lower-priority topics, a quick reference and review questions. Diagrams are plain HTML/CSS (flow, layers, tree): no scripts and no diagram libraries. When a page is mostly an overview, the skill follows its most important links within a fixed budget (at most 5 per page, 8 pages per run, one level deep).

## Usage

In Claude Code, from this directory:

```
/tldr-docs https://code.claude.com/docs/en/skills
/tldr-docs https://code.claude.com/docs/en/agents https://code.claude.com/docs/en/plugins
```

Each run fills a bundle folder and renders all of its pages into one HTML file:

```
tldr-out/<bundle>/src/<slug>.txt     fetched source text (used to verify quotes; not committed)
tldr-out/<bundle>/data/<slug>.json   page content; _index.json holds title, intro and order
tldr-out/<bundle>/index.html         the rendered document
```

The scripts can also be run by hand (Python 3, standard library only):

```
python3 .claude/skills/tldr-docs/scripts/fetch.py tldr-out/<bundle> <url>...   # save pages, print outline and links
python3 .claude/skills/tldr-docs/scripts/build.py tldr-out/<bundle>            # validate and render index.html
```

The build fails on schema errors. It warns when a quote is not found verbatim in the source or is longer than 25 words, when a diagram has more than 8 nodes, and when prose contains emoji.

## Layout

- `.claude/skills/tldr-docs/SKILL.md`: skill instructions
- `.claude/skills/tldr-docs/references/schema.md`: content JSON schema
- `.claude/skills/tldr-docs/scripts/fetch.py`: fetcher (Markdown first, HTML fallback) with outline and link ranking
- `.claude/skills/tldr-docs/scripts/build.py`: validator and single-file renderer
- `tldr-out/claude-code/`: example bundle covering Claude Code skills, agents and plugins

## License

[MIT](LICENSE)
