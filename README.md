# MemRL Study

A small research update adapting [MemRL](https://github.com/MemTensor/MemRL) to **DeepSeek-flash + BGE-M3**, with separate experiments on math reasoning and interactive agents.

**Finding:** MemRL used fewer ALFWorld decisions and solver tokens in this run, but did not outperform similarity-only retrieval on success rate. The math result was a small net gain with higher token usage.

## HARP / AIME: math reasoning

Trained on 50 problems with compact memory, then compared two methods on a **fresh fixed set of 50 problems** (100 answers). Memory and Q values were frozen during evaluation.

| Method | Correct | Accuracy | Truncated outputs | Solver tokens |
|---|---:|---:|---:|---:|
| No Memory | 39/50 | 78% | 2 | 152,667 |
| MemRL | 40/50 | 80% | 6 | 219,884 |

Paired results: **35 both correct, 6 both wrong, 5 improved, 4 regressed**. Net gain: one question (+2 percentage points); total solver tokens increased by 44.0%. Output cap: 8,192 tokens per answer. Truncated answers remain in the denominator.

![HARP paired results](figures/harp_paired.svg)

## ALFWorld: interactive agents

One training pass over 100 tasks produced 100 memories and 270 Q updates (98 training successes, **not** a held-out score). Frozen evaluation used the same **50 custom `valid_unseen` tasks** for all three methods; success comes from the environment's `won` flag.

| Method | Success | Mean decisions: all 50 | Mean decisions: common-success 47 | Solver tokens |
|---|---:|---:|---:|---:|
| No Memory | 47/50 (94%) | 20.30 | 18.40 | 3,949,303 |
| Similarity-only | 50/50 (100%) | 15.76 | 14.81 | 2,939,953 |
| MemRL | 49/50 (98%) | 13.86 | 12.66 | 2,539,355 |

On the same 47 tasks successful in every method, MemRL used **31.2% fewer decisions than No Memory and 14.5% fewer than similarity-only**. Across all 50 tasks, total solver tokens were 35.7% and 13.6% lower, respectively. Tokens exclude training and Embedding; they are not monetary costs.

Both retrieval methods share the **same MemRL-trained memory bank**. All methods receive the full legal-action list, with a maximum of 50 decisions per task and 4,096 output tokens per decision. No API errors or output truncations were recorded.

![ALFWorld success](figures/alfworld_success.svg)
![ALFWorld common-success decisions](figures/alfworld_steps_common47.svg)

## Work completed

- DeepSeek/BGE-M3 adaptation and compact memory presentation.
- Frozen evaluation, resume support, request logging and source hashes.
- Offline checks of 100 math answers, 150 agent episodes and 2,496 decisions.
- Replayed 414 scalar Q updates and reconstructed all 100 retrieval-arm rankings. Retrieval sets differed on 33/50 ALFWorld tasks; this verifies mechanism differences, not causal benefit.

## Reproduce this report

Numerical CSVs and all six charts are included. Regenerate SVG figures without model/API requests:

```bash
python -m pip install -r requirements-analysis.txt
python scripts/plot.py --data data --out figures
```

To audit the separately retained original records:

```bash
python scripts/recompute.py --source /path/to/MemRL_stage_handoff_2026-10-20 --out data
```

This repository contains the **stage report and offline analysis**, not a standalone training package. See [Methods and limitations](docs/methods.md) for settings, provenance and data policy.

## Limitations and next step

Single-run, small custom subsets; ALFWorld covers only four layouts. Some tasks became slower or failed with memory. HARP has no similarity-only arm, so it does not isolate Q ranking. This adaptation is not a full reproduction of the paper's models, scale or multi-epoch metrics.

Next: repeat fixed paired evaluations and test true Q against shuffled Q before making stronger claims. No new experiments were started for this report.

Based on [MemRL](https://arxiv.org/abs/2601.03192); benchmarks: [HARP](https://github.com/aadityasingh/HARP) and [ALFWorld](https://github.com/alfworld/alfworld). Implementation and report preparation used AI assistance. Results reflect the saved experimental records.
