# Reversibility and Assumptions

Use reversibility to choose safe next steps under uncertainty.

## Reversibility Ratings

- Highly reversible: tests, docs, prototype, wrapper, feature flag, config change.
- Medium reversibility: new module, new dependency, internal API change.
- Low reversibility: schema rewrite, public API change, architecture rewrite, migration, irreversible data operation.

Low-confidence goals should not cause low-reversibility changes unless the user explicitly accepts the risk.

## Assumption-to-Test Gate

For each major assumption, record:

- assumption
- confidence
- validation method
- fastest useful test
- expected evidence
- failure signal
- decision impact

Convert assumptions into tests, experiments, documentation checks, repository inspection, benchmarks, or user decisions. False or expired assumptions should trigger replanning.
