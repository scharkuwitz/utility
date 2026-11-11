---
title: Plugins
source: https://code.claude.com/docs/en/plugins
fetched: 2026-11-11
summary: One installable directory that bundles skills, agents, hooks and MCP servers, with a manifest, a name prefix and an install scope.
group: Extending Claude Code
---

:::infobox
Kind: Installable bundle of Claude Code extensions
Contains: skills, agents, hooks, MCP servers and other components
Manifest: `.claude-plugin/plugin.json`; only `name` is required
Names: `/my-plugin:skill`, `my-plugin:agent`
Comes from: a marketplace, a folder, a `.zip` or a URL
Install scopes: user, project, local
Manage with: `/plugin` in a session, `claude plugin` in a shell
Related: [Skills](skills.md), subagents, hooks, MCP
:::

:::hatnote Not the Claude Code extension for VS Code or the JetBrains plugin for running Claude Code in an IDE.

A **Claude Code plugin** is "a directory of skills, agents, hooks, MCP servers, or other components that Claude Code installs and loads as one unit."[^def] A small JSON manifest gives it a name, and that name becomes a prefix on everything inside it. Most plugins are installed from a **marketplace**, a catalog listing plugins and where to fetch them.

You don't need a plugin to use a skill, a hook or an MCP server; each works on its own.[^standalone] Reach for a plugin when you want several of them "packaged as one unit":[^when] to install a setup someone else built with one command, or to give yours to a team, install it across projects, and ship versioned updates.

## How it works

