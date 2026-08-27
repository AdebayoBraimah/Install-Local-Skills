# Calibration: what real ICLR 2026 reviews looked like, and what actually decided outcomes

Distilled from 7 real ICLR 2026 submissions (4 accepted as posters, 3 rejected)
with 25 official reviews, meta-reviews, and full rebuttal threads. All papers
were in the multi-agent / LLM / RL / learning-theory space.

## 1. Score calibration

Observed rating profiles:

| Outcome | Rating profiles seen | Note |
|---|---|---|
| Accept (poster) | 4/6/6/4→6 · 2/4/6/2 · 6/4/4/6 · 4/8/6/2 | avg ≈ 4.5–5.5 |
| Reject | 2/6/4 · 4/6/4/2 · 4/6/6/6 | avg ≈ 4–5.5 |

Consequences for calibrated reviewing:

- **Ratings cluster at 4 and 6.** A borderline paper gets 4s and 6s, not 5s.
  Reserve 8 for a paper you would argue *for* in discussion; reserve 2 for a
  paper with a premise-level flaw. Do not hand out 6-by-default.
- **The overall Rating barely separates accept from reject** at the margin.
  What separated them in practice:
  - **Contribution sub-score is the strongest single predictor.** All three
    rejected papers had unanimous (or near-unanimous) `Contribution: 2`.
    Every accepted paper had at least one reviewer at Contribution 3+.
    Score Contribution honestly and independently of Soundness.
  - **The character of the weaknesses**, not their count (see §2).
- **Confidence honesty**: use 4 only when you actually checked the math or
  know the cited prior work; use 3 otherwise. The harshest reviewers with
  Confidence 4 carried the most weight with ACs.

## 2. Patchable vs fatal weaknesses (the real accept/reject axis)

**Patchable** (all accepted papers' criticisms were of this kind — fixable by
rebuttal experiments or a revision):
- Limited scope: one domain (math-only), small models (3B), 2 agents, few seeds
- Statistical rigor: no CIs, no multi-seed runs, possibly-noise deltas
- Re-implemented or possibly weakened baselines; wants equal-budget comparison
- Terminology and positioning gripes; missing citations; unclear exposition
- Missing named ablation or an extra requested benchmark

**Fatal** (each rejected paper died on at least one — no rebuttal experiment
can fix them):
- **Premise-level objection**: the problem setup itself is artificial — e.g.
  a multi-agent method evaluated on tasks a single model solves, so gains may
  just be extra fine-tuning. ("Why does this task need your machinery at all?")
- **No in-regime baseline**: closest published competitors never compared
  against, with the rebuttal *arguing they are incompatible* instead of
  constructing any comparable baseline. ACs read this as evasion.
- **"The results are expected"**: theory that follows black-box from known
  results; bounds reviewers call straightforward corollaries. Unanimous
  Contribution: 2 follows, and rebuttals cannot manufacture surprise.
- **Overclaiming caught in the act**: claiming a "new protocol"/framework the
  rebuttal later retracts; a theorem a reviewer derives from a trivial
  reduction, forcing a public correction. Credibility damage propagates to
  the meta-review.
- **Shallow analysis for the paper type**: a benchmark paper whose findings
  reduce to "models degrade with scale" with no mechanism-level insight.

When writing a weakness, decide which kind it is and say so implicitly: a
patchable weakness ends with a concrete fix; a fatal weakness states why the
central claim cannot stand as evidenced.

## 3. What made borderline papers land positively

- **Rebuttals with NEW EXPERIMENTS beat rebuttals with arguments.** Every
  accepted paper's rebuttal added experiments targeted at named weaknesses
  (multi-seed stats, larger models, transfer experiments, the requested
  baseline, a finite-time theorem). Rejected papers' rebuttals argued
  incompatibility or conceded scope.
- **ACs extrapolate.** Scores often never move (reviewer silence after
  rebuttal is normal; ICLR 2026 froze discussions mid-cycle), and ACs decided
  from "this concern is addressed / this reviewer would likely raise."
  A meta-review should therefore judge whether each major concern *has been
  or could be* addressed, not just tally scores.
- **A defensible novelty core survives harsh reviews.** Papers with one crisp,
  conceded contribution ("intrinsic rewards from interaction, no external
  supervision", "the trilemma framing") absorbed a 2-rating and still won.
- **Practicality resonates**: cheap/deployable stories (small trainable
  helper, offline-only LLM use, released datasets/code) were cited by
  reviewers and ACs as accept-side arguments.

## 4. Recurring weakness archetypes (use as a checklist against any manuscript)

1. Baselines: are the closest *published* methods compared head-to-head, in
   their native/optimal configurations? Re-implementation = flag.
2. Statistical rigor: seeds, variance, significance; is the headline delta
   bigger than the noise?
3. Scope vs claims: does "multi-agent"/"scalable"/"general" match what was
   actually run (2 agents, 3B models, one domain, 5x5 grids)?
4. Novelty vs named prior work: what precisely is new relative to the 2–4
   closest papers? (Reviewers name papers; do the same. Search if possible.)
5. Necessity of machinery: would a simpler method (single agent, standard
   fine-tuning, known algorithm) plausibly match the gains?
6. Theory nontriviality: do theorems follow black-box from known results?
   Is the interesting object in the formalism actually realized in the
   implementation?
7. Assumptions vs framing: do strong assumptions (known dynamics, central
   precomputation, ground-truth labels at test time) contradict the framing
   (decentralized, unsupervised, practical)?
8. Fair-comparison hygiene: equal compute/token budgets, same base models
   across tables, contamination-suspect benchmarks, tiny eval sets (n=30).
9. Analysis depth: mechanism-level insight (failure modes, error propagation,
   what was actually learned), not just aggregate deltas.
10. Presentation: overloaded figures, appendix-buried details, undefined
    notation, terminology that collides with established usage.

## 5. Meta-review norms (for the Area Chair)

- Enumerate each reviewer's main concerns and mark: resolved in rebuttal /
  unresolved / unresolvable.
- Predict score trajectories ("R3 would likely raise from 4") rather than
  averaging posted numbers.
- The decision sentence names the single decisive axis: e.g. "technical
  objections resolved; scope focused but above bar" (accept) vs "the
  fundamental concern — machinery imposed on tasks not requiring it —
  remained outstanding" (reject).
