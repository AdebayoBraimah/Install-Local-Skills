---
name: ai-anti-pattern-review
description: Reviews prose, drafts, generated text, and text-like files for AI-ish writing anti-patterns using an updateable JSON pattern database. Use when the user asks to review writing for AI tells, AI-isms, anti-patterns, generic generated prose, over-polished style, or wants a file checked for these issues.
---

# AI Anti-Pattern Review

Use this skill to flag writing patterns commonly associated with AI-generated prose. The reference patterns live in `references/ai_antipatterns.json` so they can be updated without rewriting the skill.

## Workflow

1. Get the input as pasted text or a file path.
2. Run the scanner first:
   - Pasted text:
     ```bash
     python ~/.agents/skills/ai-anti-pattern-review/scripts/review_ai_antipatterns.py --text "The text to review" --format json
     ```
   - File path:
     ```bash
     python ~/.agents/skills/ai-anti-pattern-review/scripts/review_ai_antipatterns.py --file path/to/file.md --format json
     ```
3. Read `findings` for deterministic matches and `manual_review_patterns` for subtle patterns that require judgment.
4. Manually inspect the input for each returned manual-review pattern. Only report a manual pattern as an applied finding when there is concrete evidence.
5. Return a findings-only report unless the user explicitly asks for a rewrite.

## Report Format

Return this structure:

```markdown
Verdict: [No major issues | Minor AI-pattern signals | Likely AI-patterned prose]

Findings
- [Severity N] pattern_id: short description
  Evidence: "short quote" (line X, column Y when available)
  Why it was flagged: concise rationale
  Suggested fix: concrete revision guidance

Manual review notes
- pattern_id: applied/not applied, with evidence when applied
```

Sort applied findings by severity descending, then confidence. If there are no deterministic findings and no manual-only patterns apply, say so plainly.

## Scanner Notes

- Supported file inputs are UTF-8 text-like files only.
- `agent_judgment` detectors are not automatic findings. They are prompts for your review.
- Use `--min-severity 4` when the user wants only high-severity issues.
- Use `--patterns-json path/to/updated.json` to test or use an alternate pattern database.

