# Content JSON schema

Output is a light-theme, compact, emoji-free page. Content should be neutral and factual. Inline text fields support `` `code` `` and `**bold**`. Everything is HTML-escaped. Fields marked `?` are optional.

## Page: `data/<slug>.json`

```json
{
  "title": "Claude Code Skills",
  "source_url": "https://code.claude.com/docs/en/skills",
  "fetched": "2026-11-11",
  "one_liner": "A skill is a folder with SKILL.md; its description decides when Claude loads it.",
  "read_time_min": 5,
  "core": [
    {"title": "Description is the trigger", "body": "Claude reads every skill's `description` and decides from it alone whether to load the body.", "why": "Vague description = skill never fires.",
     "quotes": [{"text": "Claude uses the description to decide when to apply the skill", "url": "https://code.claude.com/docs/en/skills#frontmatter", "label": "Skills > Frontmatter"}],
     "diagram": {"type": "flow", "nodes": ["User prompt", "Description matches?", "Load SKILL.md body"], "edges": ["", "yes"], "caption": "Auto-loading decision"}}
  ],
  "skip": [
    {"title": "Plugin-distributed skills", "note": "Only matters when sharing across teams. See Plugins docs."}
  ],
  "practice": [
    {
      "title": "Build and trigger your first skill",
      "goal": "Feel the description -> auto-load loop.",
      "steps": ["Create `.claude/skills/hello/SKILL.md`", "Add frontmatter with `name` and `description`", "Ask something matching the description"],
      "code": {"lang": "markdown", "text": "---\nname: hello\ndescription: ...\n---\nBody"},
      "check": "Claude announces using the skill without you naming it.",
      "variation": "Make the description vaguer; observe it stop firing."
    }
  ],
  "gotchas": ["Skill folder name must match `name`."],
  "cheatsheet": [{"term": "`allowed-tools`", "meaning": "Tools usable without prompting while the skill is active."}],
  "recall": [{"q": "What decides whether a skill loads automatically?", "a": "Its `description` frontmatter."}],
  "sources": [{"title": "Skills docs", "url": "https://code.claude.com/docs/en/skills#frontmatter"}]
}
```

Required: `title`, `one_liner`, `core` (>=1). Everything else optional but strongly encouraged (`practice`, `skip`, `recall`).
`practice[].code` is optional; may also be a list of such objects. `slug` = filename without `.json`.

### `core` item extras

- `quotes` (**required**): `[{text, url?, label?}]`. `text` must be copied verbatim from the fetched page (<=25 words). Rendered as small numbered footnotes. Verified against `tldr-out/src/<slug>.txt` (WARN on mismatch).
- `diagram` (optional): one of
  - `{"type":"image","url":"https://...","alt":"...","caption":"..."}` the docs' own image
  - `{"type":"flow","nodes":["A","B",{"label":"C","note":"detail"}],"edges":["","label for B->C"],"direction":"row|column","caption":"..."}` linear process; `edges[i]` labels the arrow after node i
  - `{"type":"layers","items":["Highest precedence","Middle",{"label":"Lowest","note":"default"}],"caption":"..."}` stacked boxes
  - `{"type":"tree","nodes":[{"label":"root","children":[{"label":"child","note":"..."}]}],"caption":"..."}` hierarchy
  - `{"type":"svg","svg":"<svg viewBox=...>...</svg>","caption":"..."}` (scripts and `on*` handlers are stripped)

## Index (multi-page only): `data/_index.json`

```json
{
  "title": "Claude Code docs: TLDR",
  "source_url": "https://code.claude.com/docs",
  "intro": "Suggested reading order, most foundational first.",
  "order": ["overview", "skills", "hooks"]
}
```

`order` lists slugs. If `_index.json` is absent, pages are listed alphabetically. A summary line per page is taken from its `one_liner`.
