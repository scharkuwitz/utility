---
title: Claude Code skills and plugins
source: https://code.claude.com/docs
fetched: 2026-11-11
order: skills, plugins
---

These pages condense about 2,800 lines of the Claude Code documentation on **skills** and **plugins**, the two main ways to teach Claude Code a procedure and share it, into about 20 minutes of reading. They are written for someone who already uses Claude Code day to day and has never written a skill.

When you finish, you should be able to write a skill that triggers when it should, decide whether a setup needs to be a plugin, and avoid the mistakes that make either one silently do nothing.

:::background What to know first
Claude Code works within a **context window**: everything Claude can see on a turn, including the conversation, files it has read and loaded instructions. Anything that sits in context on every turn costs tokens on every turn.

**CLAUDE.md** files hold instructions that load at the start of every session. **Slash commands** are messages that start with `/`, such as `/help`. **Subagents** are separate assistants with their own context window that Claude can hand a task to. **Hooks** are commands that Claude Code itself runs on events such as a file edit; they do not depend on Claude's judgment.
:::

## How the pieces fit

All four ways of extending Claude Code carry instructions or behavior. They differ in when they load and who decides to use them:

| Mechanism | Loads | Who decides it runs | Use it for |
|---|---|---|---|
| CLAUDE.md | Every session, in full | Always on | Short facts about the project |
| Skill | Description always; body when invoked | Claude (from the description) or you (`/name`) | Procedures, checklists, reference material |
| Hook | Registered at startup | Fires on its event, every time | Rules that must always hold |
| Plugin | Every enabled component, every session | You, by installing and enabling it | Shipping several of the above as one unit |

```nest A plugin is a package; the skills, agents, hooks and servers inside it also work on their own
Plugin : `my-plugin/`, installed from a marketplace
  Skills : instructions loaded on demand
  Agents : subagents to delegate to
  Hooks : commands run on events
  MCP servers : tools from external systems
```

## Reading paths

- **Write your first skill (8 minutes)**: [Skills](skills.md), from the start through "By example".
- **Share a setup with your team (20 minutes)**: all of [Skills](skills.md), then [Plugins](plugins.md).
- **Install someone else's plugin safely (5 minutes)**: in [Plugins](plugins.md), read "How it works", "Recipes" and "Pitfalls".

## Contents

:::pages
:::
