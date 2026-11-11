# Content JSON schema

One file per page at `tldr-out/<bundle>/data/<slug>.json`, where the slug is the name `fetch.py` printed. Inline text fields support `` `code` `` and `**bold**`; everything else is escaped. Write neutral, emoji-free prose.

## Page

```json
{
  "title": "Claude Code Skills",
  "source_url": "https://code.claude.com/docs/en/skills",
  "fetched": "2026-11-11",
  "one_liner": "A skill is a folder with SKILL.md; its description decides when Claude loads it.",
  "read_time_min": 5,
  "core": [
    {
      "title": "The description is the trigger",
      "body": "Claude reads each skill's `description` and uses it to decide whether to load the full skill.",
      "why": "A vague description means the skill is not used automatically.",
      "quotes": [
        {"text": "Claude uses this to decide when to apply the skill.",
         "url": "https://code.claude.com/docs/en/skills#frontmatter-reference",
         "label": "Skills > Frontmatter reference"}
      ],
      "diagram": {"type": "flow", "nodes": ["Descriptions in context", "Request matches", "Body loads"],
                  "caption": "Default loading behaviour"}
    }
  ],
  "practice": [
    {
      "title": "Create and trigger a skill",
      "goal": "Observe automatic loading.",
      "steps": ["Create `.claude/skills/hello/SKILL.md`", "Ask something that matches the description"],
      "code": {"lang": "markdown", "text": "---\ndescription: ...\n---\nBody"},
      "check": "Claude uses the skill without being told to.",
      "variation": "Make the description vague and test again."
    }
  ],
  "gotchas": ["Unrecognized frontmatter fields are ignored without an error."],
  "skip": [
    {"title": "Plugin-distributed skills", "note": "Only for sharing across teams.",
     "url": "https://code.claude.com/docs/en/plugins"}
  ],
  "cheatsheet": [{"term": "`disable-model-invocation: true`", "meaning": "Manual invocation only."}],
  "recall": [{"q": "What decides whether a skill loads automatically?", "a": "Its `description`."}],
  "sources": [{"title": "Extend Claude with skills", "url": "https://code.claude.com/docs/en/skills"}]
}
```

Required: `title`, `one_liner`, and `core` with at least one item. Every `core` item needs `title` and `quotes`. Everything else is optional but expected (`practice`, `skip` and `recall` especially). `practice[].code` may be a single object or a list. `skip[].url` makes the title a link; use it for pointers you chose not to follow.

## Quotes

`[{text, url?, label?}]`, rendered as numbered footnotes. `text` must appear verbatim in `src/<slug>.txt`. Matching ignores case, whitespace, curly versus straight quotes, `*`, `_`, backticks, markdown link syntax (`[text](url)` counts as `text`), blockquote markers and backslash escapes. The build warns when a quote is missing from the source or longer than 25 words.

## Diagrams (`core[].diagram`, optional, at most 8 nodes)

| Type | Shape | Use for |
|---|---|---|
| `image` | `{"type":"image","url":"https://...","alt":"...","caption":"..."}` | the docs' own diagram |
| `flow` | `{"type":"flow","nodes":["A",{"label":"B","note":"detail"}],"edges":["label for A->B"],"direction":"row\|column"}` | processes, lifecycles |
| `layers` | `{"type":"layers","items":[{"label":"Top","note":"wins"},"Middle","Bottom"]}` | precedence, load order (first item is highlighted) |
| `tree` | `{"type":"tree","nodes":[{"label":"root/","children":[{"label":"file","note":"..."}]}]}` | directory layouts, hierarchies |
| `svg` | `{"type":"svg","svg":"<svg viewBox=...>...</svg>"}` | last resort; scripts and `on*` handlers are stripped |

All types accept `caption`. `edges[i]` labels the arrow after node `i`.

## Bundle index: `data/_index.json` (needed when there are several pages)

```json
{
  "title": "Claude Code Docs: Summaries",
  "source_url": "https://code.claude.com/docs",
  "intro": "Suggested reading order: skills, then subagents, then plugins.",
  "order": ["skills", "sub-agents", "plugins"]
}
```

`order` lists slugs. Pages it omits follow in alphabetical order. The contents list uses each page's `title` and `one_liner`, and the header sums `read_time_min`.
