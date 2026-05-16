#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Installs agent skills via npx skills add (https://skills.sh/).
#
# Target agents: claude-code, antigravity
# NOTE: codex and gemini are universal and already handled.

# TODO:
#   - Add lit-<skills> from claude code [later; requires more work]
#   - Create/modify lit-skills for codex [later; requires more work]

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
  "${SCRIPT_DIR}/skills/plan-review-cdx"                                        "plan-review-cdx"
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
  "${SCRIPT_DIR}/skills/plan-review"                                            "plan-review"
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
#   Gemini CLI and Antigravity IDE discover skills from
#   ~/.agents/skills/ directly. Prior ~/.gemini/antigravity/skills/
#   symlinks (from earlier versions of this script) are cleaned up
#   on the next install when they point at the canonical target.
#
#   Always installed (no --local flag required).
#
# =========================================================================

COPY_SKILLS=(
  # --- Visualization ---
  "${SCRIPT_DIR}/skills/data-viz"                                               "data-viz"

  # --- Research engineering ---
  "${SCRIPT_DIR}/skills/research-engineer-ai-ml"                                "research-engineer-ai-ml"
)

# Patched fork of ctsstc/get-shit-done-skills vendored as a submodule
# (removes .env* glob + "Secrets location" template — secret-leak fix).
# If the submodule is uninitialized we skip installing the patched copy
# AND remove any pre-existing upstream-installed gsd so the user is not
# left running the unsafe upstream skill.
GSD_SUBMODULE="${SCRIPT_DIR}/submodules/get-shit-done-skills"
GSD_SOURCE="${GSD_SUBMODULE}/.kilocode/skills/gsd"
GSD_VULN_FILE="${GSD_SOURCE}/agents/codebase-mapper/SKILL.md"
if [[ -f "${GSD_VULN_FILE}" ]]; then
  COPY_SKILLS+=("${GSD_SOURCE}" "gsd")
else
  # NOTE: echo_yellow is defined later in the script, so this block uses
  # plain echo with inline ANSI yellow to stay independent of helper order.
  printf '\033[33m%s\033[0m\n' "Note: submodules/get-shit-done-skills is not initialized — skipping gsd."
  printf '\033[33m%s\033[0m\n' "  To enable, run: git submodule update --init --recursive"
  # Fail-closed: remove stale upstream-installed gsd to prevent the
  # vulnerable version from continuing to be active after the swap.
  for stale in "${HOME}/.agents/skills/gsd" \
               "${HOME}/.claude/skills/gsd" \
               "${HOME}/.gemini/antigravity/skills/gsd"; do
    if [[ -e "${stale}" || -L "${stale}" ]]; then
      printf '\033[33m%s\033[0m\n' "  Removing stale gsd install: ${stale}"
      rm -rf "${stale}"
    fi
  done
fi

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
  "mattpocock/skills"                                                           "caveman"
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
#   Gemini CLI and Antigravity IDE discover skills from
#   ~/.agents/skills/ directly. Prior ~/.gemini/antigravity/skills/
#   symlinks (from earlier versions of this script) are cleaned up
#   on the next install when they point at the canonical target.
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
# Math copy skills registry (installed with --math)
#
#   Each entry is a pair: <source-path> followed by <skill-name>.
#   These are local skill directories that are copied into
#   ~/.agents/skills/<skill-name>/ AND symlinked into:
#     - ~/.claude/skills/<skill-name>
#
#   Gemini CLI and Antigravity IDE discover skills from
#   ~/.agents/skills/ directly. Prior ~/.gemini/antigravity/skills/
#   symlinks (from earlier versions of this script) are cleaned up
#   on the next install when they point at the canonical target.
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
          triage, zoom-out, to-prd, to-issues, caveman,
          handoff, write-a-skill, and the
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
      Local pip packages require pip. Missing CLIs cause
      the corresponding phases to be skipped.

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
      - codex and gemini are universal for the base skill
        installation. With --repo-tools, the script also
        performs explicit Gemini MCP registration and global
        Graphify skill setup for Codex, Gemini, and Antigravity.
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
                                      (TDD, grill-me, to-issues, caveman,
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
  if "${python}" -m pip install --upgrade "${pkg}"; then
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
#   pkg: pip package name
# Globals:
#   FAILED_PIPS (appended on failure)
#######################################
install_pip_package(){
  local pkg="${1}"

  echo_blue "Installing pip package: ${pkg}"

  if pip install "${pkg}"; then
    echo_green "  -> ${pkg} installed successfully"

    # playwright requires a post-install step to download Chromium
    if [[ "${pkg}" == "playwright" ]]; then
      echo_blue "  -> Running playwright install chromium..."
      if playwright install chromium; then
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

  # One-time cleanup: remove any antigravity symlink left from prior installs
  # ONLY when it is a symlink pointing at the canonical target. Real files,
  # directories, or symlinks pointing elsewhere are left untouched.
  local stale_gemini="${HOME}/.gemini/antigravity/skills/${skill_name}"
  local expected_target="../../../.agents/skills/${skill_name}"
  if [[ -L "${stale_gemini}" && "$(readlink "${stale_gemini}")" == "${expected_target}" ]]; then
    rm -f "${stale_gemini}"
    echo_yellow "  -> Cleaned stale antigravity symlink: ${stale_gemini}"
  fi

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
    if ! command -v pip &>/dev/null; then
      echo_yellow "pip not found — skipping local pip package installation."
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

    for pkg in "${LOCAL_PIP_PACKAGES[@]}"; do
      install_pip_package "${pkg}"
    done
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
  if [[ ${#FAILED_SKILLS[@]} -gt 0 || ${#FAILED_MCPS[@]} -gt 0 || ${#FAILED_CODEX_MCPS[@]} -gt 0 || ${#FAILED_NPMS[@]} -gt 0 || ${#FAILED_AGENTS_COPY_SKILLS[@]} -gt 0 || ${#FAILED_PIPS[@]} -gt 0 || ${#FAILED_COPY_SKILLS[@]} -gt 0 || ${#FAILED_COPY_SKILLS_ALWAYS[@]} -gt 0 || ${#FAILED_MATH_COPY_SKILLS[@]} -gt 0 || ${#FAILED_CLAUDE_COPY_SKILLS[@]} -gt 0 || ${#FAILED_PLUGINS[@]} -gt 0 || ${#FAILED_CODEX_PLUGINS[@]} -gt 0 || ${#FAILED_REPO_TOOL_PIPS[@]} -gt 0 || ${#FAILED_REPO_TOOL_NPMS[@]} -gt 0 || ${#FAILED_GEMINI_MCPS[@]} -gt 0 || ${#FAILED_ANTIGRAVITY_MCPS[@]} -gt 0 ]]; then
    exit 1
  fi

  exit 0
}

# Main function
main "${@}"
