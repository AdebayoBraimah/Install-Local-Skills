# ML Systems Discipline Reference

Use this reference when designing or reviewing AI/ML implementation plans, training systems, scalable data pipelines, distributed training, reproducibility tooling, or deployment-adjacent workflows.

Sculley et al. describe how ML systems accumulate hidden technical debt through unstable data dependencies, entanglement, configuration sprawl, feedback loops, and weak monitoring. Reference: Sculley et al., "Hidden Technical Debt in Machine Learning Systems," NeurIPS 2015. https://papers.nips.cc/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html

## Technical Debt Checks

- **Data dependencies:** Track dataset versions, source schemas, preprocessing code, filters, sampling policies, and feature generation.
- **Configuration debt:** Keep experiment configuration explicit, typed when possible, versioned, logged, and reproducible.
- **Entanglement:** Avoid changes where a small model or feature adjustment silently affects many unrelated behaviors.
- **Pipeline glue:** Minimize one-off scripts and hidden manual steps between data, training, evaluation, and reporting.
- **Dead experimental paths:** Remove unused features, flags, and model variants after they stop being part of active research.
- **Feedback loops:** Identify when model outputs influence future training or evaluation data.
- **Monitoring debt:** Track data drift, metric drift, calibration, failure slices, latency, throughput, memory, and cost.
- **Reproducibility debt:** Preserve exact code, configs, random seeds, checkpoint metadata, dependency versions, and hardware notes.

## PyTorch / JAX Project Structure

Prefer clear module boundaries:

```text
configs/
src/
  data/
  models/
  training/
  evaluation/
  analysis/
tests/
scripts/
```

Keep model code independent from experiment launchers. Keep evaluation deterministic and runnable from saved checkpoints. Keep analysis scripts separate from training code so benchmark tables can be regenerated.

## Config and Seeding

- Store all hyperparameters, data paths, model choices, optimizer settings, scheduler settings, precision settings, and distributed settings in config.
- Log the resolved config at runtime.
- Seed Python, NumPy, PyTorch or JAX, dataloader workers, environment instances, and distributed ranks.
- Save RNG state in checkpoints when exact resume behavior matters.
- Document nondeterministic operations and hardware-dependent behavior.

## Logging and Checkpointing

- Log metrics at consistent steps and include train, validation, and test namespaces.
- Save best, latest, and periodic checkpoints when runs are long or preemption is likely.
- Store model, optimizer, scheduler, scaler, RNG state, config, step, epoch, and code commit.
- Validate checkpoint load and resume paths with tests or smoke runs.
- Save evaluation artifacts, not only scalar metrics, when qualitative errors matter.

## Distributed and Multi-GPU Planning

- Start with DDP for standard multi-GPU data parallel training when the model fits per GPU.
- Consider FSDP or ZeRO-style sharding when optimizer state, gradients, or parameters exceed memory.
- Consider tensor or pipeline parallelism only when model architecture and hardware topology justify the complexity.
- Use gradient accumulation when global batch size exceeds memory but communication overhead is manageable.
- Profile dataloading, host-to-device transfer, kernel utilization, communication, and checkpoint I/O before optimizing blindly.
- Make evaluation and checkpointing rank-safe.

## Data Pipeline Discipline

- Version raw and processed datasets.
- Separate train, validation, test, and held-out generalization splits.
- Cache expensive transforms with content-addressed or versioned keys.
- Detect schema drift and invalid examples early.
- Keep augmentation deterministic under logged seeds when reproducing experiments.
- Include small synthetic or fixture datasets for fast tests.

## Testing Standards

- Unit test config parsing, model shape contracts, loss functions, metric functions, and checkpoint save/load.
- Smoke test one tiny training run end to end.
- Test distributed initialization and rank-specific behavior when using multi-GPU code.
- Test evaluation from a saved checkpoint.
- Add regression tests for known failure cases and data bugs.

## Scaling Decision Rule

Do not add distributed systems complexity because it is fashionable. Add it when a measured bottleneck or stated scale requirement requires it, and document the cost in debugging, reproducibility, and operational complexity.
