# Repo Tools Guide: Choosing Between Graphify and GitNexus

Both [Graphify](https://graphify.net/#features) and [GitNexus](https://github.com/abhigyanpatwari/GitNexus) ship behind the `--repo-tools` flag of `install-skills.sh`. They overlap, but they are optimized for different jobs. This guide explains which to reach for when a coding agent is operating on a repository — particularly a monorepo.

## TL;DR

- **For monorepos where coding agents will actively edit code: choose GitNexus as the primary context engine.**
- **For multimodal repo understanding (code + docs + papers + diagrams + experiment notes): use Graphify as a complementary layer.**

GitNexus is more directly optimized for "agent uses the repo graph while editing": CLI + MCP, Claude Code / Codex / Cursor / Windsurf / OpenCode integration, hooks, stale-index detection, multi-repo grouping, git-diff impact analysis, wiki generation, and local persistent indexing. Its README explicitly positions CLI + MCP as the recommended path for agentic editors; the web UI is for quick exploration.

Graphify is stronger when the "repo context" includes non-code artifacts: Markdown, PDFs, papers, diagrams, images, videos, SQL schemas, R scripts, shell scripts, architecture notes. It produces `graph.html`, `GRAPH_REPORT.md`, and `graph.json` you can hand to an agent for an architectural pass.

## Practical Comparison

| Criterion | Graphify | GitNexus | Better choice |
|---|---|---|---|
| Coding-agent integration | Claude Code, Codex, OpenCode, Cursor, Gemini CLI, Aider | CLI + MCP, Codex setup, Claude Code hooks, Cursor / OpenCode support | **GitNexus** |
| Monorepo / multi-repo support | Can graph "any folder" — code + docs + infra | Explicit repository groups, multi-repo MCP, contract extraction, cross-repo queries, group sync/status | **GitNexus** |
| Agent reliability during edits | Useful graph/report; less tied to edit-time guardrails | Skills, MCP tools, Claude hooks, stale-index detection, git-diff impact analysis | **GitNexus** |
| Multimodal context | Strong — code, Markdown, PDFs, images, videos, diagrams | Primarily code intelligence; web/CLI graph explorer + Graph RAG | **Graphify** |
| Local / privacy model | Code parsing is local; docs and images may be sent through the assistant model for semantic extraction | CLI runs locally with no network calls; index stored in `.gitnexus/`; web mode runs in-browser | **GitNexus** for stricter code privacy |
| Language / code parsing | Tree-sitter; documented examples include `.py`, `.js`, `.go`, `.java` | README states "14 Language Support" recently completed | Depends — test on your repo |
| Best use case | "Understand this whole project, including docs / papers / diagrams." | "Help coding agents make safer edits across a large monorepo." | Split usage |

## Suggested Setup for a Research / Code Monorepo

1. **Use GitNexus as the primary agent context engine.** Run it from the monorepo root and wire it into Codex / Claude Code via MCP. Let agents use it for impact analysis, dependency tracing, search, and stale-index warnings during edits.
2. **Use Graphify for architectural and documentation passes.** Run it when the agent needs a higher-level semantic map across code, Sphinx docs, experiment notes, PDFs, diagrams, READMEs, reports, and design docs.
3. **Gitignore the raw indexes.** Keep `.gitnexus/`, `graphify-out/`, and cache directories out of version control by default. Commit curated outputs only — e.g. reviewed excerpts of `GRAPH_REPORT.md` or generated docs.

## Strongest Workflow

```bash
# Agentic coding / monorepo impact analysis
npx gitnexus analyze
npx gitnexus setup

# Broad architecture + documentation / research context
graphify .
```

## Bottom Line

- **GitNexus > Graphify** for day-to-day agentic development on a monorepo.
- **Graphify** when the agent must reason across code + docs + papers + diagrams + experiment writeups.
- The two are complementary — there is no need to pick exactly one.
