# Experiment notes

These notes support the main report. This was a small study to learn how to compare memory methods and understand their results.

## Tasks and settings

GSM8K was an early difficulty check: No Memory scored 92/94 (97.87%). That exploration ended; the remaining 106 questions in the original candidate file are not pending work.

For HARP/AIME, I checked difficulty and selected Level 6 problems. The final 50 questions were separate from training and earlier development/calibration sets. I also worked on final-answer parsing, cut-off responses, and memory prompts that were too long.

For ALFWorld, I fixed 50 `valid_unseen` tasks, favoring multi-stage tasks with longer reference action sequences. Selection did not use model test scores. The set contained 17 two-object placement, 16 cleaning, 9 cooling, and 8 heating tasks from four room layouts. It did not overlap training, the earlier test set, or development tasks.

| Setting | HARP / AIME | ALFWorld |
|---|---|---|
| Training | 50 problems | 100 tasks, one pass |
| Final test | 50 problems, two methods | 50 tasks, three methods |
| Model | DeepSeek-flash; temperature 0.6; thinking disabled | Same |
| Embedding model | BAAI/bge-m3 | Same |
| Output limit | 8,192 tokens per answer | 4,096 tokens per decision |
| Task limit | One answer per method | 50 decisions per task |
| Memory during testing | No new memories or Q updates | Same |
| Memory text limit | 1,200 characters per memory; 4,000 total | Same |

The methods received the same test tasks. Both ALFWorld memory methods used the same trained memory bank. Similarity-based memory selected relevant experiences; MemRL also used learned usefulness scores, called Q values. Each task retrieved memory once at the start. All three methods received complete legal-action lists.

ALFWorld's 98/100 training successes are not a test score.

## Reading the results

- **Math accuracy:** checked using a fixed final-answer rule. Cut-off answers stayed in the results.
- **Agent success:** determined by the environment's `won` flag.
- **Decisions:** include invalid actions and actions that made no progress.
- **Same 47 successful tasks:** the identical tasks completed by all three methods. This comparison reduces the influence of failures reaching the step limit; it still needs to be read alongside overall success rates.
- **Tokens:** input plus output for generating answers/actions. Training and Embedding are separate in `data/token_ledger.csv`; some totals are summary-only, and complete HARP costs are unavailable.

ALFWorld recorded no API errors or output truncations. Actions outside the legal-action list were 100/1,015, 36/788, and 26/693 for No Memory, similarity-based memory, and MemRL.

There were counterexamples: MemRL failed a cloth-cleaning task at 50 decisions while similarity-based memory succeeded in 36. A changed memory choice alone does not prove what caused the outcome.

## Limits and next questions

This is one run on small subsets. Longer ALFWorld tasks still produced high baseline success, and only four layouts were covered. The effect of legal-action lists was not separately tested. HARP has no similarity-only comparison, so it cannot show the extra value of Q scores.

Repeated comparisons and closer study of failures are useful next steps. The [original paper](https://arxiv.org/html/2601.03192v2) uses different models, scale, and training schedules; local scores should not be expected to match it.

## Recreate the charts

With Python 3.10+, these commands process saved numbers without model requests:

```bash
python -m pip install -r requirements-analysis.txt
python scripts/plot.py --data data --out figures
```

SVG output is always available. PNG additionally requires Poppler's `pdftoppm`.

For someone with the separately retained original records:

```bash
python scripts/recompute.py --source /path/to/MemRL_stage_handoff_2026-10-20 --out data
```

This checks saved answers, environment results, decisions, tokens, memory records, and file hashes. `data/source_hashes.csv` lists its inputs. Raw questions, responses, trajectories, memory text, private checkpoints, and credentials are not included.

<details>
<summary>Additional implementation details</summary>

Base MemRL commit: `c1b322ca43de36ddf64c6712f89d0095bfc35ce0`. Experiment environment: Linux/WSL, Python 3.10.21, ALFWorld 0.4.2, TextWorld 1.6.2, OpenAI SDK 1.109.1, memoryos 1.0.0.

Retrieval used k=5, topk=3, epsilon=0, and similarity thresholds 0.25/0.62 for HARP/ALFWorld. Similarity-only weights were (1,0); MemRL weights were (0.5,0.5). Q updates used alpha=0.3 and rewards +1/-1. New ALFWorld memories started at Q=0; HARP V3 explicitly used 1/0 for success/failure.

The retained handoff passed its 134-file hash list. An independent cloud/local byte comparison was unavailable. The public files do not support resuming the original training checkpoint.

Final original results: `harp_aime/memrl_compact_train50_v3/confirmation50_v3/` and `alfworld/unseen_challenge50_frozen_v1/`, under `research_records/results/`.

</details>

Sources: [MemRL](https://github.com/MemTensor/MemRL), [HARP](https://github.com/aadityasingh/HARP), [ALFWorld](https://github.com/alfworld/alfworld). Upstream licenses and dataset rights apply; raw benchmark material is not redistributed here.
