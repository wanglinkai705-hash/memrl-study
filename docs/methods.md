# Methods and data notes

Stage evaluated and audited on 2026-10-20. All results describe one local adaptation run.

## Experimental settings

| Setting | HARP / AIME | ALFWorld |
|---|---|---|
| Training | 50 problems, V3 compact memory | 100 tasks, one pass |
| Evaluation | Fresh fixed 50 problems, two arms | Custom `valid_unseen` 50 tasks, three arms |
| Model | DeepSeek-flash, temperature 0.6, thinking disabled | Same |
| Embedding | BAAI/bge-m3, 1,024 dimensions | Same |
| Retrieval | k=5, topk=3, threshold 0.25 | k=5, topk=3, threshold 0.62 |
| Similarity/Q weights | (0.5,0.5) | Similarity-only (1,0); MemRL (0.5,0.5) |
| Exploration | epsilon=0 | epsilon=0 |
| Memory presentation | 1,200 characters per memory; 4,000 total | Same caps; SCRIPT/reflection only |
| Evaluation updates | No memory writes or Q updates | Same; one retrieval before each episode |
| Output budget | 8,192 tokens per answer | 4,096 tokens per decision; 50 decisions per task |

ALFWorld task composition: two-object placement 17, cleaning 16, cooling 9, heating 8. Four floor plans contribute 29/5/3/13 tasks. Selection used reference walkthrough action counts, not model failures. The challenge IDs do not overlap training, the old `valid_seen` evaluation set or dev3.

Similarity-only uses the MemRL-trained bank; it is a retrieval ablation, not independently trained RAG. All arms receive complete legal-action menus. The shared-bank design controls memory content but does not isolate every source of generation variability.

## Definitions and checks

- A decision includes invalid or unproductive actions. It is not wall-clock time or a simulator motor step.
- The common-success set contains the same 47 task IDs successful in all methods. It is an outcome-conditioned comparison and is reported alongside all-task results.
- Actions outside the saved legal-action list: No Memory 100/1,015 (9.85%), similarity-only 36/788 (4.57%), MemRL 26/693 (3.75%). This does not count every kind of poor action.
- Solver tokens are summed from per-answer/per-step API usage. Training and Embedding are separate in `data/token_ledger.csv`; provenance labels identify summary-only totals. HARP end-to-end memory-generation/Embedding usage is incomplete.
- HARP correctness uses the existing fixed parser and saved numeric answers. No rescoring, repair or exclusion of truncated answers was applied.
- The audit checks source hashes, paired membership, final `won`, decision numbering, action-list membership, token totals and frozen bindings.
- It replays Q updates with alpha=0.3 and reward +/-1. ALFWorld initializes new Q at zero; HARP V3 explicitly initializes new memories at 1/0 for success/failure, overriding generic configuration fields.
- All 100 retrieval-arm rankings can be reconstructed from saved similarities, candidate membership and Q, within `1e-6` score tolerance. Embeddings were not regenerated. Fifty-four ALFWorld memories have no subsequent utility update.

Positive cases coexist with counterexamples: a two-CD task takes 37/32/11 decisions; a cloth-cleaning task ending in `022321_380927` fails at 50 with MemRL while similarity-only succeeds in 36. A retrieval change and a causal improvement are separate claims.

## Reproducibility and provenance

Base MemRL commit: `c1b322ca43de36ddf64c6712f89d0095bfc35ce0`. Recorded experiment environment: Linux/WSL, Python 3.10.21, ALFWorld 0.4.2, TextWorld 1.6.2, OpenAI SDK 1.109.1 and memoryos 1.0.0.

Final original record directories:

- `research_records/results/harp_aime/memrl_compact_train50_v3/confirmation50_v3/`
- `research_records/results/alfworld/unseen_challenge50_frozen_v1/`

The audit used the retained local handoff archive and its export directory. All 134 manifest entries passed SHA-256 checks and matched the local ZIP. Remote attachment download failed, so an independent cloud/local byte comparison was not performed. `data/source_hashes.csv` identifies the inputs used by the offline script. Private native checkpoints and complete journals are not included; the report package cannot provide a bit-identical training resume.

Dataset SHA-256:

- HARP confirmation: `9ac65341d1f6c097ff228e0ab3c7a8f9a25ee1f8babba033abd8b0922486aacf`
- ALFWorld challenge: `c8a92caf53f24df4fe755a5a7e20a72cc36db13a7952386b4a22bde3d02ae2cb`

## Scope and attribution

The [MemRL paper v2](https://arxiv.org/html/2601.03192v2) uses GPT-5-mini for ALFWorld, 3,553 runtime tasks over 10 epochs and 140 `valid_seen` transfer instances. Its last-epoch SR, cumulative SR and transfer SR are different settings. This project uses DeepSeek-flash, one pass and a custom `valid_unseen` subset. HARP/AIME is a local extension, not the paper's HLE benchmark.

GSM8K is a closed exploratory appendix: 92/94 correct (97.87%) from an initial 200-question candidate file; the remaining 106 are not pending experiments.

This repository publishes new report text, numerical measurements, identifiers, hashes, analysis scripts and charts. It excludes raw benchmark questions, model answers, trajectories, memory bodies, native checkpoints and credentials. The upstream repositories retain their licenses. MemRL and ALFWorld declare MIT; HARP's repository also displays MIT, but underlying contest/AoPS material requires source-specific redistribution review. Raw benchmark material is therefore not redistributed here.

Official sources: [MemRL](https://github.com/MemTensor/MemRL), [HARP](https://github.com/aadityasingh/HARP), [ALFWorld](https://github.com/alfworld/alfworld).
