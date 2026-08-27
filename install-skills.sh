#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Installs agent skills via npx skills add (https://skills.sh/).
#
# Target agents: claude-code, antigravity
# NOTE: codex and antigravity are universal and already handled.
#
# Python installs default to uv (the script bootstraps it via pip if absent);
# py_install falls back to the target interpreter's pip for non-venv targets
# and PEP 668 (externally-managed) environments.

# Resolve the directory this script lives in (for local copy skills)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# =========================================================================
#
# Skills registry
#
#   Each entry is a pair of lines: <repo> followed by <skill-name>.
#   To add or remove a skill, simply edit this array.
#
# =========================================================================

SKILLS=(
  # --- Core / utility ---
  "anthropics/skills"                                                           "skill-creator"
  "vercel-labs/skills"                                                          "find-skills"

  # --- Planning & brainstorming ---
  "obra/superpowers"                                                            "writing-plans"
  "obra/superpowers"                                                            "brainstorming"

  # --- Code review ---
  "coder/mux"                                                                   "deep-review"

  # --- Notifications ---
  "gitstua/stu-skills"                                                          "ntfy-notify"

  # --- Research ---
  "shubhamsaboo/awesome-llm-apps"                                              "deep-research"
  "shubhamsaboo/awesome-llm-apps"                                              "academic-researcher"
  "ailabs-393/ai-labs-claude-skills"                                            "research-paper-writer"
  "langchain-ai/deepagents"                                                     "web-research"
  "davila7/claude-code-templates"                                               "research-engineer"

  # --- Diagrams ---
  "softaworks/agent-toolkit"                                                    "mermaid-diagrams"

  # --- Visualization ---
  "anthropics/knowledge-work-plugins"                                           "data-visualization"

  # --- Documentation ---
  "intellectronica/agent-skills"                                                "context7"

  # --- Writing ---
  "davila7/claude-code-templates"                                               "humanizer"

  # --- Diagrams ---
  "ooiyeefei/ccc"                                                               "excalidraw"

  # --- CLI ---
  "hkuds/cli-anything"                                                          "cli-anything"

  # --- Code quality ---
  "dietrichgebert/ponytail"                                                     "ponytail"
)


# =========================================================================
#
# MCP servers registry (shared by Claude and Codex)
#
#   Each entry is a triplet: <name> <scope> <command...>
#   The command portion may contain multiple tokens.
#   Scope is used by claude mcp add and ignored by codex mcp add.
#
# =========================================================================

MCP_SERVERS=(
  # --- Codebase memory (persistent project memory MCP server) ---
  "codebase-memory-mcp"   "user"   "npx -y codebase-memory-mcp"
)


# =========================================================================
#
# npm global packages registry
#
#   Each entry is a single npm package name to install globally.
#
# =========================================================================

NPM_GLOBALS=(
  # --- Diagrams (required by mermaid-diagrams skill) ---
  "@mermaid-js/mermaid-cli"

  # --- Codex (required by codex plugin) ---
  "@openai/codex"
)


# =========================================================================
#
# Claude Code plugins registry
#
#   Each entry is a triplet:
#     <marketplace-source>  <plugin-id>  <marketplace-name>
#
#   marketplace-source: GitHub owner/repo or URL for the marketplace
#   plugin-id:          Plugin identifier to install (plugin@marketplace)
#   marketplace-name:   Name the marketplace is registered under
#
#   The marketplace is added first, then the plugin is installed from it.
#
# =========================================================================

PLUGINS=(
  # --- Codex ---
  "openai/codex-plugin-cc"    "codex@openai-codex"    "openai-codex"

  # --- Diagrams ---
  "ooiyeefei/ccc"             "ccc-skills@ccc"        "ccc"
)


# =========================================================================
#
# Codex plugins registry
#
#   Each entry is a quartet:
#     <source-repo>  <plugin-name>  <marketplace-name>  <plugin-path>
#
#   source-repo:      GitHub owner/repo or full git URL
#   plugin-name:      Codex plugin identifier
#   marketplace-name: Marketplace namespace used in Codex config
#   plugin-path:      Path to the plugin directory inside the repo
#
#   The installer clones the repo, copies the plugin into:
#     ~/.codex/plugins/cache/<marketplace>/<plugin>/<commit-sha>/
#   and enables it in ~/.codex/config.toml as:
#     [plugins."<plugin>@<marketplace>"]
#     enabled = true
#
# =========================================================================

CODEX_PLUGINS=(
  # --- Official Codex plugins ---
  "openai/plugins"            "github"                "openai-curated"   "plugins/github"
)


# =========================================================================
#
# Agents-only copy skills registry (always installed)
#
#   Each entry is a pair: <source-path> followed by <skill-name>.
#   These are local skill directories that are copied into
#   ~/.agents/skills/<skill-name>/ only. No symlinks are created.
#
#   Always installed (no --local flag required).
#
# =========================================================================

AGENTS_COPY_SKILLS=(
  # --- Planning ---
  "${SCRIPT_DIR}/skills/judgement-engineering-cdx"                             "judgement-engineering-cdx"
  "${SCRIPT_DIR}/skills/looped-engineering-cdx"                                "looped-engineering-cdx"
  "${SCRIPT_DIR}/skills/plan-review-cdx"                                        "plan-review-cdx"

  # --- Code review (gr-* code-intelligence suite) ---
  "${SCRIPT_DIR}/skills/gr-review-cdx"                                          "gr-review-cdx"
  "${SCRIPT_DIR}/skills/gr-ask-cdx"                                             "gr-ask-cdx"
  "${SCRIPT_DIR}/skills/gr-learnings-cdx"                                       "gr-learnings-cdx"
  "${SCRIPT_DIR}/skills/gr-verify-cdx"                                          "gr-verify-cdx"

  # --- Literature / research ---
  "${SCRIPT_DIR}/skills/lit-review-cdx"                                         "lit-review-cdx"
  "${SCRIPT_DIR}/skills/lit-summarizer-cdx"                                     "lit-summarizer-cdx"
  "${SCRIPT_DIR}/skills/lit-survey-cdx"                                         "lit-survey-cdx"
  "${SCRIPT_DIR}/skills/research-council-cdx"                                   "research-council-cdx"
)


# =========================================================================
#
# Claude-only copy skills registry (always installed)
#
#   Each entry is a pair: <source-path> followed by <skill-name>.
#   These are local skill directories that are copied directly into
#   ~/.claude/skills/<skill-name>/ (NOT ~/.agents/skills/).
#   No symlinks are created — these are exclusive to Claude Code.
#
#   Always installed (no --local flag required).
#
# =========================================================================

CLAUDE_COPY_SKILLS=(
  # --- Planning ---
  "${SCRIPT_DIR}/skills/judgement-engineering-clc"                             "judgement-engineering-clc"
  "${SCRIPT_DIR}/skills/looped-engineering-clc"                                "looped-engineering-clc"
  "${SCRIPT_DIR}/skills/plan-review-clc"                                        "plan-review-clc"

  # --- Code review (gr-* code-intelligence suite) ---
  "${SCRIPT_DIR}/skills/gr-review-clc"                                          "gr-review-clc"
  "${SCRIPT_DIR}/skills/gr-ask-clc"                                             "gr-ask-clc"
  "${SCRIPT_DIR}/skills/gr-learnings-clc"                                       "gr-learnings-clc"
  "${SCRIPT_DIR}/skills/gr-verify-clc"                                          "gr-verify-clc"

  # --- Literature / research ---
  "${SCRIPT_DIR}/skills/lit-review-clc"                                         "lit-review-clc"
  "${SCRIPT_DIR}/skills/lit-summarizer-clc"                                     "lit-summarizer-clc"
  "${SCRIPT_DIR}/skills/lit-survey-clc"                                         "lit-survey-clc"
  "${SCRIPT_DIR}/skills/research-council-clc"                                   "research-council-clc"
  "${SCRIPT_DIR}/skills/manuscript-review-clc"                                  "manuscript-review-clc"
)


# =========================================================================
#
# Anti-Gravity copy skills registry (installed when Anti-Gravity is present)
#
#   Each entry is a pair: <source-path> followed by <target-skill-name-agy>.
#   These local skill directories are copied to ~/.agents/skills/<name-agy>/
#   and adapted (YAML frontmatter name and Codex/Claude text references are
#   updated to Anti-Gravity).
#
# =========================================================================

ANTIGRAVITY_COPY_SKILLS=(
  # --- Planning ---
  "${SCRIPT_DIR}/skills/judgement-engineering-cdx"                             "judgement-engineering-agy"
  "${SCRIPT_DIR}/skills/looped-engineering-cdx"                                "looped-engineering-agy"
  "${SCRIPT_DIR}/skills/plan-review-cdx"                                        "plan-review-agy"

  # --- Code review (gr-* code-intelligence suite) ---
  "${SCRIPT_DIR}/skills/gr-review-clc"                                          "gr-review-agy"
  "${SCRIPT_DIR}/skills/gr-ask-clc"                                             "gr-ask-agy"
  "${SCRIPT_DIR}/skills/gr-learnings-clc"                                       "gr-learnings-agy"
  "${SCRIPT_DIR}/skills/gr-verify-clc"                                          "gr-verify-agy"

  # --- Literature / research ---
  "${SCRIPT_DIR}/skills/lit-review-cdx"                                         "lit-review-agy"
  "${SCRIPT_DIR}/skills/lit-summarizer-cdx"                                     "lit-summarizer-agy"
  "${SCRIPT_DIR}/skills/lit-survey-cdx"                                         "lit-survey-agy"
  "${SCRIPT_DIR}/skills/research-council-cdx"                                   "research-council-agy"
)


# =========================================================================
#
# Shared copy skills registry (always installed)
#
#   Each entry is a pair: <source-path> followed by <skill-name>.
#   These are local skill directories that are copied into
#   ~/.agents/skills/<skill-name>/ AND symlinked into:
#     - ~/.claude/skills/<skill-name>
#
#   Anti-Gravity agents discover skills from
#   ~/.agents/skills/ directly.
#
#   Always installed (no --local flag required).
#
# =========================================================================

COPY_SKILLS=(
  # --- Visualization ---
  "${SCRIPT_DIR}/skills/data-viz"                                               "data-viz"

  # --- Research engineering ---
  "${SCRIPT_DIR}/skills/research-engineer-ai-ml"                                "research-engineer-ai-ml"

  # --- Writing / AI detection ---
  "${SCRIPT_DIR}/skills/pangram"                                                "pangram"

  # --- Writing review ---
  "${SCRIPT_DIR}/skills/ai-anti-pattern-review"                                 "ai-anti-pattern-review"

  # --- Obsidian / RAG ---
  "${SCRIPT_DIR}/skills/obsidian-graphrag-index"                                "obsidian-graphrag-index"
  "${SCRIPT_DIR}/skills/obsidian-llamaindex-vector-indexing"                    "obsidian-llamaindex-vector-indexing"

  # --- Notifications ---
  "${SCRIPT_DIR}/skills/alert-me"                                               "alert-me"
)

# gsd has been removed from this installer (its only consumer, orchestrate,
# is also removed). Fail-closed teardown runs unconditionally so any stale
# gsd install — including the unsafe upstream version with the .env* glob +
# "Secrets location" secret-leak template — is removed everywhere it could
# still be active. The submodules/get-shit-done-skills checkout is left on
# disk (unused; optionally `git submodule deinit` later).
# NOTE: echo_yellow is defined later in the script, so this block uses
# plain echo with inline ANSI yellow to stay independent of helper order.
printf '\033[33m%s\033[0m\n' "Note: gsd is no longer installed by this script — removing any stale gsd installs."
for stale in "${HOME}/.agents/skills/gsd" \
             "${HOME}/.claude/skills/gsd"; do
  if [[ -e "${stale}" || -L "${stale}" ]]; then
    printf '\033[33m%s\033[0m\n' "  Removing stale gsd install: ${stale}"
    rm -rf "${stale}"
  fi
done

# AdebayoBraimah/claude-deep-research-skill vendored as a submodule so the
# installed copy is pinned to a known commit rather than tracking the
# remote main branch via `npx skills add`. If the submodule is
# uninitialized, skip and leave any prior install untouched (no fail-closed
# cleanup — this fork has no known security issue).
DRA_SUBMODULE="${SCRIPT_DIR}/submodules/claude-deep-research-skill"
DRA_PROBE="${DRA_SUBMODULE}/SKILL.md"
if [[ -f "${DRA_PROBE}" ]]; then
  COPY_SKILLS+=("${DRA_SUBMODULE}" "deep-research-academic")
else
  printf '\033[33m%s\033[0m\n' "Note: submodules/claude-deep-research-skill is not initialized — skipping deep-research-academic."
  printf '\033[33m%s\033[0m\n' "  To enable, run: git submodule update --init --recursive"
fi


# =========================================================================
#
# Local-only skills registry (installed with --local)
#
#   Same pair format as SKILLS: <repo> followed by <skill-name>.
#   These are only installed when the --local flag is passed.
#
# =========================================================================

LOCAL_SKILLS=(
  # --- Research ---
  "https://github.com/teng-lin/notebooklm-py.git"                                "notebooklm"

  # --- Diagrams ---
  "https://github.com/bahayonghang/drawio-skills.git"                             "drawio"
)


