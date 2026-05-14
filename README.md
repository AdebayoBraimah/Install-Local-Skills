# Install-Local-Skills

Batch installs agent skills locally from [skills.sh](https://skills.sh).

The `install-skills.sh` script uses `npx skills add` to install every skill defined in its built-in registry in a single run. Skills are installed globally (`--global`) for **claude-code** and **antigravity** agents. It also installs any required MCP servers, Claude Code plugins, Codex plugins, and npm global dependencies.

The script runs **nine always-on installation phases**:

1. **Agent skills** — via `npx skills add`
2. **Claude MCP servers** — via `claude mcp add`
3. **Codex MCP servers** — via `codex mcp add` (same servers, shared registry)
4. **npm global packages** — via `npm install -g`
5. **Agents-only copy skills** — copy to `~/.agents/skills/` only (no symlinks)
6. **Claude-only copy skills** — copy to `~/.claude/skills/` only
7. **Shared copy skills** — copy to `~/.agents/skills/` + symlinks to `~/.claude/skills/` and `~/.gemini/antigravity/skills/`
8. **Claude Code plugins** — via `claude plugin marketplace add` + `claude plugin install`
9. **Codex plugins** — via shallow repo clone + `~/.codex/config.toml` enablement

When `--local` is passed, **four additional phases** run:

- **Local agent skills** — via `npx skills add`
- **Local pip packages** — via `pip install`
- **Local copy skills** — copy + symlinks
- **Local Claude-only copy skills** — copy to `~/.claude/skills/` only

When `--math` is passed, **one additional phase** runs:

- **Math copy skills** — copy + symlinks (`mathematician`, `mathematician-ai-ml`)

`--math` is independent of `--local`; either or both may be passed.

> **Note:** Phase 1 requires `npx`. Phases 2 and 8 require the `claude` CLI. Phases 3 and 9 require the `codex` CLI. The `--local` pip phase requires `pip`. The `--math` phase requires Lean 4 + Lake on PATH for runtime verification (not auto-installed). Missing CLIs cause the corresponding phases to be skipped. codex and gemini are universal agents and are already handled by `skills.sh` — no extra steps needed.

## Prerequisites

- [Node.js](https://nodejs.org/) (provides `npx`)
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (optional — required for Claude MCP servers and plugin installation)
- [Codex CLI](https://developers.openai.com/codex/cli/) (optional — required for Codex MCP server and plugin installation)
- [Python pip](https://pip.pypa.io/) (optional — required for `--local` pip package installation)
- [draw.io Desktop](https://github.com/jgraph/drawio-desktop) (optional — required for the `drawio` local skill)
- [Lean 4 + Lake (via elan)](https://leanprover.github.io/) (optional — required only for `--math`; see [Installing Lean 4 + Lake](#installing-lean-4--lake) below. Mathlib is required for the `mathematician-ai-ml` skill's full feature set.)
- Python ≥3.10 on PATH (conda envs OK; `which python` is consulted first) — required for `--repo-tools`.
- Node.js ≥22 — required by GitNexus under `--repo-tools` (the rest of the script works with older Node).
- `jq` — required only for Antigravity IDE MCP registration under `--repo-tools`; install via `brew install jq` on macOS. Other agents work without it.
- Optional CLIs that `--repo-tools` wires up: `claude`, `codex`, `gemini`. Missing CLIs are skipped with yellow warnings, not failures.
- Optional: Xcode Command Line Tools on macOS for GitNexus's Tree-sitter postinstall; set `GITNEXUS_SKIP_OPTIONAL_GRAMMARS=1` to skip the optional grammar build.
- If this is your **first time** installing skills, run the interactive install once so that `npx` can set things up:

  ```bash
  npx skills add https://github.com/vercel-labs/skills --skill find-skills
  ```

## Cloning with Submodules

This repo vendors two skills as git submodules under `submodules/`:

| Submodule | Skill | Why vendored |
|---|---|---|
| `submodules/get-shit-done-skills` | `gsd` | Patched fork of `ctsstc/get-shit-done-skills` — fixes a secret-leak in `agents/codebase-mapper/SKILL.md` |
| `submodules/claude-deep-research-skill` | `deep-research-academic` | Pinned to a known commit for reproducible installs of `AdebayoBraimah/claude-deep-research-skill` |

Clone with submodules so both skills install correctly:

```bash
git clone --recurse-submodules https://github.com/AdebayoBraimah/Install-Local-Skills.git
```

If you already cloned without `--recurse-submodules`:

```bash
git submodule update --init --recursive
```

To pull future updates from a vendored fork:

```bash
# get-shit-done-skills
git submodule update --remote submodules/get-shit-done-skills
git add submodules/get-shit-done-skills
git commit -m "MNT: Bumped get-shit-done-skills submodule"

# claude-deep-research-skill
git submodule update --remote submodules/claude-deep-research-skill
git add submodules/claude-deep-research-skill
git commit -m "MNT: Bumped claude-deep-research-skill submodule"
```

If a submodule is left uninitialized, `install-skills.sh` skips the corresponding skill. For `gsd`, the script additionally **removes any previously installed upstream `gsd`** so users do not keep running the leaky version. For `deep-research-academic`, any prior install is left untouched.

## Usage

```bash
# Clone the repo (recurse-submodules pulls the vendored skill forks)
git clone --recurse-submodules https://github.com/AdebayoBraimah/Install-Local-Skills.git
cd Install-Local-Skills

# Make the script executable (one-time)
chmod +x install-skills.sh

# Install all skills (always-on phases only)
./install-skills.sh

# Install all skills including local-only skills
./install-skills.sh --local

# Install all skills including math skills (requires Lean + Lake)
./install-skills.sh --math

# Install everything (local + math)
./install-skills.sh --local --math

# Install repo-analysis tools (Graphify + GitNexus)
./install-skills.sh --repo-tools

# Combined: local skills + repo tools
./install-skills.sh --local --repo-tools

# Print the help menu
./install-skills.sh --help
```

## Runtime Examples

Running the script prints a progress banner, per-skill status, and a final summary:

```
==========================================
 Installing 18 Agent Skills
 Agents: claude-code, antigravity
==========================================

Installing: skill-creator  (from anthropics/skills)
  -> skill-creator installed successfully

Installing: find-skills  (from vercel-labs/skills)
  -> find-skills installed successfully

...

==========================================
 All 18 skills installed successfully!
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
1 Codex plugin(s) failed to install:
   - github@openai-curated
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
| Research | `deep-research-academic` | submodules/claude-deep-research-skill (vendored fork of AdebayoBraimah/claude-deep-research-skill) |
| Research | `research-paper-writer` | ailabs-393/ai-labs-claude-skills |
| Research | `web-research` | langchain-ai/deepagents |
| Research | `research-engineer` | davila7/claude-code-templates |
| Diagrams | `mermaid-diagrams` | softaworks/agent-toolkit |
| Diagrams | `excalidraw` | ooiyeefei/ccc |
| Visualization | `data-visualization` | anthropics/knowledge-work-plugins |
| Documentation | `context7` | intellectronica/agent-skills |
| Writing | `humanizer` | davila7/claude-code-templates |
| CLI | `cli-anything` | hkuds/cli-anything |
| Project management | `gsd` | submodules/get-shit-done-skills (patched fork of ctsstc/get-shit-done-skills) |

## Claude Code Plugins

Plugins extend Claude Code with additional capabilities beyond skills. They are installed via the `claude plugin` CLI.

| Plugin | Marketplace | Source | Description |
|---|---|---|---|
| `codex` | openai-codex | openai/codex-plugin-cc | Codex code review and task delegation |
| `ccc-skills` | ccc | ooiyeefei/ccc | Skills collection (excalidraw, streak) |

> **Notes:**
>
> - After installation, run `/codex:setup` inside Claude Code to verify Codex CLI readiness and complete authentication. Use `/codex:setup --enable-review-gate` to enable a stop-time review gate that requires Codex to review your changes before Claude Code completes a task. You will also need a [ChatGPT subscription or OpenAI API key](https://developers.openai.com/codex/pricing).
> - The `ccc-skills` plugin installs the excalidraw diagram generator and the streak challenge tracker as Claude Code skills.

## Codex Plugins

Codex plugins are tracked separately from Claude Code plugins. The script installs them from the `CODEX_PLUGINS` registry by:

1. cloning the source repo at shallow depth
2. copying the plugin directory into `~/.codex/plugins/cache/<marketplace>/<plugin>/<commit-sha>/`
3. enabling the plugin in `~/.codex/config.toml`

The default Codex plugin registry currently includes:

| Plugin | Marketplace | Source | Plugin Path |
|---|---|---|---|
| `github` | `openai-curated` | openai/plugins | `plugins/github` |

> **Note:** The Codex CLI on this setup does not expose a `plugin install` command, so the installer uses Codex's local cache and config layout directly.

## npm Global Dependencies

Some skills and plugins require globally installed npm packages. These are installed automatically via `npm install -g`.

| Package | Required by |
|---|---|
| `@mermaid-js/mermaid-cli` | mermaid-diagrams |
| `@openai/codex` | codex plugin |

## Bundled Copy Skills

Skills bundled in the `skills/` directory of this repo that are always installed (no `--local` flag required). Each skill targets a specific agent directory.

### Agents-Only Skills

Copied into `~/.agents/skills/` only. No symlinks are created — these are available to agents that read from `~/.agents/skills/` directly.

| Category | Skill | Source | Description |
|---|---|---|---|
| Planning | `plan-review-cdx` | `skills/plan-review-cdx/` | Two-reviewer QA loop for Codex (spec + execution reviewers) |

### Claude-Only Skills

Copied directly into `~/.claude/skills/` only. These are exclusive to Claude Code.

| Category | Skill | Source | Description |
|---|---|---|---|
| Planning | `plan-review` | `skills/plan-review/` | Two-reviewer QA loop with default Claude+Codex pairing and a `claude-only` fallback (auto-engaged when Codex is unavailable, e.g. on HPC SLURM nodes) |

### Shared Skills

Copied into `~/.agents/skills/` AND symlinked into `~/.claude/skills/` and `~/.gemini/antigravity/skills/`. Always installed.

| Category | Skill | Source | Description |
|---|---|---|---|
| Visualization | `data-viz` | `skills/data-viz/` | Customized variant of upstream `data-visualization` extended for ML, statistical, high-dimensional, scalable, and publication workflows. Both skills are installed; trigger by name. |
| Research engineering | `research-engineer-ai-ml` | `skills/research-engineer-ai-ml/` | AI/ML research engineering: reproducible experiments, baselines/ablations, PyTorch/JAX implementation plans |

> **Note:** `gsd` is conditionally appended to the shared copy-skills set from the patched submodule at `submodules/get-shit-done-skills/.kilocode/skills/gsd`. See [Cloning with Submodules](#cloning-with-submodules) — if the submodule is not initialized, the install script skips `gsd` and removes any stale upstream-installed copy.

> **Note:** `deep-research-academic` is conditionally appended to the shared copy-skills set from the submodule at `submodules/claude-deep-research-skill`. See [Cloning with Submodules](#cloning-with-submodules) — if the submodule is not initialized, the install script skips it and leaves any prior install untouched.

> **Note:** `mathematician-ai-ml-workspace` (under `~/.agents/skills/`) is a Lean scratch workspace, not a skill — intentionally excluded from bundling.

## Math Skills (`--math`)

Installed only when `--math` is passed. The flag is independent of `--local`; either or both may be passed.

| Category | Skill | Source | Description |
|---|---|---|---|
| Mathematics | `mathematician` | `skills/mathematician/` | Mathematical reasoning, theorem proving, Lean 4 formalization, proof checking |
| Mathematics | `mathematician-ai-ml` | `skills/mathematician-ai-ml/` | AI/ML-specific mathematical reasoning with Mathlib-aware Lean formalization |

> **Prerequisites for `--math`:** Lean 4 and Lake on PATH (install via [elan](https://leanprover.github.io/)). Mathlib is required for the `mathematician-ai-ml` skill's full feature set. The script does **not** auto-install these — the bundled skills run their own `lean --version` / `lake --version` runtime checks and fall back to informal mathematics when Lean is unavailable.

### Installing Lean 4 + Lake

Lean 4 and Lake are installed together via [elan](https://github.com/leanprover/elan), the official Lean version manager. `elan` provisions the `lean`, `lake`, and `leanc` binaries on PATH and pins the toolchain per-project from a `lean-toolchain` file (so Mathlib-based projects get the exact compiler they need).

#### macOS / Linux

```bash
# Install elan (non-interactive, default toolchain = stable)
curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
  | sh -s -- -y --default-toolchain leanprover/lean4:stable

# Add elan to your current shell (new shells pick this up automatically via ~/.profile)
source "$HOME/.elan/env"

# Important for reproducibility
elan default leanprover/lean4:stable

# Verify
lean --version
lake --version
elan show
```

If your shell does not source `~/.profile` automatically (e.g. zsh on macOS), add this to `~/.zshrc`:

```bash
. "$HOME/.elan/env"
```

#### Windows

Download and run [`elan-init.exe`](https://github.com/leanprover/elan/releases/latest) from the elan releases page, or via PowerShell:

```powershell
curl -L -o elan-init.exe https://github.com/leanprover/elan/releases/latest/download/elan-init-x86_64-pc-windows-msvc.exe
./elan-init.exe -y --default-toolchain leanprover/lean4:stable
```

Open a new terminal and run `lean --version` and `lake --version` to verify.

#### Homebrew (macOS, alternative)

```bash
brew install elan-init
elan default leanprover/lean4:stable
```

#### Pinning a toolchain

Inside any Lake project, the file `lean-toolchain` controls which Lean version is used. The first time you run `lake build` (or `lake exe cache get`) inside a project, elan downloads the pinned toolchain automatically. To switch the global default:

```bash
elan default leanprover/lean4:stable    # latest stable
elan default leanprover/lean4:nightly   # latest nightly (Mathlib head tracks this)
elan toolchain list                     # show installed toolchains
```

#### Mathlib

Mathlib is provided per-project, not globally. The `mathematician-ai-ml` skill bootstraps a scratch workspace at `~/lean-ai-ml-math/AIMLMath` on first use via:

```bash
~/.agents/skills/mathematician-ai-ml/scripts/init_aiml_workspace.sh
```

Internally this runs `lake new AIMLMath math.lean` (the Mathlib-aware template) and then `lake exe cache get` to pull pre-built Mathlib oleans (avoids a multi-hour local build). Re-run `lake exe cache get` inside the project whenever you bump the Mathlib revision.

To create a new Mathlib project manually:

```bash
lake new my-project math.lean
cd my-project
lake exe cache get
lake build
```

#### Uninstalling

```bash
elan self uninstall
```

This removes `~/.elan/`, all installed toolchains, and the PATH shim.

## Repo Tools (`--repo-tools`)

Installed only when `--repo-tools` is passed. The flag is independent of `--local` and `--math`; any combination may be passed. Repo tools are code-intelligence packages that ship via PyPI / npm (not skill registries), and they need explicit MCP / skill registration for each agent runtime — this flag automates that wiring with zero human intervention.

| Tool | Package | Source | Description |
|---|---|---|---|
| [Graphify](https://graphify.net/#features) | `graphifyy[mcp]` (pip) | [PyPI](https://pypi.org/project/graphifyy/) | Builds queryable code knowledge graphs; installs global skill files for Claude Code, Codex, Gemini CLI, and Antigravity. |
| [GitNexus](https://github.com/abhigyanpatwari/GitNexus) | `gitnexus` (npm) | [npm](https://www.npmjs.com/package/gitnexus) | 16-tool code-intelligence MCP server, exposed via `gitnexus mcp`. |

What gets installed:

- **Graphify** via `python -m pip install graphifyy[mcp]` using the highest-priority interpreter detected by `which python` (so an activated conda env wins) that satisfies Python ≥3.10.
- Graphify global skill files for each agent via the documented platform commands: `graphify install` (Claude Code), `graphify install --platform codex` (Codex), and `graphify install --platform gemini` (Gemini CLI, run from a temp directory that is removed afterward to avoid project-local writes).
- Antigravity global Graphify skill: the installer copies Graphify's packaged `skill.md` into `~/.agents/skills/graphify/SKILL.md`, prepending an Antigravity-compatible frontmatter. The documented `graphify antigravity install` command is intentionally **not** invoked here because it mutates the current project; treat it as a per-project bootstrap step in target repos.
- Codex Graphify enablement: `[features].multi_agent = true` is added to `~/.codex/config.toml` idempotently. This is required by Graphify's Codex parallel extraction.
- **GitNexus** via `npm install -g gitnexus` (Node ≥22 required).
- **GitNexus MCP** registration for all four runtimes from `REPO_TOOL_MCP_SERVERS`:
  - Claude Code: `claude mcp add -s user gitnexus -- npx -y gitnexus@latest mcp`
  - Codex: `codex mcp add gitnexus -- npx -y gitnexus@latest mcp`
  - Gemini CLI: `gemini mcp add --scope user gitnexus npx -y gitnexus@latest mcp`
  - Antigravity IDE: idempotent `jq` merge into `~/.gemini/antigravity/mcp_config.json` (preserves other keys, no duplicates on re-run).
- GitNexus MCP runs on demand via `npx -y gitnexus@latest mcp`; the first cold start downloads the package.

> **Not part of global install:** `graphify extract`, `graphify gemini install`, `graphify antigravity install`, and `gitnexus analyze` are per-repo bootstrap commands the user runs inside target projects.

> **Choosing between them:** See [docs/repo-tools-guide.md](docs/repo-tools-guide.md) for a comparison of Graphify vs GitNexus and which to reach for during repo init and maintenance (TL;DR: GitNexus as the primary context engine for agentic monorepo coding; Graphify as a complementary multimodal documentation/research layer).

### Verifying Repo Tools

After running `./install-skills.sh --repo-tools`:

```bash
# 1. Help text mentions the new flag
./install-skills.sh --help | grep -- --repo-tools

# 2. Graphify installed and globally registered
which graphify                       # should resolve
graphify --version                   # prints a version
grep -A5 '^\[features\]' ~/.codex/config.toml | grep 'multi_agent = true'
test -f ~/.agents/skills/graphify/SKILL.md
# Repo should NOT be mutated by Graphify Gemini install:
test ! -e ./GEMINI.md
test ! -e ./.gemini/settings.json
test ! -e ./.agents/rules/graphify.md
test ! -e ./.agents/workflows/graphify.md

# 3. GitNexus installed
which gitnexus
gitnexus --version

# 4. GitNexus MCP registered for each runtime
claude mcp list | grep gitnexus       # Claude Code (user scope)
codex  mcp list | grep gitnexus       # Codex
gemini mcp list | grep gitnexus       # Gemini CLI (user scope, if gemini CLI present)
jq '.mcpServers.gitnexus' ~/.gemini/antigravity/mcp_config.json   # Antigravity (if installed)

# 5. Smoke-test the MCP server (Ctrl-C after the handshake prints)
npx -y gitnexus@latest mcp

# 6. Re-running is idempotent. Antigravity merge is a jq assignment, never a duplicate.
./install-skills.sh --repo-tools
jq '.mcpServers | keys' ~/.gemini/antigravity/mcp_config.json
```

## Local-Only Skills (`--local`)

These skills are only installed when the `--local` flag is passed. They may have additional dependencies (e.g. Python packages) that are not needed by the default skill set.

### Remote Skills

Installed via `npx skills add` (same as standard skills, but only with `--local`).

| Category | Skill | Source |
|---|---|---|
| Research | `notebooklm` | teng-lin/notebooklm-py |
| Diagrams | `drawio` | bahayonghang/drawio-skills |

### Local Copy Skills

Skills bundled in the `skills/` directory of this repo. These are copied into `~/.agents/skills/` and symlinked to agent directories (`~/.claude/skills/`, `~/.gemini/antigravity/skills/`).

| Category | Skill | Source | Description |
|---|---|---|---|
| Image & vector graphics | `gimp` | `skills/gimp/` | Image manipulation via GIMP CLI |
| Image & vector graphics | `inkscape` | `skills/inkscape/` | Vector graphics manipulation via Inkscape CLI |

### pip Dependencies (local)

Local skills may require Python packages. These are installed automatically via `pip install` when `--local` is used.

| Package | Required by |
|---|---|
| `notebooklm-py[browser]` | notebooklm |
| `playwright` | notebooklm |

> **Notes:**
>
> - After `playwright` is installed, `playwright install chromium` is run automatically to download the Chromium browser binary.
> - After installation, authenticate with NotebookLM (first time only, opens browser):
>
>   ```bash
>   notebooklm login
>   ```
>
> - See the [notebooklm-py documentation](https://github.com/teng-lin/notebooklm-py?tab=readme-ov-file) for full usage details.
> - The `drawio` skill requires the [draw.io Desktop](https://github.com/jgraph/drawio-desktop) application to be installed.

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

## Adding or Removing Codex Plugins

Edit the `CODEX_PLUGINS` array at the top of `install-skills.sh`. Each Codex plugin is a quartet — a source repo, a plugin name, a marketplace name, and the plugin path inside the repo:

```bash
CODEX_PLUGINS=(
  "owner/repo"  "plugin-name"  "marketplace-name"  "plugins/plugin-name"
)
```

To **add** a Codex plugin, append a new quartet. To **remove** one, delete all four values.

## Adding or Removing Copy Skills

There are five copy skill arrays, each targeting a different destination and gated by a different flag. Place the skill directory under `skills/` in this repo, then add an entry to the appropriate array in `install-skills.sh`:

| Array | Target | Symlinks | Flag |
|---|---|---|---|
| `AGENTS_COPY_SKILLS` | `~/.agents/skills/` | none | always |
| `CLAUDE_COPY_SKILLS` | `~/.claude/skills/` | none | always |
| `COPY_SKILLS` | `~/.agents/skills/` | `~/.claude/skills/`, `~/.gemini/antigravity/skills/` | always |
| `LOCAL_COPY_SKILLS` | `~/.agents/skills/` | `~/.claude/skills/`, `~/.gemini/antigravity/skills/` | `--local` |
| `LOCAL_CLAUDE_COPY_SKILLS` | `~/.claude/skills/` | none | `--local` |
| `MATH_COPY_SKILLS` | `~/.agents/skills/` | `~/.claude/skills/`, `~/.gemini/antigravity/skills/` | `--math` |

> **Repo as source of truth:** Each install run overwrites the matching `~/.agents/skills/<name>/` entries with the bundled copies in this repo. To promote a local edit back into the repo, copy from `~/.agents/skills/<name>/` into `skills/<name>/`, re-run the path-portability rewrite, and commit. Skills are overwritten only when their gating flag matches:
>
> - Always overwritten: `data-viz`, `research-engineer-ai-ml` (`COPY_SKILLS`); `plan-review-cdx` (`AGENTS_COPY_SKILLS`); `plan-review` (`CLAUDE_COPY_SKILLS`).
> - Overwritten only with `--local`: `gimp`, `inkscape` (`LOCAL_COPY_SKILLS`).
> - Overwritten only with `--math`: `mathematician`, `mathematician-ai-ml` (`MATH_COPY_SKILLS`).

Each entry is a pair — a source path and a skill name:

```bash
AGENTS_COPY_SKILLS=(
  "${SCRIPT_DIR}/skills/my-skill"    "my-skill"
)
```

## Adding or Removing Repo Tools

The `--repo-tools` flag is driven by three arrays at the top of `install-skills.sh`:

```bash
# Single pip package name per entry
REPO_TOOL_PIP_PACKAGES=(
  "graphifyy[mcp]"
)

# Single npm package name per entry
REPO_TOOL_NPM_GLOBALS=(
  "gitnexus"
)

# Triplet: <name> <scope> <command...> — used for Claude, Codex, Gemini,
# and Antigravity. Codex ignores scope; command tokens are whitespace-split.
REPO_TOOL_MCP_SERVERS=(
  "gitnexus" "user" "npx -y gitnexus@latest mcp"
)
```

To **add** a repo tool, append to whichever arrays match its packaging (pip / npm / MCP). To **remove** one, delete the matching lines from each array (preserve the stride: 1 line per pip/npm entry, 3 lines per MCP entry).

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
