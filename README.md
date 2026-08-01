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
7. **Shared copy skills** — copy to `~/.agents/skills/` + symlink to `~/.claude/skills/` (Gemini CLI and Antigravity IDE discover via the canonical `~/.agents/skills/` path)
8. **Claude Code plugins** — via `claude plugin marketplace add` + `claude plugin install`
9. **Codex plugins** — via shallow repo clone + `~/.codex/config.toml` enablement

When `--local` is passed, **four additional phases** run:

- **Local agent skills** — via `npx skills add`
- **Local pip packages** — via `uv pip install` (falls back to the resolved interpreter's `pip`)
- **Local copy skills** — copy + symlinks
- **Local Claude-only copy skills** — copy to `~/.claude/skills/` only

When `--math` is passed, **one additional phase** runs:

- **Math copy skills** — copy + symlinks (`mathematician`, `mathematician-ai-ml`)

`--math` is independent of `--local`; either or both may be passed.

When `--eng` (or `--engineering`) is passed, **one additional phase** runs:

- **Engineering + productivity skills** — via `npx skills add` (Matt Pocock's opinionated TDD/grill-me/triage/handoff/etc.)

`--eng` is independent of `--local`, `--math`, and `--repo-tools`; any combination may be passed.

> **Note:** Phase 1 requires `npx`. Phases 2 and 8 require the `claude` CLI. Phases 3 and 9 require the `codex` CLI. The `--local` pip phase requires `uv` or `pip`. The `--math` phase requires Lean 4 + Lake on PATH for runtime verification (not auto-installed). Missing CLIs cause the corresponding phases to be skipped. codex and antigravity are universal agents and are already handled by `skills.sh` — no extra steps needed.

> **Python installs use `uv` by default.** Before Phase 1 the script ensures `uv` is available — bootstrapping it via `pip install --user uv` (with a PEP 668 `--break-system-packages` retry) when missing — and routes every pip install through a helper that prefers `uv pip install` and falls back to the target interpreter's `pip`. It also installs [SkillSpector](https://github.com/NVIDIA/skillspector) via `uv tool install` first, then scans the installed skills after all phases complete (detection-after-fetch, so remote `npx`-fetched skills are inspected too). Both the `uv` bootstrap and the SkillSpector scan are best-effort and non-fatal.

## Prerequisites

- [Node.js](https://nodejs.org/) (provides `npx`)
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (optional — required for Claude MCP servers and plugin installation)
- [Codex CLI](https://developers.openai.com/codex/cli/) (optional — required for Codex MCP server and plugin installation)
- [Python pip](https://pip.pypa.io/) (optional — required for `--local` pip package installation; also used to bootstrap `uv` if it is missing)
- [uv](https://docs.astral.sh/uv/) (optional — the default Python installer; auto-bootstrapped via `pip` if not already on PATH)
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
| `submodules/get-shit-done-skills` | `gsd` *(no longer installed)* | Patched fork of `ctsstc/get-shit-done-skills`. `gsd` has been retired from this installer (its only consumer, the `orchestrate` skill, was removed); the checkout is left on disk but nothing installs from it. |
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

If a submodule is left uninitialized, `install-skills.sh` skips the corresponding skill. `gsd` is **no longer installed** by the script; on every run it unconditionally **removes any stale `gsd` install** (including the leaky upstream version) from `~/.agents/skills/` and `~/.claude/skills/`. For `deep-research-academic`, any prior install is left untouched.

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

# Install all skills including engineering skills
./install-skills.sh --eng

# Print the help menu
./install-skills.sh --help
```

The normal `./install-skills.sh` command installs `research-council-cdx` into
`~/.agents/skills/research-council-cdx/`; `--local` is not required. Invoke it
from a Codex session with subagents enabled, choosing the review depth explicitly
when needed:

```text
research-council-cdx quick "Review this research idea: ..."
research-council-cdx standard path/to/draft.md
research-council-cdx full path/to/repository
```

`research-council-cdx` is the Codex-native council: it uses Codex subagents for
independent reviewers, verification, and Chair synthesis. The separate
`research-council-clc` skill remains the Claude Code version and uses Claude's
Workflow orchestration.

The normal install also includes the Codex-native GR code-intelligence suite:

```text
gr-ask-cdx "How does request authentication reach the session store?"
gr-review-cdx --base main
gr-learnings-cdx --dry-run --since 50
gr-verify-cdx --from-report path/to/gr-review.md
```

`gr-ask-cdx` answers repository questions with cited graph context;
`gr-review-cdx` reviews a working diff, branch, or PR with independent reviewer
and verifier subagents; `gr-learnings-cdx` mines recurring review standards into
`LEARNINGS.md`; and `gr-verify-cdx` tests findings in a disposable worktree. The
separate `gr-*-clc` skills remain the Claude Code variants.

## Getting Started Workflows

Start with the workflow guide that matches the project state:

- [New project workflow](docs/getting-started-new-project.md) — bootstrap a
  greenfield project, clarify intent, turn requirements into work, then build
  with TDD.
- [Existing project workflow](docs/getting-started-existing-project.md) —
  orient in a brownfield repo, index and analyze the codebase, zoom out before
  edits, diagnose unclear failures, then change safely.

Use the deeper references when you need details about individual skills or
repo-tool behavior:

- [Engineering Skills Guide: Matt Pocock's `mattpocock/skills`](docs/mattpocock-skills-guide.md)
- [Repo Tools Guide: Choosing Between Graphify and GitNexus](docs/repo-tools-guide.md)

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
| Code quality | `ponytail` | dietrichgebert/ponytail |

## MCP Servers

MCP servers are registered from the shared `MCP_SERVERS` registry for both Claude (`claude mcp add`, phase 2) and Codex (`codex mcp add`, phase 3). Each entry is a `<name> <scope> <command...>` triplet; Codex ignores the scope.

| Server | Scope | Command | Description |
|---|---|---|---|
| `codebase-memory-mcp` | `user` | `npx -y codebase-memory-mcp` | Local code-intelligence engine that builds a persistent knowledge graph of your codebase ([DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp)). 14 MCP tools, 158 languages, no API key. |

> **Note:** `claude mcp add` / `codex mcp add` register the launch command without validating it, so the first cold start (`npx` fetch of the package) happens on first use inside the agent.

### codebase-memory-mcp

[codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) is a code-intelligence MCP server that AST-parses your repository (via tree-sitter across 158 languages) into a persistent knowledge graph of functions, classes, call chains, HTTP routes, and cross-service links. It answers structural questions about a codebase in a single graph query instead of dozens of grep/read cycles — its own benchmarks report ~10× fewer tokens and ~2× fewer tool calls versus file-by-file exploration.

Everything runs **100% locally** — no API key, no Docker, no network. The graph persists to `~/.cache/codebase-memory-mcp/`, so it survives across sessions.

**What this installer does:** registers the npm-distributed server (`npx -y codebase-memory-mcp`) as a `user`-scoped MCP server for Claude Code and Codex. This is all you need to use the tools from your agent. (The project *also* ships a standalone static binary with its own `install` command that auto-configures 11 agents and adds an optional 3D graph UI / auto-index hooks — see "Optional: standalone binary" below. The two approaches are interchangeable; this script uses the lighter `npx` path.)

#### Usage

1. **Verify registration** after running `./install-skills.sh`:

   ```bash
   claude mcp list | grep codebase-memory-mcp     # Claude Code (user scope)
   codex  mcp list | grep codebase-memory-mcp     # Codex
   ```

2. **Index a project.** Open the repo in your agent and ask it, in natural language:

   > "Index this project."

   The agent calls the server's `index_repository` tool. First-time indexing of an average repo takes milliseconds to seconds; the graph is cached under `~/.cache/codebase-memory-mcp/` and a background watcher keeps it in sync on subsequent edits.

3. **Query the graph** by asking the agent normal questions — it picks the right one of the 14 tools:

   > - "What's the overall architecture of this service?" → `get_architecture`
   > - "What breaks if I change `parse_config`?" → impact / call-graph tools
   > - "Find dead code." → dead-code detection
   > - "Where is the `/users/:id` route handled, and what does it call?" → route + call tools
   > - "Show functions matching `.*Handler.*`." → `search_graph`
   > - Ad-hoc graph query: `MATCH (f:Function)-[:CALLS]->(g) WHERE f.name = 'main' RETURN g.name` → `cypher`

#### Use cases

- **Onboarding / code exploration** — get an architecture overview (languages, packages, entry points, routes, hotspots, layers) in one call.
- **Change-impact analysis** — `detect_changes` maps uncommitted git changes to affected symbols with risk classification before you refactor.
- **Call-graph & dependency tracing** — import-aware, type-inferred call resolution across files and packages.
- **Dead-code detection** — functions with zero callers (entry points excluded).
- **Semantic + structural + full-text search** — vector search (bundled embeddings, no Ollama), regex/label/degree structural filters, and BM25 FTS.
- **Cross-service linking** — HTTP/gRPC/GraphQL/tRPC route ↔ call-site matching and pub/sub channel detection.
- **Architecture Decision Records** — `manage_adr` persists decisions across sessions.

#### Instructions & configuration

- **No API key or extra setup** is required beyond the MCP registration this script performs.
- **CLI mode** (outside an agent) for quick checks:

  ```bash
  codebase-memory-mcp cli search_graph '{"name_pattern": ".*Handler.*"}'
  ```

- **Optional environment variables** (set in your shell or the agent's MCP env): `CBM_CACHE_DIR` (override the `~/.cache/codebase-memory-mcp/` graph location) and `CBM_LOG_LEVEL` (e.g. `debug`).
- **Auto-index on session start** (indexes new projects automatically): `codebase-memory-mcp config set auto_index true` (limit via `config set auto_index_limit 50000`).
- **Team-shared graph** — committing `.codebase-memory/graph.db.zst` (a zstd snapshot of the graph) lets teammates skip the first full reindex; add `.codebase-memory/` to `.gitignore` if you'd rather everyone reindex locally.
- **Optional: standalone binary** — if you prefer the native binary (faster cold start, optional 3D UI at `localhost:9749`, auto-detected config for more agents), install it directly and let it configure agents instead of the `npx` registration:

  ```bash
  curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash
  # then restart your agent; "Index this project" to begin
  ```

  Keep it current with `codebase-memory-mcp update`; remove its agent configs with `codebase-memory-mcp uninstall`.

> **Source of truth:** tool names and flags above reflect the upstream README ([DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp)) at the time of writing; check the repo for the current tool list, as the server is updated frequently.

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
| Engineering workflow | `judgement-engineering-cdx` | `skills/judgement-engineering-cdx/` | Codex judgement gate for problem framing, reversibility, and stop/go decisions before planning |
| Engineering workflow | `looped-engineering-cdx` | `skills/looped-engineering-cdx/` | Codex adaptive engineering loop for orientation, planning, execution, verification, closeout, and alerts |
| Planning | `plan-review-cdx` | `skills/plan-review-cdx/` | Two-reviewer QA loop for Codex (spec + execution reviewers) |
| Code intelligence | `gr-review-cdx` | `skills/gr-review-cdx/` | Codex graph-context code review with independent correctness, security, impact, conventions, and verification passes |
| Code intelligence | `gr-ask-cdx` | `skills/gr-ask-cdx/` | Codex repository Q&A with GitNexus context and path:line citations |
| Code intelligence | `gr-learnings-cdx` | `skills/gr-learnings-cdx/` | Codex miner for recurring, provenance-backed review rules in `LEARNINGS.md` |
| Code intelligence | `gr-verify-cdx` | `skills/gr-verify-cdx/` | Codex runtime validation of review findings in isolated worktrees |
| Literature / research | `lit-review-cdx` | `skills/lit-review-cdx/` | Codex literature review skill |
| Literature / research | `lit-summarizer-cdx` | `skills/lit-summarizer-cdx/` | Codex literature summarization skill |
| Literature / research | `lit-survey-cdx` | `skills/lit-survey-cdx/` | Codex literature survey skill |
| Literature / research | `research-council-cdx` | `skills/research-council-cdx/` | Codex-native adversarial academic review council: independent subagent reviewers with Chair synthesis and tiered quick/standard/full review |

### Claude-Only Skills

Copied directly into `~/.claude/skills/` only. These are exclusive to Claude Code.

| Category | Skill | Source | Description |
|---|---|---|---|
| Engineering workflow | `judgement-engineering-clc` | `skills/judgement-engineering-clc/` | Claude Code judgement gate for problem framing, reversibility, and stop/go decisions before planning |
| Engineering workflow | `looped-engineering-clc` | `skills/looped-engineering-clc/` | Claude Code adaptive engineering loop for orientation, planning, execution, verification, closeout, and alerts |
| Planning | `plan-review-clc` | `skills/plan-review-clc/` | Two-reviewer QA loop with default Claude+Codex pairing and a `claude-only` fallback (auto-engaged when Codex is unavailable, e.g. on HPC SLURM nodes) |
| Code intelligence | `gr-review-clc` | `skills/gr-review-clc/` | Claude graph-context code review with parallel dimension reviewers and adversarial verification |
| Code intelligence | `gr-ask-clc` | `skills/gr-ask-clc/` | Claude repository Q&A with GitNexus context and path:line citations |
| Code intelligence | `gr-learnings-clc` | `skills/gr-learnings-clc/` | Claude miner for recurring, provenance-backed review rules in `LEARNINGS.md` |
| Code intelligence | `gr-verify-clc` | `skills/gr-verify-clc/` | Claude runtime validation of review findings in isolated worktrees |
| Literature / research | `lit-review-clc` | `skills/lit-review-clc/` | Claude literature review skill |
| Literature / research | `lit-summarizer-clc` | `skills/lit-summarizer-clc/` | Claude literature summarization skill |
| Literature / research | `lit-survey-clc` | `skills/lit-survey-clc/` | Claude literature survey skill |
| Literature / research | `research-council-clc` | `skills/research-council-clc/` | Adversarial academic review council (AI/ML + math): parallel persona reviewers via the Workflow tool with chair synthesis, tiered quick/standard/full |

### Shared Skills

Copied into `~/.agents/skills/` AND symlinked into `~/.claude/skills/`. Gemini CLI and Antigravity IDE discover skills via `~/.agents/skills/` directly. Always installed.

| Category | Skill | Source | Description |
|---|---|---|---|
| Visualization | `data-viz` | `skills/data-viz/` | Customized variant of upstream `data-visualization` extended for ML, statistical, high-dimensional, scalable, and publication workflows. Both skills are installed; trigger by name. |
| Research engineering | `research-engineer-ai-ml` | `skills/research-engineer-ai-ml/` | AI/ML research engineering: reproducible experiments, baselines/ablations, PyTorch/JAX implementation plans |
| Writing / AI detection | `pangram` | `skills/pangram/` | AI-text detection via the Pangram API |
| Writing review | `ai-anti-pattern-review` | `skills/ai-anti-pattern-review/` | Flags AI-writing anti-patterns in text (with evals + fixtures) |
| Obsidian / RAG | `obsidian-graphrag-index` | `skills/obsidian-graphrag-index/` | Scaffolds and indexes a GraphRAG pipeline over an Obsidian vault |
| Obsidian / RAG | `obsidian-llamaindex-vector-indexing` | `skills/obsidian-llamaindex-vector-indexing/` | Scaffolds and maintains a LlamaIndex vector index over an Obsidian vault |
| Notifications | `alert-me` | `skills/alert-me/` | Sends an ntfy push to topic `ab-mac` on task finish/stop (thin wrapper over `ntfy-notify`) |

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

## Engineering Skills (`--eng` / `--engineering`)

Installed only when `--eng` (or its long form `--engineering`) is passed. The flag is independent of `--local`, `--math`, and `--repo-tools`; any combination may be passed.

These are Matt Pocock's opinionated workflow skills from [`mattpocock/skills`](https://github.com/mattpocock/skills) — an "anti-failure" toolkit targeting misalignment, verbosity, broken code, and architectural decay. They are gated rather than always-on because they shape the agent's working style (TDD, adversarial grilling, PRD-first issue management), not because they're optional utilities.

| Category | Skill | Source | Description |
|---|---|---|---|
| Engineering discipline | `setup-matt-pocock-skills` | [mattpocock/skills](https://github.com/mattpocock/skills) | **Per-project bootstrap** — provisions the `## Agent skills` block in `AGENTS.md`/`CLAUDE.md` and the `docs/agents/` layout that the other 11 rely on. Run once per project before first use. |
| Engineering discipline | `tdd` | [mattpocock/skills](https://github.com/mattpocock/skills) | Red-green-refactor loop discipline |
| Engineering discipline | `diagnose` | [mattpocock/skills](https://github.com/mattpocock/skills) | Structured debugging for bugs and performance regressions |
| Engineering discipline | `grill-me` | [mattpocock/skills](https://github.com/mattpocock/skills) | Adversarial questioning to drive alignment before coding |
| Engineering discipline | `grill-with-docs` | [mattpocock/skills](https://github.com/mattpocock/skills) | Same loop, but updates the project's `CONTEXT.md` |
| Engineering discipline | `improve-codebase-architecture` | [mattpocock/skills](https://github.com/mattpocock/skills) | Identifies structural improvement opportunities |
| Engineering discipline | `triage` | [mattpocock/skills](https://github.com/mattpocock/skills) | Issue management via state machines |
| Engineering discipline | `zoom-out` | [mattpocock/skills](https://github.com/mattpocock/skills) | Adds system-wide context to a code section |
| Engineering discipline | `to-prd` | [mattpocock/skills](https://github.com/mattpocock/skills) | Converts conversations into PRDs (GitHub-issue creation is now handled by to-issues) |
| Engineering discipline | `to-issues` | [mattpocock/skills](https://github.com/mattpocock/skills) | Converts a PRD into GitHub issues (companion to `to-prd`, completes the PRD → issues pipeline) |
| Productivity | `handoff` | [mattpocock/skills](https://github.com/mattpocock/skills) | Compact current conversation into a handoff document for another agent |
| Productivity | `write-a-skill` | [mattpocock/skills](https://github.com/mattpocock/skills) | Scaffold a new skill with proper structure and progressive disclosure |

> **Cross-folder bundle (`mattpocock/skills`):** `grill-me`, `handoff`, and `write-a-skill` live under upstream `productivity/`; the remaining nine are from `engineering/`. They are grouped here for workflow coherence — the bundle is intentionally cross-folder.

> **Bootstrap reminder:** After installation, run `setup-matt-pocock-skills` **once per project** before first use of the other 11 (the bootstrap itself doesn't depend on itself). It writes the `AGENTS.md`/`CLAUDE.md` agent-skills block and `docs/agents/` layout the rest depend on; 10 of the 11 will silently degrade without it.

> **Now included (policy reversal):** `to-issues` was previously excluded "to keep the bundle scoped to discipline rather than issue tracking." That rationale has been reversed — the PRD → GitHub-issues handoff is now considered part of the discipline bundle, completing the `grill-me → to-prd → to-issues → triage` planning pipeline. Bundled with `--eng`.

> **Choosing when to invoke:** See [docs/mattpocock-skills-guide.md](docs/mattpocock-skills-guide.md) for per-skill triggers and how the 12 compose into one workflow.

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

Skills bundled in the `skills/` directory of this repo. These are copied into `~/.agents/skills/` and symlinked into `~/.claude/skills/`. Gemini CLI and Antigravity IDE discover them via the canonical `~/.agents/skills/` path.

| Category | Skill | Source | Description |
|---|---|---|---|
| Image & vector graphics | `gimp` | `skills/gimp/` | Image manipulation via GIMP CLI |
| Image & vector graphics | `inkscape` | `skills/inkscape/` | Vector graphics manipulation via Inkscape CLI |

### pip Dependencies (local)

Local skills may require Python packages. These are installed automatically when `--local` is used — via `uv pip install` against the resolved interpreter, falling back to that interpreter's `pip` (with a PEP 668 `--break-system-packages` retry) when `uv` is unavailable or refuses a non-venv target.

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
| `COPY_SKILLS` | `~/.agents/skills/` | `~/.claude/skills/` | always |
| `LOCAL_COPY_SKILLS` | `~/.agents/skills/` | `~/.claude/skills/` | `--local` |
| `LOCAL_CLAUDE_COPY_SKILLS` | `~/.claude/skills/` | none | `--local` |
| `MATH_COPY_SKILLS` | `~/.agents/skills/` | `~/.claude/skills/` | `--math` |

> **Note:** Anti-Gravity agents discover skills directly from `~/.agents/skills/`.

> **Repo as source of truth:** Each install run overwrites the matching `~/.agents/skills/<name>/` entries with the bundled copies in this repo. To promote a local edit back into the repo, copy from `~/.agents/skills/<name>/` into `skills/<name>/`, re-run the path-portability rewrite, and commit. Skills are overwritten only when their gating flag matches:
>
> - Always overwritten: `data-viz`, `research-engineer-ai-ml`, `pangram`, `ai-anti-pattern-review`, `obsidian-graphrag-index`, `obsidian-llamaindex-vector-indexing`, `alert-me` (`COPY_SKILLS`); `judgement-engineering-cdx`, `looped-engineering-cdx`, `plan-review-cdx`, `gr-*-cdx`, `lit-*-cdx`, `research-council-cdx` (`AGENTS_COPY_SKILLS`); `judgement-engineering-clc`, `looped-engineering-clc`, `plan-review-clc`, `gr-*-clc`, `lit-*-clc`, `research-council-clc` (`CLAUDE_COPY_SKILLS`).
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
