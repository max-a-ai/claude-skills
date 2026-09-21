---
name: train-eval-matrix
description: Launch a run for a chosen combination of training sources and evaluation sources, then publish the comparison as an HTML artifact. Use when asked to train on or evaluate on a particular set of datasets, flip a loss or model knob for one run, sweep a data mixture, or compare existing runs across eval sources.
---

# train-eval-matrix

A **combination** is what varies: which sources the run trains on, which it
is evaluated on, and which knobs are flipped. Fix the combination, launch
it, then publish the comparison as one HTML page.

## Read the catalogue from the repo, never from memory

The set of sources lives in the configs. Discover it before offering
choices, because it drifts:

```bash
python3 -c "
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
print('train:', [s['name'] for s in d['data']['train']])
print('eval: ', [s['name'] for s in d['data']['val']])
" configs/<a-current-config>.yaml
```

Current `lidar-bedlam` set, as a starting point to confirm rather than
assume:

- **train**: `waymo`, `sloper4d`, `synth`, `threedpw` — each with a `weight`
  that sets its share of every batch.
- **eval**: `waymo_val`, `sloper4d_test`, `threedpw_test`.
- **knobs** worth varying alone: `loss.*` terms, `model.gate_mode`,
  `model.transl_anchor`, the synthetic pool cap.

## Config or override: the run-name trap

Two ways to express a combination, and they differ in what the run ends up
called:

- **A named experiment gets its own config.** The run name is derived from
  the config's `experiment` field, so a combination you will cite later —
  an ablation row, anything going on the scoreboard — needs
  `configs/<name>.yaml` with a matching `experiment:`. Without it there is
  no run directory by that name, and the monitoring routine that rsyncs
  `outputs/<name>/` silently collects nothing.
- **A one-off knob flip can ride `EXTRA_SET`** on an existing config
  (`EXTRA_SET="loss.box3d=0"`). Cheaper, but the run still takes the *base
  config's* name, so it lands beside the unmodified run with only a
  sequence number between them.

Decide which one the user meant and say which you used.

## Launch

Confirm the exact submit line with the user before running it — launching,
cancelling and requeuing always need their word, every time.

Before submitting, check three things:

1. **The config exists** where the job will look for it. An unset or
   missing `CONFIG` is the dangerous case: job scripts commonly default it
   (`CONFIG=${CONFIG:-configs/<something>.yaml}`), so the job starts a
   completely different experiment instead of failing. Read the default out
   of the job script and confirm the chosen config is really passed.
2. **The code the cluster will run is the code you edited.** Deploy per
   `git-it` Flow D — the user pushes, you pull on the cluster and confirm
   the hash — before the job starts, not after.
3. **The run will be visible in wandb.** `wandb-training` owns the auth and
   the flags; obey it. Where the trainer runs offline and a mirror process
   pushes metrics from a login node, confirm the mirror is alive, or the
   run trains into a void.

After submitting, verify: the job is in the queue, and once it starts, the
job log names the run and config it actually picked up. A submit command
that returned a job id proves nothing about which experiment is running.

## The comparison page

One HTML artifact, republished in place. `run-monitoring` owns the page
conventions — section order, generating from a script rather than editing
HTML, read-then-merge on a refused publish. Follow it; do not restate it.

What is specific here is the shape of the comparison:

- **One table per eval source.** A run that wins on one source and loses on
  another is the normal case, and a single merged table hides it.
- **Rows are runs, ordered by what varied** — the mixture ratio, the knob
  setting — so the axis reads down the column.
- **Mark what is not comparable.** A run trained before a fix, or evaluated
  at a different step, keeps its numbers but is greyed and excluded from
  ranking, with the reason in its own column.
- **Close every table with the reference run**, so each comparison carries
  its own baseline.

Pull the metrics from whichever store the project actually trusts — the
wandb API, or the mirrored `metrics.jsonl` per run. Prefer the full-set
evaluation over in-training validation when both exist, and check the
evaluation's step matches the run's final step before using the row.
