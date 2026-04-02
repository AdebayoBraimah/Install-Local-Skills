# Install-Local-Skills

Batch installs agent skills locally from [skills.sh](https://skills.sh).

The `install-skills.sh` script uses `npx skills add` to install every skill defined in its built-in registry in a single run. Skills are installed globally (`--global`) for **claude-code** and **antigravity** agents. It also installs any required MCP servers, Claude Code plugins, and npm global dependencies via the `claude` CLI.

The script runs five installation phases in order:

1. **Agent skills** — via `npx skills add`
2. **Claude MCP servers** — via `claude mcp add`
3. **Codex MCP servers** — via `codex mcp add` (same servers, shared registry)
4. **npm global packages** — via `npm install -g`
5. **Claude Code plugins** — via `claude plugin marketplace add` + `claude plugin install`

> **Note:** Phase 1 requires `npx`. Phases 2 and 5 require the `claude` CLI. Phase 3 requires the `codex` CLI. Missing CLIs cause the corresponding phases to be skipped. codex and gemini are universal agents and are already handled by `skills.sh` — no extra steps needed.

## Prerequisites

- [Node.js](https://nodejs.org/) (provides `npx`)
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (optional — required for Claude MCP servers and plugin installation)
- [Codex CLI](https://developers.openai.com/codex/cli/) (optional — required for Codex MCP server installation)
- [Python pip](https://pip.pypa.io/) (optional — required for `--local` pip package installation)
- If this is your **first time** installing skills, run the interactive install once so that `npx` can set things up:

  ```bash
  npx skills add https://github.com/vercel-labs/skills --skill find-skills
  ```

## Usage

```bash
# Clone the repo
git clone https://github.com/AdebayoBraimah/Install-Local-Skills.git
cd Install-Local-Skills

# Make the script executable (one-time)
chmod +x install-skills.sh

# Install all skills
./install-skills.sh

# Install all skills including local-only skills
./install-skills.sh --local

# Print the help menu
./install-skills.sh --help
```

## Runtime Examples

Running the script prints a progress banner, per-skill status, and a final summary:

```
==========================================
 Installing 17 Agent Skills
 Agents: claude-code, antigravity
==========================================

Installing: skill-creator  (from anthropics/skills)
  -> skill-creator installed successfully

Installing: find-skills  (from vercel-labs/skills)
  -> find-skills installed successfully

...

==========================================
 All 17 skills installed successfully!
==========================================

Installed skills can be listed with: npx skills list --global
```

If any skills, MCP servers, npm packages, or plugins fail, the summary lists them and the script exits with a non-zero status:

```
==========================================
 2 skill(s) failed to install:
   - deep-research
   - ntfy-notify
 1 Claude Code plugin(s) failed to install:
   - codex@openai-codex
==========================================
```

## Included Skills

| Category | Skill | Source |
|---|---|---|
| Core / utility | `skill-creator` | anthropics/skills |
| Core / utility | `find-skills` | vercel-labs/skills |
| Planning | `writing-plans` | obra/superpowers |
| Planning | `brainstorming` | obra/superpowers |
| Code review | `deep-review` | coder/mux |
| Notifications | `ntfy-notify` | gitstua/stu-skills |
| Research | `deep-research` | shubhamsaboo/awesome-llm-apps |
| Research | `academic-researcher` | shubhamsaboo/awesome-llm-apps |
| Research | `deep-research-academic` | AdebayoBraimah/claude-deep-research-skill |
| Research | `research-paper-writer` | ailabs-393/ai-labs-claude-skills |
| Research | `web-research` | langchain-ai/deepagents |
| Research | `research-engineer` | davila7/claude-code-templates |
| Diagrams | `mermaid-diagrams` | softaworks/agent-toolkit |
| Diagrams | `excalidraw` | ooiyeefei/ccc |
| Documentation | `context7` | intellectronica/agent-skills |
| Writing | `humanizer` | davila7/claude-code-templates |
| CLI | `cli-anything` | hkuds/cli-anything |

## Claude Code Plugins

Plugins extend Claude Code with additional capabilities beyond skills. They are installed via the `claude plugin` CLI.

| Plugin | Marketplace | Source | Description |
|---|---|---|---|
| `codex` | openai-codex | openai/codex-plugin-cc | Codex code review and task delegation |
| `ccc-skills` | ccc | ooiyeefei/ccc | Skills collection (excalidraw, streak) |

> **Notes:**
> - After installation, run `/codex:setup` inside Claude Code to verify Codex CLI readiness and complete authentication. Use `/codex:setup --enable-review-gate` to enable a stop-time review gate that requires Codex to review your changes before Claude Code completes a task. You will also need a [ChatGPT subscription or OpenAI API key](https://developers.openai.com/codex/pricing).
> - The `ccc-skills` plugin installs the excalidraw diagram generator and the streak challenge tracker as Claude Code skills.

## npm Global Dependencies

Some skills and plugins require globally installed npm packages. These are installed automatically via `npm install -g`.

| Package | Required by |
|---|---|
| `@mermaid-js/mermaid-cli` | mermaid-diagrams |
| `@openai/codex` | codex plugin |


## Local-Only Skills (`--local`)

These skills are only installed when the `--local` flag is passed. They may have additional dependencies (e.g. Python packages) that are not needed by the default skill set.

| Category | Skill | Source |
|---|---|---|
| Research | `notebooklm` | teng-lin/notebooklm-py |
| Diagrams | `drawio` | bahayonghang/drawio-skills |

### pip Dependencies (local)

Local skills may require Python packages. These are installed automatically via `pip install` when `--local` is used.

| Package | Required by |
|---|---|
| `notebooklm-py[browser]` | notebooklm |
| `playwright` | notebooklm |

> **Notes:**
> - After `playwright` is installed, `playwright install chromium` is run automatically to download the Chromium browser binary.
> - After installation, authenticate with NotebookLM (first time only, opens browser):
>   ```bash
>   notebooklm login
>   ```
> - See the [notebooklm-py documentation](https://github.com/teng-lin/notebooklm-py?tab=readme-ov-file) for full usage details.

## Adding or Removing Skills

Edit the `SKILLS` array at the top of `install-skills.sh`. Each skill is a pair of lines — a repo and a skill name:

```bash
SKILLS=(
  "owner/repo"       "skill-name"
  "owner/other-repo" "another-skill"
)
```

To **add** a skill, append a new repo/name pair. To **remove** one, delete both lines.

## Adding or Removing Plugins

Edit the `PLUGINS` array at the top of `install-skills.sh`. Each plugin is a triplet — a marketplace source, a plugin identifier, and a marketplace name:

```bash
PLUGINS=(
  "owner/repo"    "plugin@marketplace"    "marketplace-name"
)
```

To **add** a plugin, append a new triplet. To **remove** one, delete all three values.

## Updating the Script

Pull the latest changes from the repository:

```bash
cd Install-Local-Skills
git pull origin main
```

Then re-run the script to pick up any newly added skills:

```bash
./install-skills.sh
```

## Listing Installed Skills

After installation, you can verify what's installed:

```bash
npx skills list --global
```
