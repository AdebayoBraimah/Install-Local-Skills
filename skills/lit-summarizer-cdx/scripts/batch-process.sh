#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Detects new Obsidian files and Zotero references, then invokes
#   Codex to process them via the lit-summarizer-cdx skill.


# Globals
VAULT_PATH="${OBSIDIAN_VAULT:-$HOME/Obsidian/Academics}"
CLI_ZOTERO="$HOME/anaconda3/bin/cli-anything-zotero"
PROGRESS_FILE="${VAULT_PATH}/Ideas/Research/_batch-progress.md"
CODEX_BIN="${CODEX_BIN:-codex}"
NTFY_SCRIPT="${HOME}/.agents/skills/ntfy-notify/scripts/ntfy_send.sh"
NTFY_TOPIC="ab-mac"
LOG_FILE=""
ERR_FILE=""
LAST_MESSAGE_FILE=""


#######################################
# Prints usage to the command line interface.
# Arguments:
#   None
#######################################
Usage(){
  cat << USAGE

  Usage:

      $(basename ${0}) [options]
      $(basename ${0}) --collection <name>
      $(basename ${0}) --zotero-only
      $(basename ${0}) --new-files-only

  Detects new Zotero references and/or new Obsidian files, then
  invokes Codex (headless) to batch-summarize them into
  structured Obsidian literature notes via the lit-summarizer-cdx
  skill.

  Optional arguments
    --collection <name>             Process a specific Zotero collection by name
    --zotero-only                   Only process new Zotero references (no Obsidian files)
    --new-files-only                Only process new/modified Obsidian files (no Zotero)
    --dry-run                       Show what would be processed without invoking Codex
    --no-notify                     Suppress push notifications via ntfy
    -h, -help, --help               Prints the help menu, then exits.

  Requirements
    - codex CLI on PATH, or set CODEX_BIN=/path/to/codex
    - cli-anything-zotero at ${CLI_ZOTERO}
    - Codex login/configuration already set up for non-interactive execution

  Examples
    # Auto-detect and process all new items
    $(basename ${0})

    # Process a single Zotero collection
    $(basename ${0}) --collection "LLM pruning"

    # Preview without making changes
    $(basename ${0}) --dry-run

    # Run via cron (nightly at 2 AM)
    # 0 2 * * * /path/to/batch-process.sh >> /tmp/batch-process.log 2>&1

USAGE
  exit 1
}


#######################################
# Prints message to the command line interface
#   in some arbitrary color.
# Arguments:
#   msg
#######################################
echo_color(){
  msg='\033[0;'"${@}"'\033[0m'
  echo -e ${msg}
}


#######################################
# Prints message to the command line interface
#   in red.
# Arguments:
#   msg
#######################################
echo_red(){
  echo_color '31m'"${@}"
}


#######################################
# Prints message to the command line interface
#   in green.
# Arguments:
#   msg
#######################################
echo_green(){
  echo_color '32m'"${@}"
}


#######################################
# Prints message to the command line interface
#   in blue.
# Arguments:
#   msg
#######################################
echo_blue(){
  echo_color '36m'"${@}"
}


#######################################
# Prints message to the command line interface
#   in red when an error is intended to be raised.
# Arguments:
#   msg
#######################################
exit_error(){
  echo_red "${@}"
  exit 1
}


#######################################
# Logs a timestamped message to stdout and log file.
# Globals:
#   LOG_FILE
# Arguments:
#   Message string
#######################################
log(){
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] ${@}"
  echo "${msg}"
  if [[ -n "${LOG_FILE}" ]] && [[ -f "${LOG_FILE}" ]]; then
    echo "${msg}" >> "${LOG_FILE}"
  fi
}


#######################################
# Logs the command to file, and executes (runs) the command.
# Globals:
#   LOG_FILE
#   ERR_FILE
# Arguments:
#   Command to be logged and performed.
#######################################
run(){
  echo "${@}"
  "${@}" >>"${LOG_FILE}" 2>>"${ERR_FILE}"
  if [[ ! ${?} -eq 0 ]]; then
    echo "failed: see log files ${LOG_FILE} ${ERR_FILE} for details"
    exit 1
  fi
  echo "-----------------------"
}


