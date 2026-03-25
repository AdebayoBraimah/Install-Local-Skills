#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Installs agent skills via npx skills add (https://skills.sh/).
#
# Target agents: claude-code, antigravity
# NOTE: codex and gemini are universal and already handled.

# TODO:
# Add these to the install list for plug-ins:
# https://github.com/ooiyeefei/ccc/tree/main/skills/excalidraw
# npm install -g @mermaid-js/mermaid-cli # need this for mermaid-diagram skill

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

  # --- Productivity ---
  "ctsstc/get-shit-done-skills"                                                 "gsd"

  # --- Documentation ---
  "intellectronica/agent-skills"                                                "context7"

  # --- Writing ---
  "davila7/claude-code-templates"                                               "humanizer"

  # --- Reasoning ---
  "mrgoonie/claudekit-skills"                                                   "sequential-thinking"
)


# =========================================================================
#
# MCP servers registry
#
#   Each entry is a triplet: <name> <scope> <command...>
#   The command portion may contain multiple tokens.
#
# =========================================================================

MCP_SERVERS=(
  # --- Reasoning ---
  "sequential-thinking"  "user"  "npx -y @modelcontextprotocol/server-sequential-thinking"
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

      Also installs required MCP servers via the claude CLI
      when available.

      NOTE:
      - codex and gemini are universal and already handled.
      - If installing skills for the first time, use
        the interactive install process with:

        npx skills add https://github.com/vercel-labs/skills --skill find-skills

  Optional arguments:
      -h, -help, --help               Prints this help menu, then exits.

  Example usage:

      # Install all skills
      $(basename ${0})

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

  while [[ ${#} -gt 0 ]]; do
    case "${1}" in
      -h|-help|--help) Usage; ;;
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
    echo_yellow "claude CLI not found — skipping MCP server installation."
    local skip_mcp=true
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
  # Install MCP servers
  #============================

  FAILED_MCPS=()

  local total_mcps=$(( ${#MCP_SERVERS[@]} / 3 ))

  if [[ "${skip_mcp}" != true && ${total_mcps} -gt 0 ]]; then
    echo
    echo_blue "=========================================="
    echo_blue " Installing ${total_mcps} MCP Server(s)"
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

  if [[ "${skip_mcp}" != true ]]; then
    if [[ ${#FAILED_MCPS[@]} -eq 0 ]]; then
      echo_green " All ${total_mcps} MCP server(s) installed successfully!"
    else
      echo_yellow " ${#FAILED_MCPS[@]} MCP server(s) failed to install:"
      for mcp in "${FAILED_MCPS[@]}"; do
        echo_red "   - ${mcp}"
      done
    fi
  fi

  echo_blue "=========================================="
  echo
  echo_green "Installed skills can be listed with: npx skills list --global"

  # Exit with failure if any skills or MCPs failed
  if [[ ${#FAILED_SKILLS[@]} -gt 0 || ${#FAILED_MCPS[@]} -gt 0 ]]; then
    exit 1
  fi

  exit 0
}

# Main function
main "${@}"
