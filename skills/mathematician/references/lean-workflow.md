# Lean Workflow

Use this reference when a mathematical task benefits from Lean formalization.

## Availability Check

Before writing or checking Lean, run:

```bash
~/.agents/skills/mathematician/scripts/check_lean.sh
```

If the script is unavailable:

```bash
lean --version
lake --version
```

Lean verification can only be claimed when the relevant `lean`, `lake env lean`, or `lake build` command exits with status `0`.

## Project Selection

Use this order:

1. Existing project: if the current repo has `lakefile.lean` and `lean-toolchain`, use that Lake project.
2. Repo-local project: if the user explicitly wants formalization committed to the repo, create a project under `lean/` unless they specify another directory.
3. Scratch project: otherwise use `~/lean-work/math_skill`.

Do not create Lean project files in an unrelated repo just because it is the current working directory.

## Scratch Core-Lean Project

```bash
mkdir -p ~/lean-work
cd ~/lean-work
lake new math_skill
cd math_skill
lake build
```

## Scratch Mathlib Project

Use Mathlib only when the theorem needs it.

```bash
mkdir -p ~/lean-work
cd ~/lean-work
lake new math_skill math
cd math_skill
lake build
```

If `lake new math_skill math` is unsupported, create a core project with `lake new math_skill`, explain that Mathlib setup was unavailable, and mark Mathlib-dependent proof attempts `Lean-attempted but incomplete`.

If the generated project pins a different Lean toolchain, prefer the project toolchain through Lake/elan. If that fails, report the toolchain mismatch.

## Suggested Module Layout

```text
math_skill/
├── MathSkill/
│   ├── Basic.lean
│   ├── Algebra.lean
│   ├── Analysis.lean
│   ├── Probability.lean
│   └── MLTheory.lean
├── MathSkill.lean
├── lakefile.lean
├── lean-toolchain
└── README.md
```

File roles:

- `Basic.lean`: logic, sets, functions, induction, natural numbers
- `Algebra.lean`: groups, rings, fields, vector spaces
- `Analysis.lean`: limits, continuity, derivatives, inequalities
- `Probability.lean`: probability spaces, expectation, concentration
- `MLTheory.lean`: optimization, loss functions, learning theory

## Verification Commands

Focused project file:

```bash
lake env lean MathSkill/Basic.lean
```

Whole project:

```bash
lake build
```

Standalone core-Lean file with no project imports:

```bash
lean /tmp/example.lean
```

Always report the exact command and exit status.

## Known Mathlib Namespaces

Use these checked names in the local Mathlib environment instead of guessing from informal mathematical terminology.

Probability measures and expectation infrastructure:

```lean
#check MeasureTheory.ProbabilityMeasure
#check MeasureTheory.IsProbabilityMeasure
#check MeasureTheory.Integrable
#check MeasureTheory.condExp
#check MeasureTheory.Measure.rnDeriv
```

Probability independence, kernels, and distribution laws:

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

## Proof Repair Loop

1. State the informal theorem precisely.
2. Identify variables, domains, assumptions, and conclusion.
3. Try simple examples or counterexamples.
4. Write a small Lean theorem statement.
5. Run Lean.
6. Inspect the first meaningful error.
7. Split the result into helper lemmas.
8. Search for or derive the missing lemma.
9. Rerun Lean.
10. Report `Lean-verified`, `Lean-attempted but incomplete`, `Informal only`, `Counterexample found`, or `Needs additional assumptions`.

Prefer a checked small lemma over an unchecked large proof.
