# Alert Policy

Use `alert-me` when the workflow finishes successfully or stops for an observed reason.

## Alert On

- successful finish
- blocker
- high-risk human decision needed
- validation cannot be resolved locally
- long-running milestone completed
- handoff written
- execution paused or transferred

## Alert Contents

Keep alerts concise:

- outcome
- status
- plan or handoff path if relevant
- next action if any

## Commands

Use the `alert-me` skill. Its documented sender is:

```bash
~/.agents/skills/ntfy-notify/scripts/ntfy_send.sh \
  --topic ab-mac \
  --title "<short task name>" \
  "Finished: <one-line summary>"
```

For stops:

```bash
~/.agents/skills/ntfy-notify/scripts/ntfy_send.sh \
  --topic ab-mac \
  --title "<short task name>" \
  "Stopped: <why it stopped>"
```

Fallback if unavailable:

```bash
curl -d "<message>" https://ntfy.sh/ab-mac
```

`alert-me` cannot catch abnormal stops that the agent never observes, such as crashes, aborts, or killed processes.
