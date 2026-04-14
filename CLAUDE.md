# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Batch installer for agent skills, MCP servers, plugins, and dependencies. A single bash script (`install-skills.sh`) drives all installation using array-based registries. Target agents: **claude-code** and **antigravity** (codex and gemini are universal and handled by skills.sh automatically).

## Usage

```bash
./install-skills.sh          # Install all standard components
./install-skills.sh --local  # Also install local-only skills, pip deps, and local copy skills
./install-skills.sh --help   # Print help
```

Prerequisites: Node.js (provides `npx`). Optional: `claude` CLI, `codex` CLI, `pip`. Missing CLIs cause their phases to be skipped gracefully.

## Architecture

The script has one file (`install-skills.sh`) with two main sections:

### Registry Arrays (top of file)

All installable components are defined as bash arrays with fixed-stride element patterns:

| Array | Stride | Elements per entry | Flag |
|---|---|---|---|
| `SKILLS` | 2 | `repo`, `skill-name` | always |
| `MCP_SERVERS` | 3 | `name`, `scope`, `command` | always |
| `NPM_GLOBALS` | 1 | `package-name` | always |
| `PLUGINS` | 3 | `marketplace-source`, `plugin-id`, `marketplace-name` | always |
| `CODEX_PLUGINS` | 4 | `source-repo`, `plugin-name`, `marketplace-name`, `plugin-path` | always |
| `LOCAL_SKILLS` | 2 | `repo`, `skill-name` | `--local` |
| `LOCAL_PIP_PACKAGES` | 1 | `package-name` | `--local` |
| `LOCAL_COPY_SKILLS` | 2 | `source-path`, `skill-name` | `--local` |

To add/remove a component, edit the corresponding array. Maintain the correct stride (e.g., delete both lines of a skill pair, all three lines of a plugin triplet).

Repos can be `owner/repo` shorthand or full git URLs. The `repo_to_git_url()` helper normalizes both forms.

### Installation Functions + Main

Each array has a corresponding `install_*()` function. The `main()` function parses args, checks dependencies, iterates each registry, and prints a summary. Failed items are tracked in `FAILED_*` arrays and reported at exit.

### Installation Phases (execution order)

1. Agent skills (`npx skills add --global --yes`)
2. Claude MCP servers (`claude mcp add`)
3. Codex MCP servers (`codex mcp add`)
4. npm global packages (`npm install -g`)
5. Local pip packages (`pip install`) — `--local` only
6. Local copy skills (copy to `~/.agents/skills/` + symlink) — `--local` only
7. Claude Code plugins (marketplace add + plugin install)
8. Codex plugins (shallow clone + cache copy + config.toml enablement)

### Skill Installation Directories

Skills installed via `npx skills add` land in `~/.agents/skills/<name>/` (canonical), with relative symlinks created at:
- `~/.claude/skills/<name>` → `../../.agents/skills/<name>`
- `~/.gemini/antigravity/skills/<name>` → `../../../.agents/skills/<name>`

The `LOCAL_COPY_SKILLS` mechanism replicates this same pattern for skills bundled in the repo under `skills/`.

### Codex Plugin Installation

Codex has no native `plugin install` command. The script manually:
1. Shallow-clones the source repo
2. Copies the plugin into `~/.codex/plugins/cache/<marketplace>/<plugin>/<commit-sha>/`
3. Enables it in `~/.codex/config.toml` via an `awk`-based `enable_codex_plugin()` function

### Local Copy Skills (`skills/` directory)

Skills bundled in this repo live under `skills/<skill-name>/`. These are copied into `~/.agents/skills/` and symlinked to agent directories when `--local` is passed. Source paths in the `LOCAL_COPY_SKILLS` array use `${SCRIPT_DIR}` for portability across machines.

## Git Rules

- **No co-author tags**: NEVER append "Co-Authored-By" (or any variation) to commit messages.
- **Never stage or commit CLAUDE.md or AGENTS.md**: These files must never be added to git staging or included in any commit.
- **Never push to remote**: Do NOT run `git push` unless explicitly instructed by the user.

## Commit Convention

See `contributing.md`. Prefix with category, past-tense, 8-12 words max:

```
ENH: Added mermaid-diagrams skill to registry
DOC: Updated README with local copy skills section
BF: Fixed symlink path for gemini antigravity directory
```

Prefixes: BF, RF, ENH, BW, OPT, BK, DOC, TEST, MNT, CI, STY, BLD, OPS, CHORE, API, DEV, REV, MERGE. Breaking changes use `!` (e.g., `ENH!:`).