:::main [Plugins overview](https://code.claude.com/docs/en/plugins)

A plugin is an ordinary directory. Each kind of component has a fixed folder under the plugin root, and the manifest sits apart from them in `.claude-plugin/`.

```nest A plugin bundles components that also exist on their own; only the manifest is plugin-specific
my-plugin/ : the plugin root, the folder you install or load
  Manifest : `.claude-plugin/plugin.json`, name and version
  Skills : `skills/<name>/SKILL.md`
  Agents : `agents/<name>.md`
  Hooks : `hooks/hooks.json`
  MCP servers : `.mcp.json`
```

### From a marketplace to your session

A marketplace is a repository or folder with a `.claude-plugin/marketplace.json` file. "It's a catalog, not a hosted store":[^catalog] it lists plugins and says where to fetch each one. Claude Code adds Anthropic's official marketplace the first time you start an interactive terminal session.[^official] You add any other marketplace once, then install its plugins by name, as `plugin@marketplace`.

```flow An installed plugin reaches a session only after it is enabled in settings, fetched to disk and loaded
Marketplace : catalog listing plugins
-> install, pick a scope
Settings : `enabledPlugins` records it
Disk : fetched into `~/.claude/plugins/`
-> startup or `/reload-plugins`
Session : components load
```

During development you skip the marketplace entirely: `--plugin-dir` "loads a directory or `.zip` archive for one session."[^plugin-dir]

### Enabled means present in every session

"An enabled plugin is part of every session, not only the sessions where you use it."[^every-session] That has three costs to weigh before installing:

- **Context.** The name and description of every skill and agent that Claude can invoke on its own sit in context on every turn, as with standalone skills. Full text loads only when used.
- **Processes.** Its MCP servers run alongside each session, and its hooks fire on their events. Hooks don't wait for one of the plugin's skills to be used.[^hooks-fire]
- **Permissions.** "What the plugin runs, it runs as you."[^runs-as-you] This holds for every marketplace tier, official ones included.

To stop a plugin without uninstalling it, disable it.

### Scopes decide who has it

When you install, you pick a scope, and the scope decides which settings file records the plugin as enabled.

```stack The same plugin set at several scopes: the most specific setting wins
^ wins
Local : `.claude/settings.local.json`, you in this repository
Project : `.claude/settings.json`, everyone in this repository
User : `~/.claude/settings.json`, you in every project
```

The local setting overrides the project setting, which overrides the user setting.[^scope-order] Project scope has a catch: committing the setting "turns the plugin on for your collaborators but doesn't download it to their machines."[^project-scope] Each collaborator installs it once per clone. Cloud sessions, including claude.ai/code, don't load plugins from your local settings at all.[^cloud]

### Names get a prefix

Inside a plugin, skills and agents take the plugin's name as a prefix, "so two plugins can each provide a `hello` skill without colliding."[^prefix] The manifest's `name` is the only required field, because it becomes that prefix.[^name]

| Component | File in the plugin | What the user sees |
|---|---|---|
| Skill | `skills/review/SKILL.md` | `/my-plugin:review` |
| Agent | `agents/security-reviewer.md` | `my-plugin:security-reviewer`[^agent-name] |
| MCP server | `db` in `.mcp.json` | `plugin:my-plugin:db` in `/mcp`[^mcp-name] |
| Hook | `hooks/hooks.json` | Nothing; it fires on its event |

## By example

:::example Build a plugin and run it without a marketplace
This is the docs' minimal plugin: one skill, loaded straight from its folder. Create the plugin root and the manifest folder inside it.

```console
$ mkdir -p my-first-plugin/.claude-plugin
```

The manifest names the plugin. `name` becomes the prefix of every command; `version` holds users at that version until you change it.

```json my-first-plugin/.claude-plugin/plugin.json
{
  "name": "my-first-plugin",
  "description": "A greeting plugin to learn the basics",
  "version": "1.0.0",
  "author": {
    "name": "Your Name"
  }
}
```

The skill goes under `skills/` at the plugin root, next to `.claude-plugin/`, never inside it. `disable-model-invocation: true` means only you can run it.

```markdown my-first-plugin/skills/hello/SKILL.md
---
name: hello
description: Greet the user with a friendly message
disable-model-invocation: true
---

Greet the user warmly and ask how you can help them today.
```

Validate before running. The check covers the manifest and the front matter of every skill, agent and command file.[^validate] On success it prints the manifest path and a pass line.

```console
$ claude plugin validate ./my-first-plugin
```

```output Last line of the output, as the docs give it
✔ Validation passed
```

Start a session with the plugin loaded for that session only, then run the skill under its prefixed name.

```console
$ claude --plugin-dir ./my-first-plugin
```

```text
/my-first-plugin:hello
```
:::

## Recipes

:::recipes
- Browse and install from your marketplaces, in a session:
  `/plugin`

- Open one plugin's details to review it and choose a scope:
  `/plugin install {{plugin}}@{{marketplace}}`

- Install from your shell, for example in a setup script:
  `claude plugin install {{plugin}}@{{marketplace}} --scope {{user|project|local}}`

- Add a marketplace hosted on GitHub:
  `/plugin marketplace add {{owner/repo}}`

- Load a plugin you are writing, for one session:
  `claude --plugin-dir {{path/to/plugin}}`

- Apply plugin changes made on disk to the running session:
  `/reload-plugins`

- Turn a plugin off without uninstalling it:
  `claude plugin disable {{plugin}}@{{marketplace}}`

- Update one plugin now:
  `claude plugin update {{plugin}}@{{marketplace}}`
:::

## Reference

### Layout

Add only the folders you use. Paths in the manifest can point components elsewhere.

| Location | Contents |
|---|---|
| `.claude-plugin/plugin.json` | The manifest, and nothing else in that folder |
| `skills/` | One `<name>/SKILL.md` folder per skill |
| `agents/` | One Markdown file per subagent |
| `hooks/hooks.json` | Hooks under a top-level `"hooks"` key, in the same shape as the `hooks` object in `settings.json`[^hook-shape] |
| `.mcp.json` | MCP server definitions, in the same shape as a project `.mcp.json` |
| `commands/` | Flat Markdown files, the older form of skills |

### Paths inside a plugin

You don't know where a plugin will be installed, so plugin files refer to each other through variables. Claude Code substitutes them in skill and agent content, hook commands and MCP configurations.

| Variable | Points to | Use for |
|---|---|---|
| `${CLAUDE_PLUGIN_ROOT}` | This version's install directory, which changes on every update[^root] | Bundled scripts and files; never state |
| `${CLAUDE_PLUGIN_DATA}` | `~/.claude/plugins/data/<id>/`, which survives updates | `node_modules`, virtual environments, caches[^data] |
| `${CLAUDE_PROJECT_DIR}` | The project root | Project files |

### Updates

Auto-update is on for Anthropic's official marketplaces and off for every other marketplace, "including the community marketplace, third-party marketplaces, and local development marketplaces."[^autoupdate] An update changes the files on disk, but "the running session keeps the versions it already loaded";[^session-keeps] run `/reload-plugins` or start a new session.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| The plugin loads, but its skills are missing | `skills/` was placed inside `.claude-plugin/`[^skills-missing] | Move every component folder to the plugin root |
| `--plugin-dir` loads nothing, with no error | It points at a marketplace root, not a plugin root[^mp-root] | Point it at the folder that holds `.claude-plugin/plugin.json` |
| Instructions in the plugin's `CLAUDE.md` are ignored | Claude Code doesn't load a `CLAUDE.md` at the plugin root[^no-claude-md] | Write the instructions as a skill |
| Saved state disappears after an update | It was written under `${CLAUDE_PLUGIN_ROOT}`, which is per version | Write to `${CLAUDE_PLUGIN_DATA}` |
| Teammates don't get a project-scoped plugin | The committed setting enables it but doesn't download it | Each collaborator runs `claude plugin install <name>@<marketplace> --scope project` |
| An edit or update doesn't show up | The session loaded the old version | Run `/reload-plugins` |
| A component fails to load | Bad path or front matter | Check the **Errors** tab in `/plugin`, then run `claude plugin validate` |

:::warning
Any plugin, from any marketplace tier, can run code with your user privileges through its hooks and MCP servers. Read the **Will install** list in the plugin's details before you install it.
:::

## Not covered

- **Running a marketplace** for a team: [Create a marketplace](https://code.claude.com/docs/en/plugins/create-marketplace) and [Host and maintain a marketplace](https://code.claude.com/docs/en/plugins/host-marketplace).
- **Publishing**, including submission to Anthropic's directory: [Publish and distribute a plugin](https://code.claude.com/docs/en/plugins/publish).
- **Reviewing a plugin's safety** and the marketplace tiers: [Plugin security and trust](https://code.claude.com/docs/en/plugins/security).
- **Organization policy**: allowlists, forced installs and managed scope: [Manage plugins for your organization](https://code.claude.com/docs/en/plugins/org).
- **Other components**: LSP servers, monitors, channels, themes, output styles, executables, default settings, `userConfig` options, and mods: [Add components to a plugin](https://code.claude.com/docs/en/plugins/components).
- **Measuring cost and testing behavior** with `claude plugin eval`: [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals).
- **Plugins on claude.ai and in Cowork**, where a different set of components loads.

## Check yourself

:::recall
You have one skill you want in all your projects. Do you need a plugin?
: No. Save it in `~/.claude/skills/`. Plugins are for bundling several components or for sharing and versioning them.[^standalone]

A plugin you installed hasn't been used all week. Is it costing you anything?
: Yes. An enabled plugin is part of every session: its descriptions take context, its MCP servers run and its hooks fire. Disable it if you don't need it.[^every-session]

A plugin is enabled at user scope, and `.claude/settings.local.json` disables it. Is it on in this repository?
: No. Local overrides project, which overrides user.[^scope-order]

You committed a plugin at project scope, but a teammate's session doesn't have it. Why?
: Project scope enables the plugin but doesn't download it. The teammate installs it once in their clone.[^project-scope]

To keep the plugin root tidy, you move `skills/` into `.claude-plugin/`. What happens?
: The plugin still loads, but its skills don't. Only `plugin.json` goes in `.claude-plugin/`; components go at the plugin root.[^manifest-only]

Where should a plugin keep a downloaded cache so that it survives updates?
: In `${CLAUDE_PLUGIN_DATA}`. `${CLAUDE_PLUGIN_ROOT}` changes with every version.[^data]
:::

[^def]: "A Claude Code plugin is a directory of skills, agents, hooks, MCP servers, or other components that Claude Code installs and loads as one unit." https://code.claude.com/docs/en/plugins
[^standalone]: "Skills, subagents, hooks, and MCP servers all work on their own, without a plugin." https://code.claude.com/docs/en/plugins#decide-whether-you-need-a-plugin
[^when]: "Use a plugin when you want several skills, subagents, hooks, or MCP servers packaged as one unit." https://code.claude.com/docs/en/plugins#decide-whether-you-need-a-plugin
[^catalog]: "It's a catalog, not a hosted store." https://code.claude.com/docs/en/plugins#get-plugins-from-a-marketplace
[^official]: "Claude Code adds Anthropic's official marketplace the first time you start an interactive terminal session" https://code.claude.com/docs/en/plugins#get-plugins-from-a-marketplace
[^plugin-dir]: "--plugin-dir: loads a directory or `.zip` archive for one session." https://code.claude.com/docs/en/plugins/create#develop-without-a-marketplace
[^every-session]: "An enabled plugin is part of every session, not only the sessions where you use it." https://code.claude.com/docs/en/plugins#what-an-enabled-plugin-adds-to-your-sessions
[^hooks-fire]: "A plugin's hooks don't wait for one of the plugin's skills or commands to be used." https://code.claude.com/docs/en/plugins/components#when-plugin-hooks-fire
[^runs-as-you]: "what the plugin runs, it runs as you." https://code.claude.com/docs/en/plugins#what-an-enabled-plugin-adds-to-your-sessions
[^scope-order]: "the local setting overrides the project setting, and the project setting overrides the user setting" https://code.claude.com/docs/en/plugins/install#choose-an-install-scope
[^project-scope]: "Committing that entry turns the plugin on for your collaborators but doesn't download it to their machines." https://code.claude.com/docs/en/plugins/install#choose-an-install-scope
[^cloud]: "A cloud session, including one in the browser at claude.ai/code, doesn't load the plugins in your local settings." https://code.claude.com/docs/en/plugins#understand-install-scopes
[^prefix]: "plugin skills and agents get the plugin name as a prefix, such as `/my-plugin:hello`, so two plugins can each provide a `hello` skill without colliding" https://code.claude.com/docs/en/plugins/create#decide-when-to-use-a-plugin
[^name]: "required. It identifies the plugin and becomes the prefix on every skill and agent the plugin provides." https://code.claude.com/docs/en/plugins/create#create-your-first-plugin
[^agent-name]: "This agent is named `my-plugin:security-reviewer`" https://code.claude.com/docs/en/plugins/components#agents
[^mcp-name]: "Load the plugin and run `/mcp` to confirm the server appears as `plugin:my-plugin:db`." https://code.claude.com/docs/en/plugins/components#mcp-servers
[^validate]: "It checks the manifest and the frontmatter of every skill, agent, and command file" https://code.claude.com/docs/en/plugins/create#test-and-debug
[^hook-shape]: "in the same shape as the `hooks` object in `settings.json`" https://code.claude.com/docs/en/plugins/components#hooks
[^root]: "Each version has its own cache directory, so the path changes when the plugin updates. Don't write state there" https://code.claude.com/docs/en/plugins/components#reference-plugin-paths-and-store-data
[^data]: "a directory that survives updates, for `node_modules`, virtual environments, and caches" https://code.claude.com/docs/en/plugins/components#reference-plugin-paths-and-store-data
[^autoupdate]: "every other marketplace, including the community marketplace, third-party marketplaces, and local development marketplaces" https://code.claude.com/docs/en/plugins/install#keep-plugins-updated
[^session-keeps]: "The running session keeps the versions it already loaded." https://code.claude.com/docs/en/plugins/install#keep-plugins-updated
[^skills-missing]: "The `skills/` directory is inside `.claude-plugin/`, or a `skills` entry in the manifest points at a file." https://code.claude.com/docs/en/plugins/create#the-plugin-loads-but-its-skills-are-missing
[^mp-root]: "If you point it at a marketplace root instead, Claude Code doesn't read `marketplace.json`, so a plugin under `plugins/` doesn't load, and you see no error." https://code.claude.com/docs/en/plugins/create#plugin-dir-at-a-marketplace-root-doesnt-load-the-plugins-under-plugins
[^no-claude-md]: "Claude Code doesn't load a `CLAUDE.md` at the plugin root" https://code.claude.com/docs/en/plugins/components#skills
[^manifest-only]: "Only `plugin.json` goes inside `.claude-plugin/`. Components saved there don't load." https://code.claude.com/docs/en/plugins/create#plugin-layout
