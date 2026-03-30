# Development

- All development should take place on the `main` branch.

# Commit Message Prefixes

| Prefix | Meaning |
|--------|---------|
| **BF** | Bug fix |
| **RF** | Refactoring |
| **ENH** | Enhancement/new feature |
| **BW** | Addresses backward-compatibility |
| **OPT** | Optimization (performance improvements) |
| **BK** | Breaks something and/or tests fail |
| **DOC** | For all kinds of documentation related commits |
| **TEST** | For adding or changing tests |
| **MNT** | For administrative/maintenance changes |
| **CI** | For continuous-integration changes |
| **STY** | Commits that do not affect the meaning (white-space, formatting, missing semi-colons, etc), but change the style |
| **BLD** | Commits that affect build components such as build tool, ci pipeline, dependencies, project version etc. |
| **OPS** | Commits that affect operational components like infrastructure, deployment, backup, recovery etc. |
| **CHORE** | Miscellaneous commits (e.g. modifying .gitignore) |
| **API** | An (incompatible) API change |
| **DEV** | Development tool or utility |
| **REV** | Revert an earlier commit |
| **MERGE**| Merging branches/histories |

> **Note:** Breaking changes should be indicated with an exclamation mark before the colon (e.g., `ENH!: some breaking enhancement`).
