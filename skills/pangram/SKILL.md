---
name: pangram
description: Check writing with Pangram AI detection while safely discovering PANGRAM_API_KEY. Use when writing, editing, revising, or auditing text with Pangram.
version: 1.0.0
---

# Pangram Writing Check

Use this skill to run writing through Pangram's V3 AI-detection REST API without exposing `PANGRAM_API_KEY`.

## Quick Start

```bash
python /Users/adebayobraimah/.agents/skills/pangram/scripts/pangram_check.py --text "Text to check"
python /Users/adebayobraimah/.agents/skills/pangram/scripts/pangram_check.py --file draft.md --json
cat draft.md | python /Users/adebayobraimah/.agents/skills/pangram/scripts/pangram_check.py
```

To verify whether a key is discoverable without running a check:

```bash
python /Users/adebayobraimah/.agents/skills/pangram/scripts/pangram_config.py --check
```

## Key Discovery

The helper looks for `PANGRAM_API_KEY` in this order:

1. Current process environment.
2. `.env` then `.envrc` in the current project directory.
3. Parent directories up through and including the first `.git` or `.hg` root.

It supports plain and exported dotenv lines, quoted values, whitespace, and comments. It never writes to `.env` or `.envrc`.

If no key is found, the check exits without contacting Pangram. It prompts only when `--prompt-key` is explicitly set, and the prompt uses `getpass` so the key is not echoed.

## CLI Behavior

- Use exactly one input source: `--text TEXT`, `--file PATH`, or piped stdin.
- `--text` and `--file` ignore stdin.
- Empty input exits before key discovery or API calls.
- `--public-dashboard-link` requests public Pangram dashboard links.
- `--json` prints parseable JSON without serializing secrets.
- Long text is chunked with exact reconstruction, weighted fraction aggregation, summed segment counts, and offset-adjusted top windows.

## Safety Rules

- Never print, log, serialize, or include the full API key in errors.
- Do not continue API-dependent work without a non-empty key.
- Send the key only as the `x-api-key` request header to `https://text.api.pangram.com/v3`.
