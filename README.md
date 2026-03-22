# Install-Local-Skills

Batch installs agent skills locally from [skills.sh](https://skills.sh).

The `install-skills.sh` script uses `npx skills add` to install every skill defined in its built-in registry in a single run. Skills are installed globally (`--global`) for **claude-code** and **antigravity** agents. It also installs any required MCP servers via the `claude` CLI.

> **Note:** codex and gemini are universal agents and are already handled by `skills.sh` — no extra steps needed.

## Prerequisites

- [Node.js](https://nodejs.org/) (provides `npx`)
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (optional — required for MCP server installation)
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
 All 1 MCP server(s) installed successfully!
==========================================

Installed skills can be listed with: npx skills list --global
```

If any skills or MCP servers fail, the summary lists them and the script exits with a non-zero status:

```
==========================================
 2 skill(s) failed to install:
   - deep-research
   - ntfy-notify
 1 MCP server(s) failed to install:
   - sequential-thinking
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
| Productivity | `gsd` | ctsstc/get-shit-done-skills |
| Documentation | `context7` | intellectronica/agent-skills |
| Writing | `humanizer` | davila7/claude-code-templates |
| Reasoning | `sequential-thinking` | mrgoonie/claudekit-skills |

## Required MCP Servers

Some skills depend on MCP servers. These are installed automatically via `claude mcp add` when the `claude` CLI is available.

| MCP Server | Scope | Package |
|---|---|---|
| `sequential-thinking` | user | @modelcontextprotocol/server-sequential-thinking |

> If the `claude` CLI is not found, MCP installation is skipped with a warning.

## Adding or Removing Skills

Edit the `SKILLS` array at the top of `install-skills.sh`. Each skill is a pair of lines — a repo and a skill name:

```bash
SKILLS=(
  "owner/repo"       "skill-name"
  "owner/other-repo" "another-skill"
)
```

To **add** a skill, append a new repo/name pair. To **remove** one, delete both lines.

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
