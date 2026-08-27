# alert-me — Claude Code hook (CLAUDE CODE SPECIFIC)

> **This component is specific to Claude Code and does not apply to any other
> agent.** The skill itself (`SKILL.md`) is agent-agnostic — any agent that can
> run a shell command can use it. Everything described in *this* file depends
> on Claude Code's hook system and its `~/.claude/settings.json` schema. Codex,
> Anti-Gravity, and Gemini do not read these files and are unaffected by them.
> Do not port this to another agent by copying it; each has its own lifecycle
> mechanism, or none at all.

## Why this exists

`alert-me` is a passive skill: the model itself decides to send the
notification. That covers a finish, a surfaced error, or a pause for input —
but it cannot cover a stop the model never observes. A crash, an abort, a
cancel, or the process being killed all end the turn with no model left running
to invoke anything.

Claude Code's hook system runs commands in the harness, independent of the
model, so it still fires in those cases. That is the gap this hook fills, and
it is the reason the "Limitation" section of `SKILL.md` points here.

## What gets installed

| Path | What it is |
|---|---|
| `~/.claude/hooks/alert-me/turn-timer.sh` | The hook script (copied from `hooks/turn-timer.sh` in this skill) |
| `~/.claude/settings.json` → `hooks.UserPromptSubmit` | Stamps the turn start time, keyed by session id |
| `~/.claude/settings.json` → `hooks.Stop` | On stop, notifies only if the turn ran past the threshold |
| `~/.claude/hooks/alert-me/state/` | Per-session timestamp files, auto-pruned after 1 day |

The two settings entries are declared in `hooks/claude-hooks.json`. The token
`__HOOK_DIR__` in that file is replaced with the real install directory at
install time.

## Why it is a pair of hooks, not just `Stop`

A bare `Stop` hook fires every time Claude finishes responding — that is a push
notification after *every single turn*, including one-line answers. Useless in
practice.

To notify only on the long, unattended runs you actually walk away from, the
hook needs to know how long the turn took. `UserPromptSubmit` records the start
time; `Stop` reads it, computes the elapsed time, and stays silent below the
threshold. The `Stop` half is `async: true`, so it never delays your next
prompt.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `ALERT_ME_MIN_SECONDS` | `120` | Minimum turn duration before a notification is sent |

The topic (`ab-mac`) is set in `turn-timer.sh`. Notification title is
`Claude Code — <project-dir-name>`.

Sending goes through the installed `ntfy-notify` skill at
`~/.agents/skills/ntfy-notify/scripts/ntfy_send.sh`, falling back to a raw
`curl` to `https://ntfy.sh/<topic>` if that script is missing or fails.

## Installation

Handled by `install-skills.sh` via the `CLAUDE_HOOKS` registry array. It is
idempotent: re-running refreshes the script but will not add duplicate entries
to `settings.json`. Requires `jq`; the phase is skipped with a warning if `jq`
is absent, and skipped entirely if Claude Code is not installed.

Existing hooks in `settings.json` are preserved — the merge only appends the
`alert-me` entries, and a timestamped backup is written before any change.

## Removing it

```bash
jq 'del(.hooks.Stop, .hooks.UserPromptSubmit)' ~/.claude/settings.json > /tmp/s.json \
  && mv /tmp/s.json ~/.claude/settings.json
rm -rf ~/.claude/hooks/alert-me
```

Delete only the `alert-me` entries if you have other hooks on those two events —
the command above removes both events wholesale.

## Caveats

- Claude Code reloads hook config when `settings.json` changes, but a session
  already running may need `/hooks` opened once, or a restart, before the new
  hook fires.
- On a long turn where the model *also* invokes the `alert-me` skill, you get
  two notifications: the skill's "Finished" and the hook's "Stopped after …".
  They are deliberately separate mechanisms; only the hook survives a crash.
- The hook always exits 0. A notification failure can never block a turn.
