---
name: wandb-training
description: >
  How to launch ANY model training or evaluation so it is correctly logged to
  Weights & Biases (wandb). Use whenever starting, queuing, or scripting a
  training/eval run (e.g. main.py, training queues, sweeps), or when a run is
  "not showing up in wandb". Encodes the hard rule: never train without wandb
  logging.
---

# wandb-training

**Hard rule: every training run is logged to wandb.** A `main.py` training launch
without `--wandb-project` is blocked by the `enforce_wandb_training.sh` PreToolUse
hook. This skill says exactly how to satisfy that rule.

## 1. Auth (already set up — do not put keys in files)
Authentication is via `wandb login`, which stored the API key in `~/.netrc`. So
**no `WANDB_API_KEY` and no key in code/config is needed.** If a run reports
"not logged in", run `wandb login` once more; never hardcode a key in the repo,
a skill, or a committed script. If keys were ever pasted into a chat/log, rotate
them in wandb user settings.

- **entity:** `erik_hm`
- **projects:** all runs → project `action6` (older runs used per-arch projects);
  single-frame and sequential both go to `action6`, differentiated by run name.

## 2. Launching a training (skateformer repo)
Always include `--wandb-project` and `--wandb-name`. Run in the `skateformer`
conda env with the protobuf workaround (see the run-training memory):

```bash
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
/home/max/miniconda3/envs/skateformer/bin/python main.py \
  --config <config.yaml> \
  --work-dir <work_dir> \
  --wandb-project action6 \
  --wandb-name <descriptive-run-name>
```

`main.py` (when `--wandb-project` is set) calls `wandb.init(entity="erik_hm", ...)`
and logs per epoch: `train/loss`, `train/acc`, `train/lr`, and on eval
`val/acc`, `val/loss`; it calls `wandb.finish()` at the end. The
`eval_monitor.py` companion additionally logs confusion matrices and per-sample
plots when given `--wandb-project`.

## 2b. Run naming (this skill owns it)

**One string, four places:** `--wandb-name`, `outputs/<run-name>/`, the
promoted `.docs/runs/<run-name>/`, and the timetable row in
`.docs/progress.md`. That is what takes you from a wandb curve to the
checkpoint that produced it without guessing.

```
<YYYYMMDD>-<variant>-<key-hyperparams>
20260911-2D-bs768-e400
```

Date first so runs sort chronologically and `ls` agrees with the wandb run
list. `<variant>` is the thing being tested (`2D`, `seq`, `ablation-noaug`).
Include only hyperparameters that differ from the config baseline. Lowercase
and hyphens throughout — it becomes a directory name.

## 3. Queues / scripts
Any batch/queue runner (e.g. `run_variants_queue.sh`) that calls `main.py` must
pass `--wandb-project`/`--wandb-name` **per job** (use the run name to encode the
variant). A queue that omits them is the classic "curves missing from wandb" bug.

## 4. Escape hatches (rare, deliberate)
- Genuine throwaway debug run: prefix the command with `NO_WANDB=1` (the hook
  then allows it). Use sparingly — real runs always log.
- Evaluation only (no training): `--phase test` is allowed without wandb.

## 5. Pre-launch checklist
- [ ] `--wandb-project` + `--wandb-name` present (name is descriptive/unique)
- [ ] correct project for the architecture (single-frame vs sequential)
- [ ] conda `skateformer` python + `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`
- [ ] `wandb login` valid (netrc), no key hardcoded anywhere
- [ ] for queues: flags passed for every job, not just the first
- [ ] run name follows `<YYYYMMDD>-<variant>-<hyperparams>` and matches the
      `outputs/<run-name>/` directory

Related: [[general-codebase]] audits that these were actually followed.