# =========================================================================
#
# Engineering-skills registry (installed with --eng / --engineering)
#
#   Opinionated workflow skills (Matt Pocock's engineering/ +
#   productivity/ upstream folders from mattpocock/skills).
#   Gated behind --eng / --engineering because these are
#   workflow-shaping (TDD, grilling, PRDs, compressed comms)
#   rather than baseline utilities. The bundle is intentionally
#   cross-folder. The --eng flag is independent of --local,
#   --math, and --repo-tools.
#   Each entry is a pair of lines: <repo> followed by <skill-name>.
#
# =========================================================================

ENGINEERING_SKILLS=(
  # setup-matt-pocock-skills MUST run once per project before first use
  # of the other 12 — it provisions the AGENTS.md/CLAUDE.md agent-skills
  # block and docs/agents/ layout the rest depend on.
  "mattpocock/skills"                                                           "setup-matt-pocock-skills"
  "mattpocock/skills"                                                           "tdd"
  "mattpocock/skills"                                                           "diagnose"
  "mattpocock/skills"                                                           "grill-me"
  "mattpocock/skills"                                                           "grill-with-docs"
  "mattpocock/skills"                                                           "improve-codebase-architecture"
  "mattpocock/skills"                                                           "triage"
  "mattpocock/skills"                                                           "zoom-out"
  "mattpocock/skills"                                                           "to-prd"
  "mattpocock/skills"                                                           "to-issues"

  # --- Productivity (upstream skills/productivity/) ---
  "mattpocock/skills"                                                           "handoff"
  "mattpocock/skills"                                                           "write-a-skill"
)


# =========================================================================
#
# Local-only pip packages (installed with --local)
#
#   Each entry is a single pip package name to install.
#   These are only installed when the --local flag is passed.
#
# =========================================================================

LOCAL_PIP_PACKAGES=(
  # --- NotebookLM dependencies ---
  "notebooklm-py[browser]"
  "playwright"
)


# =========================================================================
#
# Local copy skills registry (installed with --local)
#
#   Each entry is a pair: <source-path> followed by <skill-name>.
#   These are local skill directories that are copied into
#   ~/.agents/skills/<skill-name>/ AND symlinked into:
#     - ~/.claude/skills/<skill-name>
#
#   Anti-Gravity agents discover skills from
#   ~/.agents/skills/ directly.
#
#   Only installed when the --local flag is passed.
#
# =========================================================================

LOCAL_COPY_SKILLS=(
  # --- Image & vector graphics ---
  "${SCRIPT_DIR}/skills/gimp"                                                   "gimp"
  "${SCRIPT_DIR}/skills/inkscape"                                               "inkscape"
)


# =========================================================================
#
# Local Claude-only copy skills registry (installed with --local)
#
#   Each entry is a pair: <source-path> followed by <skill-name>.
#   These are local skill directories that are copied directly into
#   ~/.claude/skills/<skill-name>/ (NOT ~/.agents/skills/).
#   No symlinks are created — these are exclusive to Claude Code.
#
#   Only installed when the --local flag is passed.
#
# =========================================================================

LOCAL_CLAUDE_COPY_SKILLS=(
)


# =========================================================================
#
# Claude Code hooks registry (always installed)
#
#   CLAUDE CODE SPECIFIC. Hooks are a Claude Code feature; Codex,
#   Anti-Gravity, and Gemini have no equivalent and are unaffected.
#
#   Each entry is a pair: <source-hooks-dir> followed by <hook-name>.
#
#   The source directory must contain:
#     - one or more executable scripts, copied verbatim to
#       ~/.claude/hooks/<hook-name>/
#     - claude-hooks.json — a fragment of the "hooks" object from
#       settings.json, declaring the events this hook binds to. The token
#       __HOOK_DIR__ is replaced with the real install directory.
#
#   The merge into ~/.claude/settings.json is idempotent: an entry whose
#   command already exists is never added twice. Pre-existing hooks from
#   other sources are preserved, and a timestamped backup is written
#   before any modification.
#
#   Requires jq and the claude CLI; skipped with a warning otherwise.
#
# =========================================================================

CLAUDE_HOOKS=(
  # --- Notifications ---
  "${SCRIPT_DIR}/skills/alert-me/hooks"                                         "alert-me"
)


# =========================================================================
#
# Math copy skills registry (installed with --math)
#
#   Each entry is a pair: <source-path> followed by <skill-name>.
#   These are local skill directories that are copied into
#   ~/.agents/skills/<skill-name>/ AND symlinked into:
#     - ~/.claude/skills/<skill-name>
#
#   Anti-Gravity agents discover skills from
#   ~/.agents/skills/ directly.
#
#   Only installed when the --math flag is passed. The --math flag is
#   independent of --local; either or both may be passed.
#
#   Math skills require Lean 4 and Lake (and Mathlib for the AI/ML
#   variant) on PATH for verification. The script does not auto-install
#   them — install elan from https://leanprover.github.io/ first.
#
# =========================================================================

MATH_COPY_SKILLS=(
  # --- Mathematics (requires Lean 4 + Lake; Mathlib for mathematician-ai-ml) ---
  "${SCRIPT_DIR}/skills/mathematician"                                          "mathematician"
  "${SCRIPT_DIR}/skills/mathematician-ai-ml"                                    "mathematician-ai-ml"
)


# =========================================================================
#
# Repo-tools registries (installed with --repo-tools)
#
#   --repo-tools installs code-intelligence tools that ship as installable
#   packages (not skills) and wires their MCP servers into Claude Code,
#   Codex, Gemini CLI, and Antigravity IDE.
#
#   REPO_TOOL_PIP_PACKAGES: single pip package name per entry.
#   REPO_TOOL_NPM_GLOBALS:  single npm package name per entry.
#   REPO_TOOL_MCP_SERVERS:  triplet of <name> <scope> <command...>.
#     The same triplets are used for Claude, Codex, Gemini, and Antigravity.
#     Codex ignores scope; Antigravity is merged via jq into
#     ~/.gemini/antigravity/mcp_config.json.
#     Command strings are whitespace-tokenized; do not add quoted args.
#
# =========================================================================

REPO_TOOL_PIP_PACKAGES=(
  # --- Graphify (code knowledge graphs + global skill files) ---
  "graphifyy[mcp]"
)

REPO_TOOL_NPM_GLOBALS=(
  # --- GitNexus (16-tool code-intelligence MCP server) ---
  "gitnexus"
)

REPO_TOOL_MCP_SERVERS=(
  # name | scope (Claude+Gemini honor it; Codex ignores) | command
  "gitnexus" "user" "npx -y gitnexus@latest mcp"
)


# =========================================================================
#
# Helper functions
#
# =========================================================================