#######################################
# Counts non-empty lines from stdin.
# Arguments:
#   None
# Outputs:
#   Integer count
#######################################
count_nonempty_lines(){
  sed '/^[[:space:]]*$/d' | wc -l | tr -d ' '
}


#######################################
# Sends a push notification via ntfy.
# Globals:
#   NTFY_SCRIPT
#   NTFY_TOPIC
#   NO_NOTIFY
# Arguments:
#   Message string
#######################################
notify(){
  if [[ "${NO_NOTIFY}" == "true" ]]; then
    return 0
  fi
  if [[ -x "${NTFY_SCRIPT}" ]]; then
    "${NTFY_SCRIPT}" --topic "${NTFY_TOPIC}" --title "Batch Process" --priority 3 "${1}" 2>/dev/null || true
  fi
}


#######################################
# Extracts already-processed Zotero keys from the
#   progress tracker Item Log table.
# Globals:
#   PROGRESS_FILE
# Arguments:
#   None
# Outputs:
#   Sorted unique list of 8-character Zotero keys
#######################################
get_processed_keys(){
  if [[ -f "${PROGRESS_FILE}" ]]; then
    sed -En 's/^\| ([A-Z0-9]{8})([[:space:]]*\|.*)?$/\1/p' "${PROGRESS_FILE}" | sort -u
  fi
}


#######################################
# Retrieves all Zotero item keys across all collections
#   via the cli-anything-zotero tool.
# Globals:
#   CLI_ZOTERO
# Arguments:
#   None
# Outputs:
#   Sorted unique list of 8-character Zotero keys
#######################################
get_all_zotero_keys(){
  local limit=500
  local offset=0
  local max_pages=100
  local page_num=0
  local page
  local keys
  local count

  while [[ ${page_num} -lt ${max_pages} ]]; do
    page=$("${CLI_ZOTERO}" items -n "${limit}" --offset "${offset}" 2>/dev/null || true)
    keys=$(printf '%s\n' "${page}" | sed -En 's/^[[:space:]]*\[([A-Z0-9]{8})\].*$/\1/p')
    count=$(printf '%s\n' "${keys}" | count_nonempty_lines)

    if [[ "${count}" -eq 0 ]]; then
      break
    fi

    printf '%s\n' "${keys}"
    offset=$((offset + limit))
    page_num=$((page_num + 1))
  done | sort -u
}


#######################################
# Finds new (untracked or modified) Obsidian markdown
#   files in the Ideas/Research/ directory.
# Globals:
#   VAULT_PATH
# Arguments:
#   None
# Outputs:
#   List of file paths (one per line)
#######################################
get_new_obsidian_files(){
  cd "${VAULT_PATH}"
  # Untracked .md files in Ideas/Research/
  git ls-files --others --exclude-standard 'Ideas/Research/*.md' 2>/dev/null || true
  # Modified files that might need updating
  git diff --name-only 'Ideas/Research/*.md' 2>/dev/null || true
}


#######################################
# Detects new Zotero references not yet in the progress
#   tracker by comparing all Zotero keys against processed keys.
# Globals:
#   None (calls get_processed_keys, get_all_zotero_keys)
# Arguments:
#   None
# Outputs:
#   Integer count of new items (to stdout)
#######################################
detect_new_zotero_items(){
  log "Checking for new Zotero references..." >&2

  local processed_keys
  processed_keys=$(get_processed_keys)
  local processed_count
  processed_count=$(printf '%s\n' "${processed_keys}" | count_nonempty_lines)

  local all_keys
  all_keys=$(get_all_zotero_keys)
  local total_count
  total_count=$(printf '%s\n' "${all_keys}" | count_nonempty_lines)

  # Find keys in Zotero but not in progress tracker
  local new_keys
  new_keys=$(comm -23 <(echo "${all_keys}") <(echo "${processed_keys}") 2>/dev/null || true)
  local new_count
  new_count=$(printf '%s\n' "${new_keys}" | count_nonempty_lines)

  log "  Zotero items: ${total_count} total, ${processed_count} processed, ${new_count} new" >&2
  echo "${new_count}"
}


