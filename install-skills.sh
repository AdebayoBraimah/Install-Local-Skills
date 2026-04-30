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
  "https://github.com/AdebayoBraimah/claude-deep-research-skill.git"           "deep-research-academic"
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

  # --- Project management ---
  "https://github.com/ctsstc/get-shit-done-skills.git"                          "gsd"
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
#     - ~/.gemini/antigravity/skills/<skill-name>
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
#   ~/.agents/skills/<skill-name>/ and sym-linked to:
#     - ~/.claude/skills/<skill-name>
#     - ~/.gemini/antigravity/skills/<skill-name>
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
#     - ~/.gemini/antigravity/skills/<skill-name>
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

      Phase 1 requires npx. Phases 2 and 8 require the
      claude CLI. Phases 3 and 9 require the codex CLI.
      Local pip packages require pip. Missing CLIs cause
      the corresponding phases to be skipped.

      Math skills require Lean 4 and Lake on PATH (and
      Mathlib for the AI/ML variant) for Lean verification.
      The script does not auto-install them — install elan
      from https://leanprover.github.io/ first.

      NOTE:
      - codex and gemini are universal and already handled.
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

  Example usage:

      # Install all skills
      $(basename ${0})

      # Install all skills including local-only skills
      $(basename ${0}) --local

      # Install all skills including math skills
      $(basename ${0}) --math

      # Install everything (local + math)
      $(basename ${0}) --local --math

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
#   symlinks in ~/.claude/skills/ and
#   ~/.gemini/antigravity/skills/.
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
  local gemini_dir="${HOME}/.gemini/antigravity/skills"
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

  echo_green "  -> Copied to ${target_dir}"

  # Create symlink in ~/.claude/skills/
  mkdir -p "${claude_dir}"

  if [[ -e "${claude_dir}/${skill_name}" || -L "${claude_dir}/${skill_name}" ]]; then
    rm -rf "${claude_dir}/${skill_name}"
  fi

  ln -s "../../.agents/skills/${skill_name}" "${claude_dir}/${skill_name}"
  echo_green "  -> Symlinked: ${claude_dir}/${skill_name}"

  # Create symlink in ~/.gemini/antigravity/skills/
  mkdir -p "${gemini_dir}"

  if [[ -e "${gemini_dir}/${skill_name}" || -L "${gemini_dir}/${skill_name}" ]]; then
    rm -rf "${gemini_dir}/${skill_name}"
  fi

  ln -s "../../../.agents/skills/${skill_name}" "${gemini_dir}/${skill_name}"
  echo_green "  -> Symlinked: ${gemini_dir}/${skill_name}"

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

  echo_green "  -> Copied to ${target_dir}"
  echo_green "  -> ${skill_name} installed successfully"
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

  while [[ ${#} -gt 0 ]]; do
    case "${1}" in
      -h|-help|--help) Usage; ;;
      --local) install_local=true ;;
      --math)  install_math=true ;;
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

  if [[ "${install_local}" == true ]]; then
    if ! command -v pip &>/dev/null; then
      echo_yellow "pip not found — skipping local pip package installation."
      local skip_pip=true
    fi

    # Merge local skills into main skills array
    SKILLS+=("${LOCAL_SKILLS[@]}")
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

  if [[ "${skip_claude}" != true && ${total_mcps} -gt 0 ]]; then
    if [[ ${#FAILED_MCPS[@]} -eq 0 ]]; then
      echo_green " All ${total_mcps} Claude MCP server(s) installed successfully!"
    else
      echo_yellow " ${#FAILED_MCPS[@]} Claude MCP server(s) failed to install:"
      for mcp in "${FAILED_MCPS[@]}"; do
        echo_red "   - ${mcp}"
      done
    fi
  fi

  if [[ "${skip_codex}" != true && ${total_mcps} -gt 0 ]]; then
    if [[ ${#FAILED_CODEX_MCPS[@]} -eq 0 ]]; then
      echo_green " All ${total_mcps} Codex MCP server(s) installed successfully!"
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

  echo_blue "=========================================="
  echo
  echo_green "Installed skills can be listed with: npx skills list --global"

  # Exit with failure if any skills, MCPs, npm/pip packages, or plugins failed
  if [[ ${#FAILED_SKILLS[@]} -gt 0 || ${#FAILED_MCPS[@]} -gt 0 || ${#FAILED_CODEX_MCPS[@]} -gt 0 || ${#FAILED_NPMS[@]} -gt 0 || ${#FAILED_AGENTS_COPY_SKILLS[@]} -gt 0 || ${#FAILED_PIPS[@]} -gt 0 || ${#FAILED_COPY_SKILLS[@]} -gt 0 || ${#FAILED_COPY_SKILLS_ALWAYS[@]} -gt 0 || ${#FAILED_MATH_COPY_SKILLS[@]} -gt 0 || ${#FAILED_CLAUDE_COPY_SKILLS[@]} -gt 0 || ${#FAILED_PLUGINS[@]} -gt 0 || ${#FAILED_CODEX_PLUGINS[@]} -gt 0 ]]; then
    exit 1
  fi

  exit 0
}

# Main function
main "${@}"
