# AI/ML Lean Workflow Reference

Use this reference when the task needs Lean/mathlib formalization or detailed AI/ML theorem critique.

## Lean Project Selection

1. If the current repository has `lakefile.lean` or `lakefile.toml` plus `lean-toolchain`, use that project.
2. If the user explicitly asks to commit formalization into the current repository, ask where it belongs unless a `lean/` or `formal/` convention already exists.
3. Otherwise use `~/lean-ai-ml-math/AIMLMath`.

Do not add Mathlib to a user's existing project without explicit approval.

## Theorem Formalization Pattern

Start with the smallest statement that captures the mathematical issue:

```lean
import Mathlib

#check Real
#check Matrix
#check ConvexOn
```

Then add definitions and small lemmas. Prefer checking types and existing theorem names before writing a large proof.

Useful commands and tactics:

- `#check`
- `#find`
- `exact?`
- `simp?`
- `rw?`
- `simp`
- `ring`
- `nlinarith`
- `aesop`

Automation is acceptable only if the file compiles.

## Status Reporting

Report Lean status with:

```markdown
## Lean Formalization Status

Status: Lean-attempted but incomplete

Command:
`lake env lean AIMLMath/Sanity.lean`

Exit status:
1

Reason:
- The theorem statement type-checks.
- The proof fails because ...
- The informal proof depends on ...
```

## Domain Reminders

## Known Mathlib Namespaces

Use these checked namespaces in the local Mathlib environment instead of guessing from paper terminology.

Probability measures and expectation infrastructure:

```lean
#check MeasureTheory.ProbabilityMeasure
#check MeasureTheory.IsProbabilityMeasure
#check MeasureTheory.Integrable
#check MeasureTheory.condExp
#check MeasureTheory.Measure.rnDeriv
```

Probability independence, kernels, and laws:

```lean
#check ProbabilityTheory.Indep
#check ProbabilityTheory.IndepFun
#check ProbabilityTheory.iIndepFun
#check ProbabilityTheory.IdentDistrib
#check ProbabilityTheory.Kernel
#check ProbabilityTheory.condDistrib
```

Information theory and likelihood ratios:

```lean
#check InformationTheory.klDiv
#check InformationTheory.klFun
#check MeasureTheory.llr
```

Avoid these common wrong names in this Mathlib revision:

```lean
-- ProbabilityTheory.ProbabilityMeasure
-- MeasureTheory.indepFun
-- ProbabilityTheory.condExp
-- MeasureTheory.rnDeriv
-- klDiv
-- klFun
```

### Optimization

Convex plus smooth usually gives sublinear rates under suitable step sizes, not linear convergence without stronger assumptions such as strong convexity or a Polyak-Lojasiewicz condition. Always state step-size restrictions and convergence target.

### Reinforcement Learning

Bellman contraction arguments need a discount `gamma` with `0 <= gamma < 1`, a norm such as sup norm, and a well-defined operator over value functions. Finite MDP statements are much easier to formalize than measurable-space MDPs.

### Probability and Statistics

Expectation identities usually require measurability and integrability. Product expectation factorization needs independence or an equivalent factorization assumption. Conditional statements require sigma-algebra clarity.

### Linear Algebra

PSD spectral conclusions normally require symmetric real matrices or Hermitian complex matrices. For arbitrary matrices, a quadratic form only sees the symmetric/Hermitian part.

### Information Theory

KL divergence requires support/absolute-continuity conditions. Entropy and mutual information may require finiteness assumptions. Carefully track which distribution the expectation is under.