#######################################
# Prints usage information and example
#   invocations to the command line
#   interface, then exits.
# Arguments:
#   None
#######################################
Usage(){
  cat << USAGE

  Usage:

      $(basename ${0}) [options]

  Description:

      Installs agent skills from the skills.sh registry
      (https://skills.sh/) using npx. Skills are installed
      globally (--global) for the agents: claude-code and
      antigravity.

      Also installs required MCP servers, Claude Code
      plugins, Codex plugins, and npm global dependencies
      when the required CLIs are available.

      The script runs nine always-on installation phases:

        1. Agent skills          (via npx skills add)
        2. Claude MCP servers    (via claude mcp add)
        3. Codex MCP servers     (via codex mcp add)
        4. npm packages          (via npm install -g)
        5. Agents-only copy skills (copy to ~/.agents/skills)
        6. Claude-only copy skills (copy to ~/.claude/skills)
        7. Shared copy skills    (copy + symlinks)
        8. Claude plugins        (via claude plugin install)
        9. Codex plugins         (via repo clone + Codex config)

      When --local is passed, four additional phases run:

        *  Local agent skills   (via npx skills add)
        *  Local pip packages   (via pip install)
        *  Local copy skills    (copy + symlinks)
        *  Local Claude-only copy skills (copy)

      When --math is passed, one additional phase runs:

        *  Math copy skills     (copy + symlinks)

      The --math flag is independent of --local; either or
      both may be passed.

      When --eng (or --engineering) is passed, one additional
      phase runs:

        - Engineering + productivity skills — via npx skills
          add (Matt Pocock's TDD, diagnose, grill-me,
          grill-with-docs, improve-codebase-architecture,
          triage, zoom-out, to-prd, to-issues, handoff,
          write-a-skill, and the
          setup-matt-pocock-skills bootstrap).

      --eng is independent of --local, --math, and
      --repo-tools.

      When --repo-tools is passed, the following additional
      phases run:

        *  Repo-tool pip packages (graphifyy[mcp]) and global
           Graphify skill registration for Claude Code, Codex,
           Gemini CLI, and Antigravity IDE. Codex Graphify also
           gets [features].multi_agent = true added to
           ~/.codex/config.toml idempotently.
        *  Repo-tool npm globals (gitnexus) requires Node >=22.
        *  Repo-tool MCP server registration (gitnexus) for
           Claude Code, Codex, Gemini CLI, and Antigravity IDE.

      --repo-tools is independent of --local and --math.

      Phase 1 requires npx. Phases 2 and 8 require the
      claude CLI. Phases 3 and 9 require the codex CLI.
      Local pip packages require uv or pip. Missing CLIs
      cause the corresponding phases to be skipped.

      Python installs default to uv. If uv is not found it
      is bootstrapped via pip (--user, with a PEP 668
      --break-system-packages retry); when uv is unavailable
      the script falls back to the target interpreter's pip.
      SkillSpector (a skill security scanner) is installed
      via uv first, then scans the installed skills after all
      install phases (detection-after-fetch, non-fatal).

      --repo-tools requires Python >=3.10 (which python is
      consulted first so an activated conda env wins) and
      Node >=22. Optional: gemini CLI (Gemini MCP), jq plus
      ~/.gemini/antigravity/ directory (Antigravity MCP).
      Missing optional CLIs/tools are skipped with warnings.

      Math skills require Lean 4 and Lake on PATH (and
      Mathlib for the AI/ML variant) for Lean verification.
      The script does not auto-install them — install elan
      from https://leanprover.github.io/ first.

      NOTE:
      - codex and antigravity are universal for the base skill
        installation. With --repo-tools, the script also
        performs explicit MCP registration and global
        Graphify skill setup for Codex and Antigravity.
      - If installing skills for the first time, use
        the interactive install process with:

        npx skills add https://github.com/vercel-labs/skills --skill find-skills

  Post-install setup:

      After installation, run /codex:setup inside Claude
      Code to verify Codex CLI readiness and authentication.

        /codex:setup
        /codex:setup --enable-review-gate

      The optional --enable-review-gate flag enables a
      stop-time review gate that requires Codex to review
      your changes before Claude Code completes a task.

      When --local is used, authenticate with NotebookLM
      (first time only, opens browser):

        notebooklm login

  Optional arguments:
      -h, -help, --help               Prints this help menu, then exits.
      --local                         Also install local-only skills and
                                      their pip dependencies.
      --math                          Also install math copy skills
                                      (mathematician, mathematician-ai-ml).
                                      Requires Lean 4 + Lake on PATH for
                                      verification (not auto-installed).
                                      Independent of --local.
      --repo-tools                    Also install repo-analysis tools
                                      (Graphify + GitNexus) and register
                                      their MCP/skill integrations for
                                      Claude Code, Codex, Gemini CLI, and
                                      Antigravity IDE. Requires Python
                                      >=3.10 and Node >=22. Independent
                                      of --local and --math.
      --eng, --engineering            Also install Matt Pocock's
                                      engineering + productivity skills
                                      (TDD, grill-me, to-issues,
                                      write-a-skill, etc.).
                                      Independent of --local, --math,
                                      and --repo-tools.

  Example usage:

      # Install all skills
      $(basename ${0})

      # Install all skills including local-only skills
      $(basename ${0}) --local

      # Install all skills including math skills
      $(basename ${0}) --math

      # Install everything (local + math)
      $(basename ${0}) --local --math

      # Install repo tools (Graphify + GitNexus)
      $(basename ${0}) --repo-tools

      # Combined: local skills + repo tools
      $(basename ${0}) --local --repo-tools

      # Install all skills including engineering skills
      $(basename ${0}) --eng

      # Print this help menu
      $(basename ${0}) --help

USAGE
  exit 1
}


#######################################
# Prints message to the command line
#   interface in some arbitrary color.
# Arguments:
#   msg
#######################################
echo_color(){
  msg='\033[0;'"${@}"'\033[0m'
  echo -e ${msg}
}


#######################################
# Prints message to the command line
#   interface in red.
# Arguments:
#   msg
#######################################
echo_red(){
  echo_color '31m'"${@}"
}


#######################################
# Prints message to the command line
#   interface in green.
# Arguments:
#   msg
#######################################
echo_green(){
  echo_color '32m'"${@}"
}


#######################################
# Prints message to the command line
#   interface in yellow.
# Arguments:
#   msg
#######################################
echo_yellow(){
  echo_color '33m'"${@}"
}


#######################################
# Prints message to the command line
#   interface in blue.
# Arguments:
#   msg
#######################################
echo_blue(){
  echo_color '36m'"${@}"
}


#######################################
# Prints an error message to the command
#   line interface in red, then exits
#   with a non-zero status.
# Arguments:
#   msg
#######################################
exit_error(){
  echo_red "${@}"
  exit 1
}


#######################################
# Installs a single skill from the
#   skills.sh registry using npx.
# Arguments:
#   repo:  GitHub owner/repo or full URL
#   skill: Skill name to install
# Globals:
#   FAILED_SKILLS (appended on failure)
#######################################
install_skill(){
  local repo="${1}"
  local skill="${2}"

  echo_blue "Installing: ${skill}  (from ${repo})"

  if npx skills add "${repo}" --skill "${skill}" --global --yes; then
    echo_green "  -> ${skill} installed successfully"
  else
    echo_red "  -> Failed to install ${skill}"
    FAILED_SKILLS+=("${skill}")
  fi

  echo
}


#######################################
# Installs a single MCP server using
#   claude mcp add.
# Arguments:
#   name:  MCP server name
#   scope: Scope flag (user, project)
#   cmd:   Command to run the server
# Globals:
#   FAILED_MCPS (appended on failure)
#######################################
install_mcp(){
  local name="${1}"
  local scope="${2}"
  local cmd="${3}"

  echo_blue "Installing MCP: ${name}  (scope: ${scope})"

  if claude mcp add "${name}" -s "${scope}" -- ${cmd}; then
    echo_green "  -> MCP ${name} installed successfully"
  else
    echo_red "  -> Failed to install MCP ${name}"
    FAILED_MCPS+=("${name}")
  fi

  echo
}


#######################################
# Installs a single MCP server for
#   Codex using codex mcp add.
#   Scope is ignored (codex has no scope).
# Arguments:
#   name:  MCP server name
#   scope: (ignored — kept for array compat)
#   cmd:   Command to run the server
# Globals:
#   FAILED_CODEX_MCPS (appended on failure)
#######################################
install_codex_mcp(){
  local name="${1}"
  local scope="${2}"  # ignored — codex mcp add has no scope
  local cmd="${3}"

  echo_blue "Installing Codex MCP: ${name}"

  if codex mcp add "${name}" -- ${cmd}; then
    echo_green "  -> Codex MCP ${name} installed successfully"
  else
    echo_red "  -> Failed to install Codex MCP ${name}"
    FAILED_CODEX_MCPS+=("${name}")
  fi

  echo
}


#######################################
# Installs a single Claude Code plugin.
#   Adds the marketplace (if not already
#   present) then installs the plugin.
# Arguments:
#   source:    Marketplace source (owner/repo or URL)
#   plugin_id: Plugin identifier (plugin@marketplace)
#   mkt_name:  Marketplace name
# Globals:
#   FAILED_PLUGINS (appended on failure)
#######################################
install_plugin(){
  local source="${1}"
  local plugin_id="${2}"
  local mkt_name="${3}"

  echo_blue "Adding marketplace: ${mkt_name}  (from ${source})"

  if ! claude plugin marketplace add "${source}" 2>/dev/null; then
    # Marketplace may already exist — continue to install
    echo_yellow "  -> Marketplace ${mkt_name} may already be added, continuing..."
  fi

  echo_blue "Installing plugin: ${plugin_id}"

  if claude plugin install "${plugin_id}"; then
    echo_green "  -> Plugin ${plugin_id} installed successfully"
  else
    echo_red "  -> Failed to install plugin ${plugin_id}"
    FAILED_PLUGINS+=("${plugin_id}")
  fi

  echo
}


#######################################
# Converts a GitHub owner/repo reference
#   into a cloneable git URL.
# Arguments:
#   repo: GitHub owner/repo or full URL
#######################################
repo_to_git_url(){
  local repo="${1}"

  if [[ "${repo}" == *"://"* ]]; then
    echo "${repo}"
  else
    echo "https://github.com/${repo}.git"
  fi
}


#######################################
# Detects a Python interpreter on PATH
#   with version >=3.10. Prefers `python`
#   first so an activated conda env wins.
# Outputs:
#   Absolute path to interpreter on stdout
# Returns:
#   0 on success, 1 if no >=3.10 found
#######################################
detect_python_310(){
  local candidates=(python python3 python3.13 python3.12 python3.11 python3.10)
  local cand
  for cand in "${candidates[@]}"; do
    if command -v "${cand}" &>/dev/null; then
      if "${cand}" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
        command -v "${cand}"
        return 0
      fi
    fi
  done
  return 1
}


#######################################
# Installs a Python library (importable
#   package) into an explicit interpreter,
#   preferring uv and falling back to that
#   interpreter's pip. Reserved for
#   libraries — standalone CLIs use
#   `uv tool install` instead.
#
#   Always targets an explicit interpreter
#   (no --system, which bypasses venvs and
#   trips PEP 668). uv refuses non-venv
#   --python targets, so ANY uv non-zero
#   exit falls back to pip. PEP 668 pip
#   failures retry with
#   --break-system-packages.
# Arguments:
#   pkg:           pip package spec
#   target_python: interpreter to install into (required)
#   extra_flags:   optional extra flags (e.g. --upgrade)
# Globals:
#   uv_ready (read)
# Returns:
#   Exit status of the LAST attempted
#   installer — non-zero only when BOTH uv
#   and the pip fallback fail. No trailing
#   log masks this status; callers gate on it.
#######################################
py_install(){
  local pkg="${1}"
  local target_python="${2}"
  shift 2
  local -a extra_flags=("${@}")

  if [[ -z "${target_python}" ]]; then
    echo_red "  -> py_install: no target interpreter given for ${pkg}"
    return 2
  fi

  if [[ "${uv_ready}" == true ]]; then
    echo_blue "  -> uv pip install --python ${target_python} ${extra_flags[*]} ${pkg}"
    if uv pip install --python "${target_python}" "${extra_flags[@]}" "${pkg}"; then
      return 0
    fi
    echo_yellow "  -> uv install failed (uv refuses non-venv/non-conda targets); falling back to ${target_python} -m pip"
  fi

  # pip fallback: uv unavailable OR uv returned non-zero.
  if "${target_python}" -m pip install "${extra_flags[@]}" "${pkg}"; then
    return 0
  fi
  # PEP 668 externally-managed-environment retry.
  echo_yellow "  -> pip install failed; retrying with --break-system-packages"
  "${target_python}" -m pip install --break-system-packages "${extra_flags[@]}" "${pkg}"
  return "${?}"
}


#######################################
# Installs SkillSpector (NVIDIA) as a uv
#   tool so it can scan installed skills
#   for security issues. Best-effort and
#   non-fatal: warns if uv or the network
#   is unavailable.
# Globals:
#   uv_ready (read)
#   skillspector_ready (set)
#######################################
install_skillspector(){
  skillspector_ready=false

  echo
  echo_blue "=========================================="
  echo_blue " Installing SkillSpector (skill security scanner)"
  echo_blue "=========================================="
  echo

  if [[ "${uv_ready}" != true ]] && ! command -v uv &>/dev/null; then
    echo_yellow "uv not available — skipping SkillSpector install (skill security scan will be skipped)."
    echo
    return 0
  fi

  if uv tool install git+https://github.com/NVIDIA/skillspector.git; then
    if command -v skillspector &>/dev/null; then
      skillspector_ready=true
      echo_green "  -> SkillSpector installed successfully"
    else
      echo_yellow "  -> SkillSpector installed but 'skillspector' is not on PATH (is ~/.local/bin on PATH?) — scan will be skipped"
    fi
  else
    echo_yellow "  -> Failed to install SkillSpector (network or uv tool issue) — scan will be skipped"
  fi
  echo
}


#######################################
# Scans installed skill directories with
#   SkillSpector AFTER skills are fetched,
#   so remote (npx) skills — the highest
#   risk — are actually inspected. This is
#   detection-after-fetch, NOT pre-activation
#   gating. Non-fatal; findings are surfaced
#   loudly for the summary.
# Globals:
#   skillspector_ready (read)
#######################################
run_skillspector_scan(){
  [[ "${skillspector_ready}" == true ]] || return 0

  echo
  echo_blue "=========================================="
  echo_blue " SkillSpector scan (skill security review)"
  echo_blue "=========================================="
  echo_yellow " Detection-after-fetch: inspects already-installed skills"
  echo_yellow " (including remote npx-fetched skills). NOT pre-activation gating."
  echo

  local -a scan_dirs=()
  # Canonical agents skills dir — covers shared + agents-only copy skills AND
  # the npx-global skills that `npx skills add --global` writes here.
  [[ -d "${HOME}/.agents/skills" ]] && scan_dirs+=("${HOME}/.agents/skills")
  # Claude-only real skill dirs. Skip symlinks (the shared COPY_SKILLS create
  # ~/.claude/skills/* -> ~/.agents/skills/* links) to avoid double-scanning.
  if [[ -d "${HOME}/.claude/skills" ]]; then
    local entry
    for entry in "${HOME}/.claude/skills"/*; do
      [[ -e "${entry}" ]] || continue
      [[ -L "${entry}" ]] && continue
      scan_dirs+=("${entry}")
    done
  fi

  if [[ ${#scan_dirs[@]} -eq 0 ]]; then
    echo_yellow " No skill directories found to scan."
    echo
    return 0
  fi

  local d
  for d in "${scan_dirs[@]}"; do
    echo_blue " Scanning: ${d}"
    # --no-llm keeps the scan offline (no API key needed); non-fatal on findings.
    skillspector scan "${d}" --no-llm \
      || echo_yellow "  -> SkillSpector reported findings or errored for ${d} (non-fatal)"
  done
  echo
}


#######################################
# Enables a Codex plugin in
#   ~/.codex/config.toml.
# Arguments:
#   plugin_key: plugin@marketplace key
#######################################
enable_codex_plugin(){
  local plugin_key="${1}"
  local config_dir="${HOME}/.codex"
  local config_file="${config_dir}/config.toml"
  local tmp_file

  mkdir -p "${config_dir}"

  if [[ ! -f "${config_file}" ]]; then
    printf '[plugins."%s"]\nenabled = true\n' "${plugin_key}" > "${config_file}"
    return 0
  fi

  tmp_file="$(mktemp)"

  awk -v section="[plugins.\"${plugin_key}\"]" '
    $0 == section {
      print
      in_section = 1
      saw_section = 1
      next
    }

    in_section && /^\[/ {
      if (!updated_enabled) {
        print "enabled = true"
        updated_enabled = 1
      }
      in_section = 0
    }

    in_section && /^enabled[[:space:]]*=/ {
      if (!updated_enabled) {
        print "enabled = true"
        updated_enabled = 1
      }
      next
    }

    { print }

    END {
      if (in_section && !updated_enabled) {
        print "enabled = true"
      }

      if (!saw_section) {
        if (NR > 0) {
          print ""
        }
        print section
        print "enabled = true"
      }
    }
  ' "${config_file}" > "${tmp_file}" && mv "${tmp_file}" "${config_file}"
}


#######################################
# Installs a single Codex plugin by
#   cloning its source repo, copying the
#   plugin into Codex's local cache, and
#   enabling it in ~/.codex/config.toml.
# Arguments:
#   source_repo:      GitHub owner/repo or full URL
#   plugin_name:      Codex plugin identifier
#   marketplace_name: Codex marketplace namespace
#   plugin_path:      Path to plugin directory inside repo
# Globals:
#   FAILED_CODEX_PLUGINS (appended on failure)
#######################################
install_codex_plugin(){
  local source_repo="${1}"
  local plugin_name="${2}"
  local marketplace_name="${3}"
  local plugin_path="${4}"
  local clone_url
  local tmp_dir
  local commit_sha
  local source_dir
  local target_dir
  local plugin_key="${plugin_name}@${marketplace_name}"

  echo_blue "Installing Codex plugin: ${plugin_key}  (from ${source_repo})"

  clone_url="$(repo_to_git_url "${source_repo}")"
  tmp_dir="$(mktemp -d)"

  if ! git clone --depth 1 "${clone_url}" "${tmp_dir}" >/dev/null 2>&1; then
    echo_red "  -> Failed to clone ${source_repo}"
    FAILED_CODEX_PLUGINS+=("${plugin_key}")
    rm -rf "${tmp_dir}"
    echo
    return
  fi

  source_dir="${tmp_dir}/${plugin_path}"

  if [[ ! -f "${source_dir}/.codex-plugin/plugin.json" ]]; then
    echo_red "  -> Missing Codex plugin manifest at ${plugin_path}/.codex-plugin/plugin.json"
    FAILED_CODEX_PLUGINS+=("${plugin_key}")
    rm -rf "${tmp_dir}"
    echo
    return
  fi

  commit_sha="$(git -C "${tmp_dir}" rev-parse HEAD)"
  target_dir="${HOME}/.codex/plugins/cache/${marketplace_name}/${plugin_name}/${commit_sha}"

  mkdir -p "${target_dir}"

  if ! cp -R "${source_dir}/." "${target_dir}/"; then
    echo_red "  -> Failed to copy plugin files into Codex cache"
    FAILED_CODEX_PLUGINS+=("${plugin_key}")
    rm -rf "${tmp_dir}"
    echo
    return
  fi

  if enable_codex_plugin "${plugin_key}"; then
    echo_green "  -> Codex plugin ${plugin_key} installed successfully"
  else
    echo_red "  -> Failed to enable Codex plugin ${plugin_key}"
    FAILED_CODEX_PLUGINS+=("${plugin_key}")
  fi

  rm -rf "${tmp_dir}"
  echo
}


#######################################
# Installs a single npm package globally
#   using npm install -g.
# Arguments:
#   pkg: npm package name
# Globals:
#   FAILED_NPMS (appended on failure)
#######################################
install_npm_global(){
  local pkg="${1}"

  echo_blue "Installing npm package: ${pkg}"

  if npm install -g "${pkg}"; then
    echo_green "  -> ${pkg} installed successfully"
  else
    echo_red "  -> Failed to install ${pkg}"
    FAILED_NPMS+=("${pkg}")
  fi

  echo
}


#######################################
# Idempotently sets [features].multi_agent
#   = true in ~/.codex/config.toml. Used
#   by Graphify Codex parallel extraction.
# Arguments:
#   None
#######################################
enable_codex_multi_agent(){
  local config_dir="${HOME}/.codex"
  local config_file="${config_dir}/config.toml"
  local tmp_file

  mkdir -p "${config_dir}"
  if [[ ! -f "${config_file}" ]]; then
    printf '[features]\nmulti_agent = true\n' > "${config_file}"
    return 0
  fi

  tmp_file="$(mktemp)"
  awk '
    $0 == "[features]" {
      print
      in_features = 1
      saw_features = 1
      next
    }
    in_features && /^\[/ {
      if (!updated_multi_agent) {
        print "multi_agent = true"
        updated_multi_agent = 1
      }
      in_features = 0
    }
    in_features && /^multi_agent[[:space:]]*=/ {
      if (!updated_multi_agent) {
        print "multi_agent = true"
        updated_multi_agent = 1
      }
      next
    }
    { print }
    END {
      if (in_features && !updated_multi_agent) {
        print "multi_agent = true"
      }
      if (!saw_features) {
        if (NR > 0) print ""
        print "[features]"
        print "multi_agent = true"
      }
    }
  ' "${config_file}" > "${tmp_file}" && mv "${tmp_file}" "${config_file}"
}


#######################################
# Copies Graphify's packaged skill.md into
#   ~/.agents/skills/graphify/SKILL.md for
#   Antigravity discovery. Avoids Graphify's
#   project-mutating Antigravity command.
# Arguments:
#   python: Path to the Python interpreter
# Globals:
#   FAILED_REPO_TOOL_PIPS (appended on failure)
#######################################
install_graphify_antigravity_global(){
  local python="${1}"
  local target_dir="${HOME}/.agents/skills/graphify"
  local target="${target_dir}/SKILL.md"
  local version_file="${target_dir}/.graphify_version"
  local tmp

  mkdir -p "${target_dir}"
  tmp="$(mktemp)"
  if "${python}" - <<'PY' > "${tmp}"
from importlib import resources
import graphify

content = resources.files("graphify").joinpath("skill.md").read_text(encoding="utf-8")
frontmatter = "---\nname: graphify-manager\ndescription: Rebuild the code graph or perform manual CLI queries when MCP server is offline.\n---\n\n"
if not content.startswith("---\n"):
    content = frontmatter + content
print(content, end="")
PY
  then
    mv "${tmp}" "${target}"
    "${python}" - <<'PY' > "${version_file}" 2>/dev/null || true
import graphify
print(getattr(graphify, "__version__", "unknown"))
PY
    echo_green "  -> Graphify Antigravity global skill installed at ${target}"
    return 0
  else
    rm -f "${tmp}"
    echo_red "  -> Failed to install Graphify Antigravity global skill"
    FAILED_REPO_TOOL_PIPS+=("graphifyy (antigravity global skill)")
    return 1
  fi
}


#######################################
# Installs a repo-tool pip package using
#   <python> -m pip. For graphifyy, also
#   runs documented per-platform Graphify
#   skill registration commands.
# Arguments:
#   pkg:    pip package name
#   python: Path to the Python interpreter
# Globals:
#   FAILED_REPO_TOOL_PIPS (appended on failure)
#######################################
install_repo_tool_pip(){
  local pkg="${1}"
  local python="${2}"
  local -a graphify_cmd
  local graphify_failed=false
  local graphify_tmp

  echo_blue "Installing repo-tool pip package: ${pkg}  (using ${python})"
  # py_install's per-call pip fallback guarantees the package lands in
  # ${python} (conda-aware) even when uv refuses a non-venv --python target,
  # so the graphify registration below runs against the right interpreter.
  if py_install "${pkg}" "${python}" --upgrade; then
    echo_green "  -> ${pkg} installed successfully"

    if [[ "${pkg}" == graphifyy* ]]; then
      if command -v graphify &>/dev/null; then
        graphify_cmd=(graphify)
      else
        graphify_cmd=("${python}" -m graphify)
      fi

      echo_blue "  -> Registering Graphify for Claude Code"
      if ! "${graphify_cmd[@]}" install </dev/null; then
        echo_red "  -> Failed to register Graphify for Claude Code"
        FAILED_REPO_TOOL_PIPS+=("${pkg} (graphify claude install)")
        graphify_failed=true
      fi

      echo_blue "  -> Registering Graphify for Codex"
      if ! "${graphify_cmd[@]}" install --platform codex </dev/null; then
        echo_red "  -> Failed to register Graphify for Codex"
        FAILED_REPO_TOOL_PIPS+=("${pkg} (graphify codex install)")
        graphify_failed=true
      fi
      if ! enable_codex_multi_agent; then
        echo_red "  -> Failed to enable Codex multi_agent feature"
        FAILED_REPO_TOOL_PIPS+=("${pkg} (codex multi_agent)")
        graphify_failed=true
      fi

      echo_blue "  -> Registering Graphify for Gemini CLI"
      graphify_tmp="$(mktemp -d)"
      if ! (cd "${graphify_tmp}" && "${graphify_cmd[@]}" install --platform gemini </dev/null); then
        echo_red "  -> Failed to register Graphify for Gemini CLI"
        FAILED_REPO_TOOL_PIPS+=("${pkg} (graphify gemini install)")
        graphify_failed=true
      fi
      rm -rf "${graphify_tmp}"

      echo_blue "  -> Installing Graphify global skill for Antigravity"
      if ! install_graphify_antigravity_global "${python}"; then
        graphify_failed=true
      fi

      if [[ "${graphify_failed}" != true ]]; then
        echo_green "  -> Graphify skill registered for Claude Code, Codex, Gemini CLI, and Antigravity"
      fi
    fi
  else
    echo_red "  -> Failed to install ${pkg}"
    FAILED_REPO_TOOL_PIPS+=("${pkg}")
  fi
  echo
}


#######################################
# Installs a repo-tool npm global package.
#   Failures land in FAILED_REPO_TOOL_NPMS
#   so the repo-tools summary can report
#   them independently of base npm phase.
# Arguments:
#   pkg: npm package name
# Globals:
#   FAILED_REPO_TOOL_NPMS (appended on failure)
#######################################
install_repo_tool_npm(){
  local pkg="${1}"
  echo_blue "Installing repo-tool npm package: ${pkg}"
  if npm install -g "${pkg}"; then
    echo_green "  -> ${pkg} installed successfully"
  else
    echo_red "  -> Failed to install ${pkg}"
    FAILED_REPO_TOOL_NPMS+=("${pkg}")
  fi
  echo
}


#######################################
# Installs a single pip package using
#   pip install.
# Arguments:
#   pkg:    pip package name
#   python: interpreter to install into
# Globals:
#   FAILED_PIPS (appended on failure)
#######################################
install_pip_package(){
  local pkg="${1}"
  local python="${2}"

  echo_blue "Installing pip package: ${pkg}  (using ${python})"

  if py_install "${pkg}" "${python}"; then
    echo_green "  -> ${pkg} installed successfully"

    # playwright requires a post-install step to download Chromium. Run it
    # against the SAME interpreter (not the bare `playwright` console script,
    # which may resolve to a different environment).
    if [[ "${pkg}" == "playwright" ]]; then
      echo_blue "  -> Running playwright install chromium..."
      if "${python}" -m playwright install chromium; then
        echo_green "  -> Playwright Chromium installed successfully"
      else
        echo_red "  -> Failed to install Playwright Chromium"
        FAILED_PIPS+=("${pkg} (chromium)")
      fi
    fi
  else
    echo_red "  -> Failed to install ${pkg}"
    FAILED_PIPS+=("${pkg}")
  fi

  echo
}


#######################################
# Installs a local skill by copying it
#   into ~/.agents/skills/ and creating
#   a symlink in ~/.claude/skills/.
#
#   Note: Gemini CLI and Antigravity IDE
#   discover skills from the canonical
#   ~/.agents/skills/ directory directly;
#   the historical ~/.gemini/antigravity/skills/
#   symlinks are no longer created.
# Arguments:
#   source_path: Absolute path to the
#                local skill directory
#   skill_name:  Skill name (directory name)
#   failed_var:  Optional name of the global
#                array to append failures to
#                (default: FAILED_COPY_SKILLS).
#                Uses bash declare -n nameref;
#                requires bash 4.3+.
# Globals:
#   <failed_var> (appended on failure)
#######################################
install_local_copy_skill(){
  local source_path="${1}"
  local skill_name="${2}"
  local failed_var="${3:-FAILED_COPY_SKILLS}"
  local agents_dir="${HOME}/.agents/skills"
  local target_dir="${agents_dir}/${skill_name}"
  local claude_dir="${HOME}/.claude/skills"
  declare -n failed_ref="${failed_var}"

  echo_blue "Installing local skill: ${skill_name}  (from ${source_path})"

  if [[ ! -d "${source_path}" ]]; then
    echo_red "  -> Source directory not found: ${source_path}"
    failed_ref+=("${skill_name}")
    echo
    return
  fi

  # Copy skill to ~/.agents/skills/
  mkdir -p "${agents_dir}"

  if [[ -d "${target_dir}" ]]; then
    echo_yellow "  -> Target exists, updating: ${target_dir}"
    rm -rf "${target_dir}"
  fi

  if ! cp -R "${source_path}" "${target_dir}"; then
    echo_red "  -> Failed to copy ${skill_name} to ${target_dir}"
    failed_ref+=("${skill_name}")
    echo
    return
  fi

  # Strip any .git gitlink/dir copied from a submodule-rooted source — the
  # installed skill should never carry references back to its submodule.
  rm -rf "${target_dir}/.git"

  echo_green "  -> Copied to ${target_dir}"

  # Create symlink in ~/.claude/skills/
  mkdir -p "${claude_dir}"

  if [[ -e "${claude_dir}/${skill_name}" || -L "${claude_dir}/${skill_name}" ]]; then
    rm -rf "${claude_dir}/${skill_name}"
  fi

  ln -s "../../.agents/skills/${skill_name}" "${claude_dir}/${skill_name}"
  echo_green "  -> Symlinked: ${claude_dir}/${skill_name}"

  echo_green "  -> ${skill_name} installed successfully"
  echo
}


#######################################
# Installs a local skill by copying it
#   into ~/.agents/skills/ only.
#   No symlinks are created.
# Arguments:
#   source_path: Absolute path to the
#                local skill directory
#   skill_name:  Skill name (directory name)
# Globals:
#   FAILED_AGENTS_COPY_SKILLS (appended on failure)
#######################################
install_agents_copy_skill(){
  local source_path="${1}"
  local skill_name="${2}"
  local agents_dir="${HOME}/.agents/skills"
  local target_dir="${agents_dir}/${skill_name}"

  echo_blue "Installing agents skill: ${skill_name}  (from ${source_path})"

  if [[ ! -d "${source_path}" ]]; then
    echo_red "  -> Source directory not found: ${source_path}"
    FAILED_AGENTS_COPY_SKILLS+=("${skill_name}")
    echo
    return
  fi

  # Copy skill to ~/.agents/skills/
  mkdir -p "${agents_dir}"

  if [[ -d "${target_dir}" ]]; then
    echo_yellow "  -> Target exists, updating: ${target_dir}"
    rm -rf "${target_dir}"
  fi

  if ! cp -R "${source_path}" "${target_dir}"; then
    echo_red "  -> Failed to copy ${skill_name} to ${target_dir}"
    FAILED_AGENTS_COPY_SKILLS+=("${skill_name}")
    echo
    return
  fi

  # Strip any .git gitlink/dir copied from a submodule-rooted source.
  rm -rf "${target_dir}/.git"

  echo_green "  -> Copied to ${target_dir}"
  echo_green "  -> ${skill_name} installed successfully"
  echo
}


#######################################
# Installs a local skill by copying it
#   directly into ~/.claude/skills/.
#   No ~/.agents/skills/ copy or symlinks
#   are created — Claude Code exclusive.
# Arguments:
#   source_path: Absolute path to the
#                local skill directory
#   skill_name:  Skill name (directory name)
# Globals:
#   FAILED_CLAUDE_COPY_SKILLS (appended on failure)
#######################################
install_local_claude_copy_skill(){
  local source_path="${1}"
  local skill_name="${2}"
  local claude_dir="${HOME}/.claude/skills"
  local target_dir="${claude_dir}/${skill_name}"

  echo_blue "Installing local Claude skill: ${skill_name}  (from ${source_path})"

  if [[ ! -d "${source_path}" ]]; then
    echo_red "  -> Source directory not found: ${source_path}"
    FAILED_CLAUDE_COPY_SKILLS+=("${skill_name}")
    echo
    return
  fi

  # Copy skill directly to ~/.claude/skills/
  mkdir -p "${claude_dir}"

  if [[ -d "${target_dir}" ]]; then
    echo_yellow "  -> Target exists, updating: ${target_dir}"
    rm -rf "${target_dir}"
  fi

  if ! cp -R "${source_path}" "${target_dir}"; then
    echo_red "  -> Failed to copy ${skill_name} to ${target_dir}"
    FAILED_CLAUDE_COPY_SKILLS+=("${skill_name}")
    echo
    return
  fi

  # Strip any .git gitlink/dir copied from a submodule-rooted source.
  rm -rf "${target_dir}/.git"

  echo_green "  -> Copied to ${target_dir}"
  echo_green "  -> ${skill_name} installed successfully"
  echo
}


#######################################
# Installs a Claude Code hook.
#   CLAUDE CODE SPECIFIC — no other agent
#   reads ~/.claude/settings.json.
#
#   Copies the hook scripts into
#   ~/.claude/hooks/<hook-name>/ and merges
#   claude-hooks.json into the "hooks" object
#   of ~/.claude/settings.json.
#
#   Idempotent: a hook entry whose command is
#   already present is skipped, so re-running
#   never duplicates entries. Scripts are
#   always refreshed so updates land.
#
# Arguments:
#   1 - source hooks directory
#   2 - hook name
#######################################
install_claude_hook(){
  local source_dir="${1}"
  local hook_name="${2}"
  local hook_dir="${HOME}/.claude/hooks/${hook_name}"
  local settings="${HOME}/.claude/settings.json"
  local fragment="${source_dir}/claude-hooks.json"

  echo_blue "Installing Claude Code hook: ${hook_name}  (from ${source_dir})"

  if [[ ! -d "${source_dir}" ]]; then
    echo_red "  -> Source directory not found: ${source_dir}"
    FAILED_CLAUDE_HOOKS+=("${hook_name}")
    echo
    return
  fi

  if [[ ! -f "${fragment}" ]]; then
    echo_red "  -> Missing claude-hooks.json in ${source_dir}"
    FAILED_CLAUDE_HOOKS+=("${hook_name}")
    echo
    return
  fi

  if ! jq -e . "${fragment}" >/dev/null 2>&1; then
    echo_red "  -> claude-hooks.json is not valid JSON: ${fragment}"
    FAILED_CLAUDE_HOOKS+=("${hook_name}")
    echo
    return
  fi

  # ---- Copy the hook scripts (always refresh) ----
  mkdir -p "${hook_dir}"
  local script_count=0
  local f
  for f in "${source_dir}"/*.sh; do
    [[ -e "${f}" ]] || continue
    if ! cp "${f}" "${hook_dir}/"; then
      echo_red "  -> Failed to copy $(basename "${f}") to ${hook_dir}"
      FAILED_CLAUDE_HOOKS+=("${hook_name}")
      echo
      return
    fi
    chmod +x "${hook_dir}/$(basename "${f}")"
    script_count=$(( script_count + 1 ))
  done

  if [[ ${script_count} -eq 0 ]]; then
    echo_red "  -> No .sh scripts found in ${source_dir}"
    FAILED_CLAUDE_HOOKS+=("${hook_name}")
    echo
    return
  fi

  echo_green "  -> Copied ${script_count} script(s) to ${hook_dir}"

  # ---- Resolve __HOOK_DIR__ into the real install path ----
  local resolved
  if ! resolved="$(sed "s|__HOOK_DIR__|${hook_dir}|g" "${fragment}")"; then
    echo_red "  -> Failed to resolve __HOOK_DIR__ in ${fragment}"
    FAILED_CLAUDE_HOOKS+=("${hook_name}")
    echo
    return
  fi

  # ---- Ensure settings.json exists and is valid ----
  mkdir -p "$(dirname "${settings}")"
  if [[ ! -f "${settings}" ]]; then
    echo '{}' > "${settings}"
    echo_yellow "  -> Created ${settings}"
  elif ! jq -e . "${settings}" >/dev/null 2>&1; then
    echo_red "  -> ${settings} is not valid JSON — refusing to modify it"
    FAILED_CLAUDE_HOOKS+=("${hook_name}")
    echo
    return
  fi

  # ---- Already installed? ----
  # Match on the resolved command strings. If every command in the fragment
  # is already present under its event, there is nothing to do.
  local missing
  missing="$(jq -n \
    --argjson frag "${resolved}" \
    --slurpfile cur "${settings}" \
    '
      ($cur[0].hooks // {}) as $existing
      | [ $frag | to_entries[]
          | .key as $event
          | .value[]
          | .hooks[]
          | .command
          | select( ( [ $existing[$event] // [] | .[]? | .hooks[]? | .command ] | index(.) ) == null )
        ] | length
    ' 2>/dev/null)" || missing=""

  if [[ -z "${missing}" ]]; then
    echo_red "  -> Failed to inspect existing hooks in ${settings}"
    FAILED_CLAUDE_HOOKS+=("${hook_name}")
    echo
    return
  fi

  if [[ "${missing}" -eq 0 ]]; then
    echo_green "  -> Already installed in ${settings} — scripts refreshed, settings unchanged"
    echo_green "  -> ${hook_name} hook installed successfully"
    echo
    return
  fi

  # ---- Back up, then merge only the missing entries ----
  local backup="${settings}.bak.$(date +%Y%m%d%H%M%S)"
  cp "${settings}" "${backup}"

  local merged
  if ! merged="$(jq \
    --argjson frag "${resolved}" \
    '
      .hooks = ( (.hooks // {}) as $existing
        | reduce ($frag | to_entries[]) as $e ($existing;
            .[$e.key] = ( ( .[$e.key] // [] )
              + [ $e.value[]
                  | select( [ .hooks[].command ] as $new
                      | ( [ $existing[$e.key] // [] | .[]? | .hooks[]? | .command ] ) as $old
                      | ( $new | map( . as $c | $old | index($c) ) | all(. == null) ) )
                ] )
          ) )
    ' "${settings}")"; then
    echo_red "  -> jq merge failed — ${settings} left unchanged (backup: ${backup})"
    FAILED_CLAUDE_HOOKS+=("${hook_name}")
    echo
    return
  fi

  # Validate before overwriting the real file.
  if ! printf '%s' "${merged}" | jq -e . >/dev/null 2>&1; then
    echo_red "  -> Merged settings are not valid JSON — ${settings} left unchanged (backup: ${backup})"
    FAILED_CLAUDE_HOOKS+=("${hook_name}")
    echo
    return
  fi

  printf '%s\n' "${merged}" > "${settings}"

  echo_green "  -> Merged ${missing} hook entr(y/ies) into ${settings}"
  echo_green "  -> Backup written to ${backup}"
  echo_yellow "  -> Open /hooks once (or restart Claude Code) to load it in a running session"
  echo_green "  -> ${hook_name} hook installed successfully"
  echo
}


#######################################
# Checks if Anti-Gravity is installed.
#   Returns 0 if `agy` command exists or
#   ~/.gemini/antigravity directory exists.
#######################################
is_antigravity_installed(){
  if command -v agy &>/dev/null || [[ -d "${HOME}/.gemini/antigravity" ]]; then
    return 0
  else
    return 1
  fi
}


#######################################
# Installs an Anti-Gravity skill by copying it
#   into ~/.agents/skills/<skill_name>/ and
#   adapting SKILL.md frontmatter name and text
#   to Anti-Gravity.
# Arguments:
#   source_path: Absolute path to the local skill directory
#   skill_name:  Skill target directory name (e.g. judgement-engineering-agy)
# Globals:
#   FAILED_ANTIGRAVITY_COPY_SKILLS (appended on failure)
#######################################
install_antigravity_copy_skill(){
  local source_path="${1}"
  local skill_name="${2}"
  local agents_dir="${HOME}/.agents/skills"
  local target_dir="${agents_dir}/${skill_name}"

  echo_blue "Installing Anti-Gravity skill: ${skill_name}  (adapted from ${source_path})"

  if [[ ! -d "${source_path}" ]]; then
    echo_red "  -> Source directory not found: ${source_path}"
    FAILED_ANTIGRAVITY_COPY_SKILLS+=("${skill_name}")
    echo
    return
  fi

  # Ensure ~/.agents/skills/ directory exists
  mkdir -p "${agents_dir}"

  if [[ -d "${target_dir}" ]]; then
    echo_yellow "  -> Target exists, updating: ${target_dir}"
    rm -rf "${target_dir}"
  fi

  if ! cp -R "${source_path}" "${target_dir}"; then
    echo_red "  -> Failed to copy ${skill_name} to ${target_dir}"
    FAILED_ANTIGRAVITY_COPY_SKILLS+=("${skill_name}")
    echo
    return
  fi

  # Strip any .git directory copied from submodule
  rm -rf "${target_dir}/.git"

  # Adapt SKILL.md for Anti-Gravity
  if [[ -f "${target_dir}/SKILL.md" ]]; then
    local tmp_file
    tmp_file="$(mktemp)"
    sed -e "s/^name: .*/name: ${skill_name}/" \
        -e 's/Codex/Anti-Gravity/g' \
        -e 's/Claude Code/Anti-Gravity/g' \
        "${target_dir}/SKILL.md" > "${tmp_file}" && mv "${tmp_file}" "${target_dir}/SKILL.md"
  fi

  echo_green "  -> Adapted and copied to ${target_dir}"
  echo_green "  -> ${skill_name} installed successfully"
  echo
}


#######################################
# Idempotent repo-tool Claude MCP wrapper.
#   Tries add first; treats matching entry
#   as success; otherwise backs up config,
#   removes-and-readds, restores backup on
#   replacement-add failure.
# Arguments:
#   name:  MCP server name
#   scope: Scope flag (user, project)
#   cmd:   Command to run the server
# Globals:
#   FAILED_MCPS (appended on failure)
#######################################
install_repo_tool_claude_mcp(){
  local name="${1}" scope="${2}" cmd="${3}"
  local config="${HOME}/.claude.json"
  local backup

  echo_blue "Installing repo-tool Claude MCP: ${name}  (scope: ${scope})"
  if claude mcp add -s "${scope}" "${name}" -- ${cmd}; then
    echo_green "  -> Claude MCP ${name} installed successfully"
  elif claude mcp list 2>/dev/null | grep -F "${name}" | grep -F "${cmd}" >/dev/null; then
    echo_green "  -> Claude MCP ${name} already installed"
  else
    backup="$(mktemp)"
    [[ -f "${config}" ]] && cp "${config}" "${backup}" || true
    claude mcp remove -s "${scope}" "${name}" >/dev/null 2>&1 || true
    if claude mcp add -s "${scope}" "${name}" -- ${cmd}; then
      echo_green "  -> Claude MCP ${name} replaced successfully"
    else
      [[ -s "${backup}" ]] && cp "${backup}" "${config}"
      echo_red "  -> Failed to install Claude MCP ${name}"
      FAILED_MCPS+=("${name}")
    fi
    rm -f "${backup}"
  fi
  echo
}


#######################################
# Idempotent repo-tool Codex MCP wrapper.
#   Tries add first; treats matching entry
#   as success; otherwise backs up config,
#   removes-and-readds, restores backup on
#   replacement-add failure.
# Arguments:
#   name:  MCP server name
#   scope: (ignored — kept for array compat)
#   cmd:   Command to run the server
# Globals:
#   FAILED_CODEX_MCPS (appended on failure)
#######################################
install_repo_tool_codex_mcp(){
  local name="${1}" scope="${2}" cmd="${3}"  # scope ignored by codex
  local config="${HOME}/.codex/config.toml"
  local backup

  echo_blue "Installing repo-tool Codex MCP: ${name}"
  if codex mcp add "${name}" -- ${cmd}; then
    echo_green "  -> Codex MCP ${name} installed successfully"
  elif codex mcp list 2>/dev/null | grep -F "${name}" | grep -F "${cmd}" >/dev/null; then
    echo_green "  -> Codex MCP ${name} already installed"
  else
    backup="$(mktemp)"
    [[ -f "${config}" ]] && cp "${config}" "${backup}" || true
    codex mcp remove "${name}" >/dev/null 2>&1 || true
    if codex mcp add "${name}" -- ${cmd}; then
      echo_green "  -> Codex MCP ${name} replaced successfully"
    else
      [[ -s "${backup}" ]] && cp "${backup}" "${config}"
      echo_red "  -> Failed to install Codex MCP ${name}"
      FAILED_CODEX_MCPS+=("${name}")
    fi
    rm -f "${backup}"
  fi
  echo
}


#######################################
# Installs a single Gemini CLI MCP server
#   using gemini mcp add. Same idempotent
#   add/match/backup-restore pattern as
#   Claude/Codex wrappers.
# Arguments:
#   name:  MCP server name
#   scope: Scope flag (user, project)
#   cmd:   Command to run the server
# Globals:
#   FAILED_GEMINI_MCPS (appended on failure)
#######################################
install_gemini_mcp(){
  local name="${1}" scope="${2}" cmd="${3}"
  local -a cmd_parts
  local config="${HOME}/.gemini/settings.json"
  local backup

  echo_blue "Installing Gemini MCP: ${name}  (scope: ${scope})"
  read -r -a cmd_parts <<< "${cmd}"
  if [[ ${#cmd_parts[@]} -eq 0 ]]; then
    echo_red "  -> Empty Gemini MCP command for ${name}"
    FAILED_GEMINI_MCPS+=("${name} (empty command)")
    echo
    return
  fi

  if gemini mcp add --scope "${scope}" "${name}" "${cmd_parts[@]}"; then
    echo_green "  -> Gemini MCP ${name} installed successfully"
  elif gemini mcp list 2>/dev/null | grep -F "${name}" | grep -F "${cmd}" >/dev/null; then
    echo_green "  -> Gemini MCP ${name} already installed"
  else
    backup="$(mktemp)"
    [[ -f "${config}" ]] && cp "${config}" "${backup}" || true
    gemini mcp remove --scope "${scope}" "${name}" >/dev/null 2>&1 || true
    if gemini mcp add --scope "${scope}" "${name}" "${cmd_parts[@]}"; then
      echo_green "  -> Gemini MCP ${name} replaced successfully"
    else
      [[ -s "${backup}" ]] && cp "${backup}" "${config}"
      echo_red "  -> Failed to install Gemini MCP ${name}"
      FAILED_GEMINI_MCPS+=("${name}")
    fi
    rm -f "${backup}"
  fi
  echo
}


#######################################
# Registers an MCP server for Antigravity
#   by merging into ~/.gemini/antigravity/
#   mcp_config.json via jq. Idempotent
#   assignment, preserves other keys.
# Arguments:
#   name: MCP server name
#   cmd:  Command to run the server
#         (space-separated string)
# Globals:
#   FAILED_ANTIGRAVITY_MCPS (appended on failure)
#######################################
install_antigravity_mcp(){
  local name="${1}" cmd="${2}"
  local config_dir="${HOME}/.gemini/antigravity"
  local config="${config_dir}/mcp_config.json"
  local -a cmd_parts

  echo_blue "Installing Antigravity MCP: ${name}"

  if ! command -v jq &>/dev/null; then
    echo_yellow "  -> jq not found; skipping Antigravity MCP registration for ${name}"
    FAILED_ANTIGRAVITY_MCPS+=("${name} (jq missing)")
    echo
    return
  fi

  if [[ ! -d "${config_dir}" ]]; then
    echo_yellow "  -> Antigravity dir not present (${config_dir}); skipping ${name}"
    echo
    return
  fi

  [[ -s "${config}" ]] || echo '{"mcpServers":{}}' > "${config}"

  read -r -a cmd_parts <<< "${cmd}"
  if [[ ${#cmd_parts[@]} -eq 0 ]]; then
    echo_red "  -> Empty Antigravity MCP command for ${name}"
    FAILED_ANTIGRAVITY_MCPS+=("${name} (empty command)")
    echo
    return
  fi

  local first rest_json
  first="${cmd_parts[0]}"
  rest_json=$(printf '%s\n' "${cmd_parts[@]:1}" | jq -R . | jq -s .)
  local tmp; tmp=$(mktemp)
  if jq --arg n "${name}" --arg c "${first}" --argjson a "${rest_json}" \
       '.mcpServers[$n] = {command:$c, args:$a}' "${config}" > "${tmp}"; then
    mv "${tmp}" "${config}"
    echo_green "  -> Antigravity MCP ${name} registered in ${config}"
  else
    rm -f "${tmp}"
    echo_red "  -> Failed to register Antigravity MCP ${name}"
    FAILED_ANTIGRAVITY_MCPS+=("${name}")
  fi
  echo
}


# =========================================================================
#
# Main function
#
# =========================================================================


#######################################
# Main function that parses arguments,
#   checks dependencies, and installs
#   all skills defined in the SKILLS
#   registry array.
# Arguments:
#   -h, -help, --help: Print usage
# Globals:
#   SKILLS
#   FAILED_SKILLS
#######################################
main(){
  #
  # Parse arguments
  #============================

  local install_local=false
  local install_math=false
  local install_repo_tools=false
  local install_engineering=false

  while [[ ${#} -gt 0 ]]; do
    case "${1}" in
      -h|-help|--help) Usage; ;;
      --local) install_local=true ;;
      --math)  install_math=true ;;
      --repo-tools) install_repo_tools=true ;;
      --eng|--engineering) install_engineering=true ;;
      -*) echo_red "$(basename ${0}): Unrecognized option ${1}" >&2; Usage; ;;
      *) break ;;
    esac
    shift
  done

  #
  # Dependency checks
  #============================

  if ! command -v npx &>/dev/null; then
    exit_error "npx not found. Please install Node.js (https://nodejs.org/) first."
  fi

  if ! command -v claude &>/dev/null; then
    echo_yellow "claude CLI not found — skipping Claude MCP server and plugin installation."
    local skip_claude=true
  fi

  if ! command -v codex &>/dev/null; then
    echo_yellow "codex CLI not found — skipping Codex MCP server and plugin installation."
    local skip_codex=true
  fi

  if ! is_antigravity_installed; then
    echo_yellow "Anti-Gravity not detected (neither 'agy' CLI nor ~/.gemini/antigravity found) — skipping Anti-Gravity specific skill installation."
    local skip_antigravity_skills=true
  fi

  #
  # uv bootstrap (default Python installer)
  #============================
  # uv is the default Python installer for this script: libraries via
  # `uv pip install` (py_install), standalone CLIs like SkillSpector via
  # `uv tool install`. If uv is missing, bootstrap it via pip --user
  # (honoring PEP 668). py_install falls back to each caller's interpreter's
  # pip when uv is unavailable or refuses a non-venv target.
  uv_ready=false
  if command -v uv &>/dev/null; then
    uv_ready=true
    echo_green "uv found: $(command -v uv)"
  else
    local boot_py=""
    if ! boot_py="$(detect_python_310)"; then
      if command -v python3 &>/dev/null; then
        boot_py="$(command -v python3)"
      fi
    fi
    if [[ -n "${boot_py}" ]]; then
      echo_blue "uv not found — bootstrapping via pip (using ${boot_py})..."
      if ! "${boot_py}" -m pip install --user uv; then
        # macOS Homebrew/system Python commonly needs PEP 668 override.
        "${boot_py}" -m pip install --user --break-system-packages uv || true
      fi
      # pip --user console scripts land under python's user-base bin
      # (macOS: ~/Library/Python/3.x/bin, NOT ~/.local/bin). Compute it.
      # Keep ~/.local/bin too — uv's own tool bin (SkillSpector) lives there.
      local userbase=""
      userbase="$("${boot_py}" -m site --user-base 2>/dev/null)"
      [[ -n "${userbase}" ]] && export PATH="${userbase}/bin:${HOME}/.local/bin:${PATH}"
      if command -v uv &>/dev/null; then
        uv_ready=true
        echo_green "uv bootstrapped: $(command -v uv)"
      else
        echo_yellow "uv bootstrap failed — Python installs will use pip directly."
      fi
    else
      echo_yellow "No Python found to bootstrap uv — Python installs will use pip directly."
    fi
  fi

  # Ensure uv's tool bin is on PATH so `skillspector` resolves post-install.
  export PATH="${HOME}/.local/bin:${PATH}"

  # Install SkillSpector first so the post-fetch scan can inspect every
  # installed skill (including remote npx-fetched ones).
  install_skillspector

  if [[ "${install_repo_tools}" == true ]]; then
    if ! command -v gemini &>/dev/null; then
      echo_yellow "gemini CLI not found — skipping Gemini MCP server registration."
      local skip_gemini=true
    fi
    if ! command -v jq &>/dev/null; then
      echo_yellow "jq not found — Antigravity MCP registration will be skipped."
      local skip_antigravity=true
    fi
    if [[ ! -d "${HOME}/.gemini/antigravity" ]]; then
      echo_yellow "Antigravity IDE not detected (~/.gemini/antigravity missing) — skipping its MCP registration."
      local skip_antigravity=true
    fi
  fi

  if [[ "${install_local}" == true ]]; then
    # The local pip phase prefers uv; the fallback uses "<py> -m pip". Only
    # skip when neither uv nor any "python -m pip" is available — a uv-only or
    # `python -m pip`-only machine (no bare `pip` shim) must NOT be skipped.
    local _lp_py=""
    _lp_py="$(detect_python_310 2>/dev/null)" || _lp_py=""
    if [[ "${uv_ready}" != true ]] \
       && { [[ -z "${_lp_py}" ]] || ! "${_lp_py}" -m pip --version >/dev/null 2>&1; }; then
      echo_yellow "Neither uv nor 'python -m pip' available — skipping local pip package installation."
      local skip_pip=true
    fi

    # Merge local skills into main skills array
    SKILLS+=("${LOCAL_SKILLS[@]}")
  fi

  if [[ "${install_engineering}" == true ]]; then
    SKILLS+=("${ENGINEERING_SKILLS[@]}")
  fi

  #
  # Install skills
  #============================

  FAILED_SKILLS=()

  local total=$(( ${#SKILLS[@]} / 2 ))

  echo
  echo_blue "=========================================="
  echo_blue " Installing ${total} Agent Skills"
  echo_blue " Agents: claude-code, antigravity"
  echo_blue "=========================================="
  echo

  local i=0
  while [[ ${i} -lt ${#SKILLS[@]} ]]; do
    local repo="${SKILLS[${i}]}"
    local skill="${SKILLS[$(( i + 1 ))]}"
    i=$(( i + 2 ))

    install_skill "${repo}" "${skill}"
  done

  #
  # Install MCP servers (Claude)
  #============================

  FAILED_MCPS=()

  local total_mcps=$(( ${#MCP_SERVERS[@]} / 3 ))

  if [[ "${skip_claude}" != true && ${total_mcps} -gt 0 ]]; then
    echo
    echo_blue "=========================================="
    echo_blue " Installing ${total_mcps} Claude MCP Server(s)"
    echo_blue "=========================================="
    echo

    local j=0
    while [[ ${j} -lt ${#MCP_SERVERS[@]} ]]; do
      local mcp_name="${MCP_SERVERS[${j}]}"
      local mcp_scope="${MCP_SERVERS[$(( j + 1 ))]}"
      local mcp_cmd="${MCP_SERVERS[$(( j + 2 ))]}"
      j=$(( j + 3 ))

      install_mcp "${mcp_name}" "${mcp_scope}" "${mcp_cmd}"
    done
  fi

  #
  # Install MCP servers (Codex)
  #============================

  FAILED_CODEX_MCPS=()

  if [[ "${skip_codex}" != true && ${total_mcps} -gt 0 ]]; then
    echo
    echo_blue "=========================================="
    echo_blue " Installing ${total_mcps} Codex MCP Server(s)"
    echo_blue "=========================================="
    echo

    local j=0
    while [[ ${j} -lt ${#MCP_SERVERS[@]} ]]; do
      local mcp_name="${MCP_SERVERS[${j}]}"
      local mcp_scope="${MCP_SERVERS[$(( j + 1 ))]}"
      local mcp_cmd="${MCP_SERVERS[$(( j + 2 ))]}"
      j=$(( j + 3 ))

      install_codex_mcp "${mcp_name}" "${mcp_scope}" "${mcp_cmd}"
    done
  fi

  #
  # Install npm global packages
  #============================

  FAILED_NPMS=()

  local total_npms=${#NPM_GLOBALS[@]}

  if [[ ${total_npms} -gt 0 ]]; then
    echo
    echo_blue "=========================================="
    echo_blue " Installing ${total_npms} npm Global Package(s)"
    echo_blue "=========================================="
    echo

    for pkg in "${NPM_GLOBALS[@]}"; do
      install_npm_global "${pkg}"
    done
  fi

  #
  # Install agents-only copy skills (always)
  #============================

  FAILED_AGENTS_COPY_SKILLS=()

  local total_agents_copy_skills=$(( ${#AGENTS_COPY_SKILLS[@]} / 2 ))

  if [[ ${total_agents_copy_skills} -gt 0 ]]; then
    echo
    echo_blue "=========================================="
    echo_blue " Installing ${total_agents_copy_skills} Agents-Only Skill(s)"
    echo_blue "=========================================="
    echo

    local m=0
    while [[ ${m} -lt ${#AGENTS_COPY_SKILLS[@]} ]]; do
      local copy_source="${AGENTS_COPY_SKILLS[${m}]}"
      local copy_skill="${AGENTS_COPY_SKILLS[$(( m + 1 ))]}"
      m=$(( m + 2 ))

      install_agents_copy_skill "${copy_source}" "${copy_skill}"
    done
  fi

  #
  # Install Claude-only copy skills (always)
  #============================

  FAILED_CLAUDE_COPY_SKILLS=()

  local total_claude_copy_skills=$(( ${#CLAUDE_COPY_SKILLS[@]} / 2 ))

  if [[ ${total_claude_copy_skills} -gt 0 ]]; then
    echo
    echo_blue "=========================================="
    echo_blue " Installing ${total_claude_copy_skills} Claude-Only Skill(s)"
    echo_blue "=========================================="
    echo

    local n=0
    while [[ ${n} -lt ${#CLAUDE_COPY_SKILLS[@]} ]]; do
      local claude_copy_source="${CLAUDE_COPY_SKILLS[${n}]}"
      local claude_copy_skill="${CLAUDE_COPY_SKILLS[$(( n + 1 ))]}"
      n=$(( n + 2 ))

      install_local_claude_copy_skill "${claude_copy_source}" "${claude_copy_skill}"
    done
  fi

  #
  # Install Claude Code hooks (always) - CLAUDE CODE SPECIFIC
  #============================

  FAILED_CLAUDE_HOOKS=()

  local total_claude_hooks=$(( ${#CLAUDE_HOOKS[@]} / 2 ))

  if [[ ${total_claude_hooks} -gt 0 ]]; then
    if [[ "${skip_claude}" == true ]]; then
      echo
      echo_yellow "Skipping ${total_claude_hooks} Claude Code hook(s) — claude CLI not found."
    elif ! command -v jq &>/dev/null; then
      echo
      echo_yellow "Skipping ${total_claude_hooks} Claude Code hook(s) — jq not found (required to merge settings.json safely)."
    else
      echo
      echo_blue "=========================================="
      echo_blue " Installing ${total_claude_hooks} Claude Code Hook(s)"
      echo_blue "=========================================="
      echo

      local h=0
      while [[ ${h} -lt ${#CLAUDE_HOOKS[@]} ]]; do
        local hook_source="${CLAUDE_HOOKS[${h}]}"
        local hook_name="${CLAUDE_HOOKS[$(( h + 1 ))]}"
        h=$(( h + 2 ))

        install_claude_hook "${hook_source}" "${hook_name}"
      done
    fi
  fi

  #
  # Install Anti-Gravity copy skills (adapted *-agy skills)
  #============================

  FAILED_ANTIGRAVITY_COPY_SKILLS=()

  local total_antigravity_copy_skills=$(( ${#ANTIGRAVITY_COPY_SKILLS[@]} / 2 ))

  if [[ "${skip_antigravity_skills}" != true && ${total_antigravity_copy_skills} -gt 0 ]]; then
    echo
    echo_blue "=========================================="
    echo_blue " Installing ${total_antigravity_copy_skills} Anti-Gravity Skill(s)"
    echo_blue " Target: ~/.agents/skills/"
    echo_blue "=========================================="
    echo

    local agy_idx=0
    while [[ ${agy_idx} -lt ${#ANTIGRAVITY_COPY_SKILLS[@]} ]]; do
      local agy_source="${ANTIGRAVITY_COPY_SKILLS[${agy_idx}]}"
      local agy_skill="${ANTIGRAVITY_COPY_SKILLS[$(( agy_idx + 1 ))]}"
      agy_idx=$(( agy_idx + 2 ))

      install_antigravity_copy_skill "${agy_source}" "${agy_skill}"
    done
  fi

  #
  # Install shared copy skills (always)
  #============================

  FAILED_COPY_SKILLS_ALWAYS=()

  local total_copy_skills=$(( ${#COPY_SKILLS[@]} / 2 ))

  if [[ ${total_copy_skills} -gt 0 ]]; then
    echo
    echo_blue "=========================================="
    echo_blue " Installing ${total_copy_skills} Shared Copy Skill(s)"
    echo_blue "=========================================="
    echo

    local p=0
    while [[ ${p} -lt ${#COPY_SKILLS[@]} ]]; do
      local shared_copy_source="${COPY_SKILLS[${p}]}"
      local shared_copy_skill="${COPY_SKILLS[$(( p + 1 ))]}"
      p=$(( p + 2 ))

      install_local_copy_skill "${shared_copy_source}" "${shared_copy_skill}" FAILED_COPY_SKILLS_ALWAYS
    done
  fi

  #
  # Install local pip packages (--local only)
  #============================

  FAILED_PIPS=()

  local total_pips=${#LOCAL_PIP_PACKAGES[@]}

  if [[ "${install_local}" == true && "${skip_pip}" != true && ${total_pips} -gt 0 ]]; then
    echo
    echo_blue "=========================================="
    echo_blue " Installing ${total_pips} pip Package(s) (local)"
    echo_blue "=========================================="
    echo

    # Resolve one interpreter for the whole phase (active python / detect).
    local local_pip_py=""
    if ! local_pip_py="$(detect_python_310)"; then
      echo_red "No Python >=3.10 found for local pip packages — skipping."
      FAILED_PIPS+=("${LOCAL_PIP_PACKAGES[@]}")
    else
      echo_blue "Using Python: ${local_pip_py}"
      for pkg in "${LOCAL_PIP_PACKAGES[@]}"; do
        install_pip_package "${pkg}" "${local_pip_py}"
      done
    fi
  fi

  #
  # Install local copy skills (--local only)
  #============================

  FAILED_COPY_SKILLS=()

  local total_local_copy_skills=$(( ${#LOCAL_COPY_SKILLS[@]} / 2 ))

  if [[ "${install_local}" == true && ${total_local_copy_skills} -gt 0 ]]; then
    echo
    echo_blue "=========================================="
    echo_blue " Installing ${total_local_copy_skills} Local Copy Skill(s)"
    echo_blue "=========================================="
    echo

    local m=0
    while [[ ${m} -lt ${#LOCAL_COPY_SKILLS[@]} ]]; do
      local copy_source="${LOCAL_COPY_SKILLS[${m}]}"
      local copy_skill="${LOCAL_COPY_SKILLS[$(( m + 1 ))]}"
      m=$(( m + 2 ))

      install_local_copy_skill "${copy_source}" "${copy_skill}"
    done
  fi

  #
  # Install local Claude-only copy skills (--local only)
  #============================

  local total_local_claude_copy_skills=$(( ${#LOCAL_CLAUDE_COPY_SKILLS[@]} / 2 ))

  if [[ "${install_local}" == true && ${total_local_claude_copy_skills} -gt 0 ]]; then
    echo
    echo_blue "=========================================="
    echo_blue " Installing ${total_local_claude_copy_skills} Local Claude-Only Skill(s)"
    echo_blue "=========================================="
    echo

    local n=0
    while [[ ${n} -lt ${#LOCAL_CLAUDE_COPY_SKILLS[@]} ]]; do
      local claude_copy_source="${LOCAL_CLAUDE_COPY_SKILLS[${n}]}"
      local claude_copy_skill="${LOCAL_CLAUDE_COPY_SKILLS[$(( n + 1 ))]}"
      n=$(( n + 2 ))

      install_local_claude_copy_skill "${claude_copy_source}" "${claude_copy_skill}"
    done
  fi

  #
  # Install math copy skills (--math only)
  #============================

  FAILED_MATH_COPY_SKILLS=()

  local total_math_copy_skills=$(( ${#MATH_COPY_SKILLS[@]} / 2 ))

  if [[ "${install_math}" == true && ${total_math_copy_skills} -gt 0 ]]; then
    echo
    echo_blue "=========================================="
    echo_blue " Installing ${total_math_copy_skills} Math Copy Skill(s)"
    echo_blue "=========================================="
    echo

    local q=0
    while [[ ${q} -lt ${#MATH_COPY_SKILLS[@]} ]]; do
      local math_source="${MATH_COPY_SKILLS[${q}]}"
      local math_skill="${MATH_COPY_SKILLS[$(( q + 1 ))]}"
      q=$(( q + 2 ))

      install_local_copy_skill "${math_source}" "${math_skill}" FAILED_MATH_COPY_SKILLS
    done
  fi

  #
  # Install Claude Code plugins
  #============================

  FAILED_PLUGINS=()

  local total_plugins=$(( ${#PLUGINS[@]} / 3 ))

  if [[ "${skip_claude}" != true && ${total_plugins} -gt 0 ]]; then
    echo
    echo_blue "=========================================="
    echo_blue " Installing ${total_plugins} Claude Code Plugin(s)"
    echo_blue "=========================================="
    echo

    local k=0
    while [[ ${k} -lt ${#PLUGINS[@]} ]]; do
      local plugin_source="${PLUGINS[${k}]}"
      local plugin_id="${PLUGINS[$(( k + 1 ))]}"
      local mkt_name="${PLUGINS[$(( k + 2 ))]}"
      k=$(( k + 3 ))

      install_plugin "${plugin_source}" "${plugin_id}" "${mkt_name}"
    done
  fi

  #
  # Install Codex plugins
  #============================

  FAILED_CODEX_PLUGINS=()

  local total_codex_plugins=$(( ${#CODEX_PLUGINS[@]} / 4 ))

  if [[ "${skip_codex}" != true && ${total_codex_plugins} -gt 0 ]]; then
    echo
    echo_blue "=========================================="
    echo_blue " Installing ${total_codex_plugins} Codex Plugin(s)"
    echo_blue "=========================================="
    echo

    local l=0
    while [[ ${l} -lt ${#CODEX_PLUGINS[@]} ]]; do
      local codex_source_repo="${CODEX_PLUGINS[${l}]}"
      local codex_plugin_name="${CODEX_PLUGINS[$(( l + 1 ))]}"
      local codex_marketplace_name="${CODEX_PLUGINS[$(( l + 2 ))]}"
      local codex_plugin_path="${CODEX_PLUGINS[$(( l + 3 ))]}"
      l=$(( l + 4 ))

      install_codex_plugin \
        "${codex_source_repo}" \
        "${codex_plugin_name}" \
        "${codex_marketplace_name}" \
        "${codex_plugin_path}"
    done
  fi

  #
  # Install repo tools (--repo-tools only)
  #============================

  FAILED_REPO_TOOL_PIPS=()
  FAILED_REPO_TOOL_NPMS=()
  FAILED_GEMINI_MCPS=()
  FAILED_ANTIGRAVITY_MCPS=()

  local repo_total_pips=${#REPO_TOOL_PIP_PACKAGES[@]}
  local repo_total_npms=${#REPO_TOOL_NPM_GLOBALS[@]}
  local repo_total_mcps=$(( ${#REPO_TOOL_MCP_SERVERS[@]} / 3 ))

  if [[ "${install_repo_tools}" == true ]]; then
    local repo_gitnexus_ready=true

    # Phase: repo-tool pip packages (Graphify)
    if [[ ${repo_total_pips} -gt 0 ]]; then
      echo
      echo_blue "=========================================="
      echo_blue " Installing ${repo_total_pips} Repo-Tool pip Package(s)"
      echo_blue "=========================================="
      echo

      local repo_py
      if ! repo_py="$(detect_python_310)"; then
        echo_red "No Python >=3.10 found on PATH (checked: python, python3, python3.10–3.13)."
        echo_red "Skipping repo-tool pip packages. Activate a conda env or install Python 3.10+."
        FAILED_REPO_TOOL_PIPS+=("${REPO_TOOL_PIP_PACKAGES[@]}")
      else
        echo_blue "Using Python: ${repo_py}"
        for pkg in "${REPO_TOOL_PIP_PACKAGES[@]}"; do
          install_repo_tool_pip "${pkg}" "${repo_py}"
        done
      fi
    fi

    # Phase: repo-tool npm globals (GitNexus)
    if [[ ${repo_total_npms} -gt 0 ]]; then
      echo
      echo_blue "=========================================="
      echo_blue " Installing ${repo_total_npms} Repo-Tool npm Global(s)"
      echo_blue "=========================================="
      echo

      local node_major
      node_major="$(node -v 2>/dev/null | sed 's/^v\([0-9]*\).*/\1/')"
      if [[ -z "${node_major}" ]]; then
        echo_red "Node.js not found; GitNexus requires Node >=22. Skipping repo-tool npm packages and GitNexus MCP registration."
        FAILED_REPO_TOOL_NPMS+=("${REPO_TOOL_NPM_GLOBALS[@]}")
        repo_gitnexus_ready=false
      elif [[ "${node_major}" -lt 22 ]]; then
        echo_red "Node ${node_major} detected; GitNexus requires Node >=22. Skipping GitNexus install and MCP registration."
        FAILED_REPO_TOOL_NPMS+=("${REPO_TOOL_NPM_GLOBALS[@]}")
        repo_gitnexus_ready=false
      else
        for pkg in "${REPO_TOOL_NPM_GLOBALS[@]}"; do
          install_repo_tool_npm "${pkg}"
        done
        if [[ ${#FAILED_REPO_TOOL_NPMS[@]} -gt 0 ]]; then
          repo_gitnexus_ready=false
        fi
      fi
    fi

    # Phase: repo-tool MCP servers (Claude / Codex / Gemini / Antigravity)
    if [[ "${repo_gitnexus_ready}" != true && ${repo_total_mcps} -gt 0 ]]; then
      echo_yellow "Skipping GitNexus MCP registration because GitNexus is not available."
      local k=0
      while [[ ${k} -lt ${#REPO_TOOL_MCP_SERVERS[@]} ]]; do
        local rt_name="${REPO_TOOL_MCP_SERVERS[${k}]}"
        FAILED_MCPS+=("${rt_name} (skipped: GitNexus unavailable)")
        FAILED_CODEX_MCPS+=("${rt_name} (skipped: GitNexus unavailable)")
        FAILED_GEMINI_MCPS+=("${rt_name} (skipped: GitNexus unavailable)")
        FAILED_ANTIGRAVITY_MCPS+=("${rt_name} (skipped: GitNexus unavailable)")
        k=$(( k + 3 ))
      done
    else
      if [[ "${skip_claude}" != true && ${repo_total_mcps} -gt 0 ]]; then
        echo
        echo_blue "=========================================="
        echo_blue " Installing ${repo_total_mcps} Repo-Tool Claude MCP(s)"
        echo_blue "=========================================="
        echo
        local k=0
        while [[ ${k} -lt ${#REPO_TOOL_MCP_SERVERS[@]} ]]; do
          install_repo_tool_claude_mcp \
            "${REPO_TOOL_MCP_SERVERS[${k}]}" \
            "${REPO_TOOL_MCP_SERVERS[$(( k + 1 ))]}" \
            "${REPO_TOOL_MCP_SERVERS[$(( k + 2 ))]}"
          k=$(( k + 3 ))
        done
      fi

      if [[ "${skip_codex}" != true && ${repo_total_mcps} -gt 0 ]]; then
        echo
        echo_blue "=========================================="
        echo_blue " Installing ${repo_total_mcps} Repo-Tool Codex MCP(s)"
        echo_blue "=========================================="
        echo
        local k=0
        while [[ ${k} -lt ${#REPO_TOOL_MCP_SERVERS[@]} ]]; do
          install_repo_tool_codex_mcp \
            "${REPO_TOOL_MCP_SERVERS[${k}]}" \
            "${REPO_TOOL_MCP_SERVERS[$(( k + 1 ))]}" \
            "${REPO_TOOL_MCP_SERVERS[$(( k + 2 ))]}"
          k=$(( k + 3 ))
        done
      fi

      if [[ "${skip_gemini}" != true && ${repo_total_mcps} -gt 0 ]]; then
        echo
        echo_blue "=========================================="
        echo_blue " Installing ${repo_total_mcps} Repo-Tool Gemini MCP(s)"
        echo_blue "=========================================="
        echo
        local k=0
        while [[ ${k} -lt ${#REPO_TOOL_MCP_SERVERS[@]} ]]; do
          install_gemini_mcp \
            "${REPO_TOOL_MCP_SERVERS[${k}]}" \
            "${REPO_TOOL_MCP_SERVERS[$(( k + 1 ))]}" \
            "${REPO_TOOL_MCP_SERVERS[$(( k + 2 ))]}"
          k=$(( k + 3 ))
        done
      fi

      if [[ "${skip_antigravity}" != true && ${repo_total_mcps} -gt 0 ]]; then
        echo
        echo_blue "=========================================="
        echo_blue " Installing ${repo_total_mcps} Repo-Tool Antigravity MCP(s)"
        echo_blue "=========================================="
        echo
        local k=0
        while [[ ${k} -lt ${#REPO_TOOL_MCP_SERVERS[@]} ]]; do
          install_antigravity_mcp \
            "${REPO_TOOL_MCP_SERVERS[${k}]}" \
            "${REPO_TOOL_MCP_SERVERS[$(( k + 2 ))]}"
          k=$(( k + 3 ))
        done
      fi
    fi
  fi

  #
  # SkillSpector scan (after all install phases, before the summary)
  #============================
  # Runs after every install phase (skills, copy/local/math/repo-tools) so
  # all installed skills — including remote npx-fetched ones — are inspected.
  run_skillspector_scan

  #
  # Summary
  #============================

  echo
  echo_blue "=========================================="

  if [[ ${#FAILED_SKILLS[@]} -eq 0 ]]; then
    echo_green " All ${total} skills installed successfully!"
  else
    echo_yellow " ${#FAILED_SKILLS[@]} skill(s) failed to install:"
    for skill in "${FAILED_SKILLS[@]}"; do
      echo_red "   - ${skill}"
    done
  fi

  if [[ ( "${skip_claude}" != true && ${total_mcps} -gt 0 ) || \
        ( "${install_repo_tools}" == true && ${repo_total_mcps} -gt 0 ) ]]; then
    if [[ ${#FAILED_MCPS[@]} -eq 0 ]]; then
      echo_green " Claude MCP server(s) installed successfully!"
    else
      echo_yellow " ${#FAILED_MCPS[@]} Claude MCP server(s) failed to install:"
      for mcp in "${FAILED_MCPS[@]}"; do
        echo_red "   - ${mcp}"
      done
    fi
  fi

  if [[ ( "${skip_codex}" != true && ${total_mcps} -gt 0 ) || \
        ( "${install_repo_tools}" == true && ${repo_total_mcps} -gt 0 ) ]]; then
    if [[ ${#FAILED_CODEX_MCPS[@]} -eq 0 ]]; then
      echo_green " Codex MCP server(s) installed successfully!"
    else
      echo_yellow " ${#FAILED_CODEX_MCPS[@]} Codex MCP server(s) failed to install:"
      for mcp in "${FAILED_CODEX_MCPS[@]}"; do
        echo_red "   - ${mcp}"
      done
    fi
  fi

  if [[ ${#FAILED_NPMS[@]} -eq 0 && ${total_npms} -gt 0 ]]; then
    echo_green " All ${total_npms} npm global package(s) installed successfully!"
  elif [[ ${#FAILED_NPMS[@]} -gt 0 ]]; then
    echo_yellow " ${#FAILED_NPMS[@]} npm global package(s) failed to install:"
    for pkg in "${FAILED_NPMS[@]}"; do
      echo_red "   - ${pkg}"
    done
  fi

  if [[ "${install_local}" == true && "${skip_pip}" != true && ${total_pips} -gt 0 ]]; then
    if [[ ${#FAILED_PIPS[@]} -eq 0 ]]; then
      echo_green " All ${total_pips} pip package(s) installed successfully!"
    else
      echo_yellow " ${#FAILED_PIPS[@]} pip package(s) failed to install:"
      for pkg in "${FAILED_PIPS[@]}"; do
        echo_red "   - ${pkg}"
      done
    fi
  fi

  if [[ ${total_agents_copy_skills} -gt 0 ]]; then
    if [[ ${#FAILED_AGENTS_COPY_SKILLS[@]} -eq 0 ]]; then
      echo_green " All ${total_agents_copy_skills} agents-only skill(s) installed successfully!"
    else
      echo_yellow " ${#FAILED_AGENTS_COPY_SKILLS[@]} agents-only skill(s) failed to install:"
      for skill in "${FAILED_AGENTS_COPY_SKILLS[@]}"; do
        echo_red "   - ${skill}"
      done
    fi
  fi

  if [[ ${total_copy_skills} -gt 0 ]]; then
    if [[ ${#FAILED_COPY_SKILLS_ALWAYS[@]} -eq 0 ]]; then
      echo_green " All ${total_copy_skills} shared copy skill(s) installed successfully!"
    else
      echo_yellow " ${#FAILED_COPY_SKILLS_ALWAYS[@]} shared copy skill(s) failed to install:"
      for skill in "${FAILED_COPY_SKILLS_ALWAYS[@]}"; do
        echo_red "   - ${skill}"
      done
    fi
  fi

  if [[ "${install_math}" == true && ${total_math_copy_skills} -gt 0 ]]; then
    if [[ ${#FAILED_MATH_COPY_SKILLS[@]} -eq 0 ]]; then
      echo_green " All ${total_math_copy_skills} math copy skill(s) installed successfully!"
    else
      echo_yellow " ${#FAILED_MATH_COPY_SKILLS[@]} math copy skill(s) failed to install:"
      for skill in "${FAILED_MATH_COPY_SKILLS[@]}"; do
        echo_red "   - ${skill}"
      done
    fi
  fi

  if [[ "${install_local}" == true && ${total_local_copy_skills} -gt 0 ]]; then
    if [[ ${#FAILED_COPY_SKILLS[@]} -eq 0 ]]; then
      echo_green " All ${total_local_copy_skills} local copy skill(s) installed successfully!"
    else
      echo_yellow " ${#FAILED_COPY_SKILLS[@]} local copy skill(s) failed to install:"
      for skill in "${FAILED_COPY_SKILLS[@]}"; do
        echo_red "   - ${skill}"
      done
    fi
  fi

  local all_claude_copy_skills=${total_claude_copy_skills}
  [[ "${install_local}" == true ]] && all_claude_copy_skills=$(( all_claude_copy_skills + total_local_claude_copy_skills ))

  if [[ "${skip_antigravity_skills}" != true && ${total_antigravity_copy_skills} -gt 0 ]]; then
    if [[ ${#FAILED_ANTIGRAVITY_COPY_SKILLS[@]} -eq 0 ]]; then
      echo_green " All ${total_antigravity_copy_skills} Anti-Gravity skill(s) installed successfully!"
    else
      echo_yellow " ${#FAILED_ANTIGRAVITY_COPY_SKILLS[@]} Anti-Gravity skill(s) failed to install:"
      for skill in "${FAILED_ANTIGRAVITY_COPY_SKILLS[@]}"; do
        echo_red "   - ${skill}"
      done
    fi
  fi

  if [[ ${all_claude_copy_skills} -gt 0 ]]; then
    if [[ ${#FAILED_CLAUDE_COPY_SKILLS[@]} -eq 0 ]]; then
      echo_green " All ${all_claude_copy_skills} Claude-only skill(s) installed successfully!"
    else
      echo_yellow " ${#FAILED_CLAUDE_COPY_SKILLS[@]} Claude-only skill(s) failed to install:"
      for skill in "${FAILED_CLAUDE_COPY_SKILLS[@]}"; do
        echo_red "   - ${skill}"
      done
    fi
  fi

  if [[ ${total_claude_hooks} -gt 0 ]]; then
    if [[ ${#FAILED_CLAUDE_HOOKS[@]} -eq 0 ]]; then
      echo_green " All ${total_claude_hooks} Claude Code hook(s) installed successfully!"
    else
      echo_yellow " ${#FAILED_CLAUDE_HOOKS[@]} Claude Code hook(s) failed to install:"
      for hook in "${FAILED_CLAUDE_HOOKS[@]}"; do
        echo_red "   - ${hook}"
      done
    fi
  fi

  if [[ "${skip_claude}" != true ]]; then
    if [[ ${#FAILED_PLUGINS[@]} -eq 0 && ${total_plugins} -gt 0 ]]; then
      echo_green " All ${total_plugins} Claude Code plugin(s) installed successfully!"
    elif [[ ${#FAILED_PLUGINS[@]} -gt 0 ]]; then
      echo_yellow " ${#FAILED_PLUGINS[@]} Claude Code plugin(s) failed to install:"
      for plugin in "${FAILED_PLUGINS[@]}"; do
        echo_red "   - ${plugin}"
      done
    fi
  fi

  if [[ "${skip_codex}" != true ]]; then
    if [[ ${#FAILED_CODEX_PLUGINS[@]} -eq 0 && ${total_codex_plugins} -gt 0 ]]; then
      echo_green " All ${total_codex_plugins} Codex plugin(s) installed successfully!"
    elif [[ ${#FAILED_CODEX_PLUGINS[@]} -gt 0 ]]; then
      echo_yellow " ${#FAILED_CODEX_PLUGINS[@]} Codex plugin(s) failed to install:"
      for plugin in "${FAILED_CODEX_PLUGINS[@]}"; do
        echo_red "   - ${plugin}"
      done
    fi
  fi

  if [[ "${install_repo_tools}" == true ]]; then
    echo_blue " --- Repo Tools ---"

    if [[ ${repo_total_pips} -gt 0 ]]; then
      if [[ ${#FAILED_REPO_TOOL_PIPS[@]} -eq 0 ]]; then
        echo_green " All ${repo_total_pips} repo-tool pip package(s) installed successfully!"
      else
        echo_yellow " ${#FAILED_REPO_TOOL_PIPS[@]} repo-tool pip step(s) failed:"
        for pkg in "${FAILED_REPO_TOOL_PIPS[@]}"; do
          echo_red "   - ${pkg}"
        done
      fi
    fi

    if [[ ${repo_total_npms} -gt 0 ]]; then
      if [[ ${#FAILED_REPO_TOOL_NPMS[@]} -eq 0 ]]; then
        echo_green " All ${repo_total_npms} repo-tool npm package(s) installed successfully!"
      else
        echo_yellow " ${#FAILED_REPO_TOOL_NPMS[@]} repo-tool npm package(s) failed:"
        for pkg in "${FAILED_REPO_TOOL_NPMS[@]}"; do
          echo_red "   - ${pkg}"
        done
      fi
    fi

    if [[ ${repo_total_mcps} -gt 0 ]]; then
      if [[ ${#FAILED_GEMINI_MCPS[@]} -eq 0 && "${skip_gemini}" != true ]]; then
        echo_green " All ${repo_total_mcps} Gemini MCP server(s) installed successfully!"
      elif [[ ${#FAILED_GEMINI_MCPS[@]} -gt 0 ]]; then
        echo_yellow " ${#FAILED_GEMINI_MCPS[@]} Gemini MCP server(s) failed to install:"
        for mcp in "${FAILED_GEMINI_MCPS[@]}"; do
          echo_red "   - ${mcp}"
        done
      fi

      if [[ ${#FAILED_ANTIGRAVITY_MCPS[@]} -eq 0 && "${skip_antigravity}" != true ]]; then
        echo_green " All ${repo_total_mcps} Antigravity MCP server(s) installed successfully!"
      elif [[ ${#FAILED_ANTIGRAVITY_MCPS[@]} -gt 0 ]]; then
        echo_yellow " ${#FAILED_ANTIGRAVITY_MCPS[@]} Antigravity MCP server(s) failed to install:"
        for mcp in "${FAILED_ANTIGRAVITY_MCPS[@]}"; do
          echo_red "   - ${mcp}"
        done
      fi
    fi
  fi

  echo_blue "=========================================="
  echo
  echo_green "Installed skills can be listed with: npx skills list --global"

  # Exit with failure if any skills, MCPs, npm/pip packages, or plugins failed
  if [[ ${#FAILED_SKILLS[@]} -gt 0 || ${#FAILED_MCPS[@]} -gt 0 || ${#FAILED_CODEX_MCPS[@]} -gt 0 || ${#FAILED_NPMS[@]} -gt 0 || ${#FAILED_AGENTS_COPY_SKILLS[@]} -gt 0 || ${#FAILED_PIPS[@]} -gt 0 || ${#FAILED_COPY_SKILLS[@]} -gt 0 || ${#FAILED_COPY_SKILLS_ALWAYS[@]} -gt 0 || ${#FAILED_MATH_COPY_SKILLS[@]} -gt 0 || ${#FAILED_CLAUDE_COPY_SKILLS[@]} -gt 0 || ${#FAILED_CLAUDE_HOOKS[@]} -gt 0 || ${#FAILED_ANTIGRAVITY_COPY_SKILLS[@]} -gt 0 || ${#FAILED_PLUGINS[@]} -gt 0 || ${#FAILED_CODEX_PLUGINS[@]} -gt 0 || ${#FAILED_REPO_TOOL_PIPS[@]} -gt 0 || ${#FAILED_REPO_TOOL_NPMS[@]} -gt 0 || ${#FAILED_GEMINI_MCPS[@]} -gt 0 || ${#FAILED_ANTIGRAVITY_MCPS[@]} -gt 0 ]]; then
    exit 1
  fi

  exit 0
}

# Main function
main "${@}"