#######################################
# Detects new or modified Obsidian files in the vault.
# Globals:
#   None (calls get_new_obsidian_files)
# Arguments:
#   None
# Outputs:
#   Integer count of new files (to stdout)
#######################################
detect_new_obsidian_files(){
  log "Checking for new Obsidian files..." >&2

  local new_files
  new_files=$(get_new_obsidian_files)
  local new_count
  new_count=$(printf '%s\n' "${new_files}" | count_nonempty_lines)

  log "  New/modified Obsidian files: ${new_count}" >&2
  if [[ ${new_count} -gt 0 ]]; then
    echo "${new_files}" | head -10 >&2
    [[ ${new_count} -gt 10 ]] && log "  ... and $((new_count - 10)) more" >&2
  fi
  echo "${new_count}"
}


#######################################
# Constructs the Codex prompt based on the
#   selected processing mode and detected items.
# Globals:
#   MODE
#   COLLECTION_NAME
# Arguments:
#   None
# Outputs:
#   Prompt string (to stdout)
#######################################
build_prompt(){
  local prompt=""

  case ${MODE} in
    collection)
      prompt="Use the lit-summarizer-cdx skill to process the Zotero collection '${COLLECTION_NAME}'. Extract all items, summarize papers into Obsidian literature notes, create hub notes for concept clusters, cross-reference, and make local commits if the skill workflow calls for them. Never push to a remote repository. Spawn Codex subagents by default for parallelizable extractor, summarizer, and linker work unless a newer user instruction explicitly says not to use subagents."
      ;;

    new-files)
      local files
      files=$(get_new_obsidian_files)
      if [[ -z "${files}" ]]; then
        log "No new Obsidian files found. Nothing to do." >&2
        return 1
      fi
      prompt="Use the lit-summarizer-cdx conventions to process new Obsidian files in the vault. Check these files in Ideas/Research/ and ensure they have proper frontmatter, Zotero-Key fields, and are cross-referenced with related notes. Make local commits if the workflow calls for them, but never push to a remote repository. Spawn Codex subagents by default for parallelizable processing unless a newer user instruction explicitly says not to use subagents. Files to check: ${files}"
      ;;

    zotero)
      prompt="Use the lit-summarizer-cdx skill to check for unprocessed Zotero references not yet in Ideas/Research/_batch-progress.md. Process all new items: extract metadata, summarize papers, create literature notes, link, and make local commits if the workflow calls for them. Never push to a remote repository. Spawn Codex subagents by default for parallelizable extractor, summarizer, and linker work unless a newer user instruction explicitly says not to use subagents."
      ;;

    auto)
      local new_zotero
      new_zotero=$(detect_new_zotero_items)
      local new_files
      new_files=$(detect_new_obsidian_files)

      if [[ "${new_zotero}" -eq 0 ]] && [[ "${new_files}" -eq 0 ]]; then
        log "No new items detected. Nothing to do." >&2
        return 1
      fi

      prompt="Batch process new items in the Obsidian vault:"
      if [[ "${new_zotero}" -gt 0 ]]; then
        prompt+=" There are approximately ${new_zotero} new Zotero references not yet processed. Use the lit-summarizer-cdx workflow to process all unprocessed collections."
      fi
      if [[ "${new_files}" -gt 0 ]]; then
        prompt+=" There are ${new_files} new or modified Obsidian files in Ideas/Research/ that may need frontmatter normalization and cross-referencing."
      fi
      prompt+=" Make local commits if the workflow calls for them, but never push to a remote repository. Spawn Codex subagents by default for parallelizable extractor, summarizer, and linker work unless a newer user instruction explicitly says not to use subagents."
      ;;
  esac

  echo "${prompt}"
}


