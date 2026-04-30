# Experiment Rigor Reference

Use this reference when designing or auditing AI/ML experiments, paper claims, benchmark tables, ablations, or empirical conclusions.

## Hypothesis Checklist

- State the exact claim being tested.
- Define the target population, dataset, task, or environment family.
- Identify what would falsify the claim.
- Separate primary hypotheses from exploratory analyses.
- Specify expected effect direction and practically meaningful effect size.
- List assumptions about data distribution, supervision, observability, stationarity, compute, and model class.

## Baseline Checklist

- Include the strongest relevant published or standard baselines.
- Include a simple baseline that tests whether complexity is necessary.
- Match data, preprocessing, augmentation, model size where appropriate, compute budget, tuning budget, and evaluation protocol.
- Tune baselines with the same care as the proposed method.
- Report baseline implementation source, commit, hyperparameters, and deviations from published settings.
- Avoid comparing against undertrained, outdated, or compute-starved baselines.

## Ablation Checklist

- Remove each proposed component independently.
- Test interactions between components when the method claims a combined effect.
- Include negative controls or placebo components when feasible.
- Vary important hyperparameters rather than presenting only the best setting.
- In RL/MARL, ablate reward shaping, curriculum, privileged state, communication, centralized critics, parameter sharing, and exploration aids.
- Report ablation variance, not just mean deltas.

## Statistical Analysis Checklist

- Use 3-5+ independent seeds for stochastic training or evaluation.
- Report mean and standard deviation, plus confidence intervals when comparing methods.
- Use IQM, median, percentile profiles, or stratified summaries when results are skewed, heavy-tailed, or benchmark tasks vary widely.
- Report effect sizes and practical significance, not only p-values.
- Use paired comparisons when runs share tasks, folds, or benchmark instances.
- Correct or qualify multiple comparisons when many variants are tested.
- Keep test sets, validation sets, and model selection criteria separate.
- Avoid claiming significance from cherry-picked best checkpoints or best seeds.

## Metrics Checklist

- Choose metrics that match the user-visible or scientific objective.
- Report both aggregate and per-slice metrics for heterogeneous datasets or task families.
- For classification, consider calibration, AUROC/AUPRC, F1, accuracy, log loss, and class-specific metrics as appropriate.
- For generation, include automatic metrics only with human or task-grounded validation when automatic metrics are weak proxies.
- For RL, report reward, success rate, sample efficiency, stability, and generalization when relevant.
- For MARL, add coordination, robustness to partner/opponent changes, communication cost, exploitability, or social welfare metrics when applicable.
- Include compute, wall-clock time, memory, and parameter count when efficiency is part of the claim.

## Failure Analysis Checklist

- Identify failure cases before proposing a new method variant.
- Inspect data slices, environment states, seeds, checkpoints, and qualitative outputs.
- Compare training and evaluation behavior to distinguish optimization failure from generalization failure.
- Check for data leakage, reward hacking, distribution shift, implementation bugs, and evaluation script errors.
- Test whether failures correlate with length, class, domain, difficulty, prompt pattern, observation quality, or agent population.
- Convert recurring failures into targeted ablations or diagnostics.

## Evidence Standards

A result is publication-quality only when the claim, baselines, ablations, statistics, and reproducibility metadata support it together. If one part is absent, state exactly what remains unproven.
