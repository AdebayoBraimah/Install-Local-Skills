---
name: alert-me
description: Send a push notification to ntfy topic ab-mac when a task finishes OR when the task stops for any reason (error, blocked, awaiting input). Triggers when the user says "alert me when finished", "notify me when done", "ping me if you stop", "let me know when this is done", or asks to be alerted on completion or interruption of a task.
---

# alert-me

Thin wrapper around the **ntfy-notify** skill. When a task reaches a terminal
state — it finished successfully, or it stopped for any reason (error, blocked,
waiting on the user) — send a push notification to the ntfy topic `ab-mac`.

This skill has no script of its own. It calls `ntfy-notify`'s sender directly.

## How to send the alert

Call the bundled `ntfy_send.sh` from the installed `ntfy-notify` skill, always
passing `--topic ab-mac` **explicitly** so it works even when
`~/.config/stu-skills/ntfy-notify/.env` (which would set `NTFY_DEFAULT_TOPIC`)
is absent — without the explicit topic, `ntfy_send.sh` exits with
"Missing prerequisite: set NTFY_DEFAULT_TOPIC (or pass --topic)."

The notification body is the final positional argument; `--title` is the task.

### On successful finish

```bash
~/.agents/skills/ntfy-notify/scripts/ntfy_send.sh \
  --topic ab-mac \
  --title "<short task name>" \
  "Finished: <one-line summary of what completed>"
```

### On stop for any (agent-observed) reason

```bash
~/.agents/skills/ntfy-notify/scripts/ntfy_send.sh \
  --topic ab-mac \
  --title "<short task name>" \
  "Stopped: <why it stopped — error, blocked, or needs your input>"
```

### Fallback (if ntfy_send.sh is unavailable)

```bash
curl -d "<message>" https://ntfy.sh/ab-mac
```

## Limitation — what this skill can and cannot catch

As a passive skill, alert-me fires **only** on the finish/stop cases the agent
itself reaches and acts on (task completed, hit an error it surfaces, or paused
to ask you something). It **cannot** fire on an *abnormal* stop the agent never
observes — a crash, an abort/cancel, or the process being killed — because the
model is no longer running to invoke it.

To alert on those abnormal-stop cases ("stop for **any** reason" in the literal
sense), add a **Stop hook** in `settings.json`: the harness runs the hook
itself, independent of the model. That is an optional follow-up and is out of
scope for this skill. Do not assume crash/abort coverage from alert-me alone.