#######################################
# Main function that parses arguments and orchestrates
#   the batch processing pipeline:
#     * Detect new Zotero references and/or Obsidian files
#     * Build an appropriate Codex prompt
#     * Invoke Codex in headless mode
#     * Report results and send notifications
# Arguments:
#   --collection <name>: Process a specific Zotero collection
#   --zotero-only: Only process new Zotero references
#   --new-files-only: Only process new Obsidian files
#   --dry-run: Preview without executing
#   --no-notify: Suppress ntfy notifications
# Outputs:
#   Processing results to stdout and log file
#######################################
main(){

  #
  # Parse arguments
  #============================

  if [[ ${#} -gt 0 ]] && [[ "${1}" == "-h" || "${1}" == "-help" || "${1}" == "--help" ]]; then
    Usage
  fi

  # Set defaults
  local mode="auto"
  local collection_name=""
  local dry_run="false"
  NO_NOTIFY="false"

  while [[ ${#} -gt 0 ]]; do
    case "${1}" in
      --collection) shift; collection_name="${1}"; mode="collection" ;;
      --zotero-only) mode="zotero" ;;
      --new-files-only) mode="new-files" ;;
      --dry-run) dry_run="true" ;;
      --no-notify) NO_NOTIFY="true" ;;
      -h|-help|--help) Usage ;;
      -*) echo_red "$(basename ${0}): Unrecognized option ${1}" >&2; Usage ;;
      *) break ;;
    esac
    shift
  done

  # Export to globals for helper functions
  MODE="${mode}"
  COLLECTION_NAME="${collection_name}"

  #
  # Dependency checks
  #============================

  if ! command -v "${CODEX_BIN}" >/dev/null 2>&1; then
    exit_error "Codex CLI (${CODEX_BIN}) is not installed or not on PATH. Exiting..."
  fi

  if [[ ! -x "${CLI_ZOTERO}" ]]; then
    exit_error "cli-anything-zotero not found at ${CLI_ZOTERO}. Exiting..."
  fi

  if [[ ! -d "${VAULT_PATH}" ]]; then
    exit_error "Vault directory does not exist: ${VAULT_PATH}. Exiting..."
  fi

  #
  # Check arguments
  #============================

  if [[ "${mode}" == "collection" ]] && [[ -z "${collection_name}" ]]; then
    exit_error "Collection name must be specified with --collection."
  fi

  #
  # Define log files
  #============================

  local outdir="${VAULT_PATH}"
  LAST_MESSAGE_FILE="${outdir}/batch-process.last-message.txt"

  if [[ "${dry_run}" == "true" ]]; then
    # Dry-run must not create or truncate vault files.
    LOG_FILE=""
    ERR_FILE=""
  else
    LOG_FILE="${outdir}/batch-process.log"
    ERR_FILE="${outdir}/batch-process.err"
    : > "${LOG_FILE}"
    : > "${ERR_FILE}"
    : > "${LAST_MESSAGE_FILE}"
  fi

  #
  # Build prompt
  #============================

  log "=== Zotero Batch Process ==="
  log "Mode: ${mode}"
  log "Vault: ${VAULT_PATH}"

  local prompt
  if ! prompt=$(build_prompt); then
    log "No prompt generated. Exiting."
    exit 0
  fi

  if [[ -z "${prompt}" ]]; then
    log "No prompt generated. Exiting."
    exit 0
  fi

  log "Prompt: ${prompt:0:120}..."

  #
  # Dry run check
  #============================

  if [[ "${dry_run}" == "true" ]]; then
    echo_blue "[DRY RUN] Would invoke Codex with:"
    echo "  ${CODEX_BIN} exec --cd \"${VAULT_PATH}\" --sandbox danger-full-access --output-last-message \"${LAST_MESSAGE_FILE}\" \"${prompt}\""
    echo_blue "[DRY RUN] No changes made."
    exit 0
  fi

  #
  # Invoke Codex
  #============================

  notify "Starting batch process (mode: ${mode})"
  log "Invoking Codex (headless exec)..."

  local result
  local exit_code=0

  result=$("${CODEX_BIN}" exec \
    --cd "${VAULT_PATH}" \
    --sandbox danger-full-access \
    --output-last-message "${LAST_MESSAGE_FILE}" \
    "${prompt}" 2>>"${ERR_FILE}") || exit_code=$?

  if [[ ${exit_code} -ne 0 ]]; then
    echo_red "ERROR: Codex exited with code ${exit_code}"
    log "ERROR: Codex exited with code ${exit_code}"
    notify "Batch process FAILED (exit code ${exit_code})"
    echo "See ${ERR_FILE} for details."
    exit ${exit_code}
  fi

  #
  # Extract and report results
  #============================

  local summary
  if [[ -s "${LAST_MESSAGE_FILE}" ]]; then
    summary=$(tail -20 "${LAST_MESSAGE_FILE}")
  else
    summary=$(echo "${result}" | tail -20)
  fi

  log "=== Complete ==="
  log "Result: ${summary:0:200}"
  echo_green "Batch process completed successfully."

  notify "Batch process complete: ${summary:0:100}"

  # Successful exit status
  exit 0
}

# Main function
main "${@}"
