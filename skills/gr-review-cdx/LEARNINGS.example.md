# LEARNINGS — Team Review Rules

This is the plain-English standards file the `gr-review-cdx` skill enforces. It is
the local analogue of Gr's "learnings" / custom rules.

**To use it for a real repo:** copy this file to the root of that repo as
`LEARNINGS.md` (or `.gr/LEARNINGS.md`) and edit the rules to match what your
team actually cares about. When a repo has no such file, the skill falls back to this
bundled example and applies only the rules that clearly fit.

Write each rule as one imperative sentence a reviewer can check against a diff. Group
them however you like. Delete the examples below — they are illustrative, not
prescriptive.

## How the skill reads this file
- Every rule becomes a check for the **conventions reviewer**.
- A violated rule is reported at MEDIUM or higher, quoting the rule.
- Security- and correctness-flavored rules are also honored by those reviewers.

## Example rules (replace these)

### Correctness & safety
- Every public function that can fail must return or raise an explicit error; never
  swallow exceptions silently.
- Do not introduce a new external dependency when the standard library or an existing
  in-repo helper already does the job.
- Any change to a function signature must update every call site in the same change.

### Security
- Never build a SQL query or shell command by string-concatenating user input; use
  parameterized queries / argument arrays.
- No secrets, tokens, or credentials in source, logs, or error messages.
- Every new HTTP route that reads or writes user-owned data must perform an ownership
  check.

### Style & consistency
- Match the error-handling and logging style of the surrounding module.
- New public APIs get a docstring/comment consistent with their siblings.
- Prefer reusing an existing helper over adding a near-duplicate one.

### Testing
- A bug fix should come with a regression test that fails without the fix.
- New behavior in a module that already has tests should be tested in the same style.

## Future: auto-mined learnings
In the full Gr design, rules are also learned automatically from past review
comments (the `gr-learnings` skill). This MVP reads only the rules you write
here.
