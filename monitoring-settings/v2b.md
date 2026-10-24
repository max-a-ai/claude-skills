---
project: v2b
repo: https://github.com/max-a-ai/v2b
local: ~/Documents/v2b
cluster: cluster2 (S11/S12 arms) and helma (S13 pooling arms)
status: open 2026-10-23 (handover from the main v2b chat)
updated: 2026-10-23
---

# Monitoring setting — v2b, Waymo ablations on cluster2 and helma

Taken over 2026-10-23 02:00 from the main v2b chat's handover, plus the
user's "go for helma" for the S13 arms and "fully utilise the helma
GPUs, start the trainings on your own". The 2026-10-16 helma s8e routine
this file held before is in git history.

## 0. Ground set — not repeated here

`tick-it` owns the pass and the layout, `run-monitoring` the setup,
`general-codebase` any script. If this file contradicts a skill, the
skill wins.

## 1. Where things are

| | |
|---|---|
| online repo | https://github.com/max-a-ai/v2b |
| local workspace | `~/Documents/v2b` |
| cluster2 | `ssh cluster2`, repo `~/v2b` (rsynced by the main chat, not git), outputs `/mnt/nas/methods/max/v2b-outputs`, logs `logs/v2b-<job>.out` there |
| helma | `ssh helma`, git checkout `/home/hpc/v103fe/v103fe17/v2b` (pulled to 4a68aed on 2026-10-23; rsync leftovers in `stash@{0}`), outputs and logs `outputs/`, `outputs/logs/v2b-<job>.out`, shards `/hnvme/workspace/v103fe17-bev-v2b/shards/waymo-opv2v` |
| wandb | https://wandb.ai/erik_hm/v2b |
| scoreboard | https://claude.ai/artifact/SAN6KYYFJmAnkGUrfgEM6f |

Scoreboard each tick: `ssh cluster2 'cd ~/v2b && python3 v2b/scripts/v2b-scoreboard.py collect --out outputs/scoreboard.json'`, then fetch with `ssh cluster2 'cat ~/v2b/outputs/scoreboard.json'` (scp of the NAS symlink returns 0 bytes), `python3 v2b/scripts/v2b-scoreboard.py render --in <json> --out <html>`, publish with `url`. The collector sees cluster2 only: helma rows come from reading helma's logs until a finished helma run is copied to the NAS.

## 2. Runs

cluster2, started by the main chat: 3052 `s11k2` hag2, 3058 `s11i2` rebase3 (confirms the re-base gain: full-set target pedestrian >= 0.427, car >= 0.80), 3066 `s12b` mpv64. 3067/3068 (s12a drop2/floor1, zero-shot) done.

helma, S13 pooling arms, each 20 epochs, warm start from s8e, control s11b: `s13b` pool-attn **finished** (1108131, 3 h 17 m, bestval at19, subset ped 0.404 / car 0.786 at 0.5; full set 1109521: ped 0.503 / 0.397 / 0.055, car 0.789); `s13c` pool-hist (1109519, **finished**, bestval at18, full set 1111058: ped 0.505 / 0.405 / 0.054, car 0.785) and `s13a` pool-meanmax (1109520, **finished**, bestval at20, full set 1111059: ped 0.506 / 0.406 / 0.056, car 0.788) resubmitted 2026-10-23 08:30 after the shared-link race (first tries 1108085, 1108130 failed), one H100 each. The loader caps an H100 at ~33 % busy and helma allows 32 cores per GPU, so one arm per GPU in parallel is the maximum with the current code. Epoch 0 of each must read about pedestrian 0.29 / car 0.76 on the subset; far below means the warm start did not take — report, do not submit more.

Parallel helma jobs need 4b0bbf4 or later (own `$TMPDIR/data` link tree via `V2B_DATA_ROOT`). Submit on helma through a login shell, or `module` is missing in the job and it dies in 7 s with exit 127:

    ssh helma 'bash -lc "cd /home/hpc/v103fe/v103fe17/v2b && sbatch v2b/slurm/helma.sbatch configs/<run>.yaml <run>"'

## 2c. S15 sweep (2026-10-23 22:30)

40 cells (floor raw/grid/delaunay/alpha/poisson x pooling max/meanmax/hist/attn x head 0.8 m / 0.4 m `-h04`) in 10 `helma-batch.sbatch` jobs 1116400-1116409, one floor x head each, 4 cells in succession, each trained then scored on the full set in the same job. Batch log `outputs/logs/v2b-batch-<job>.out` (staging, derive, cell starts, TRAIN-FAILED / EVAL-FAILED), cell logs `outputs/logs/v2b-c<k>-<job>.out`. Cell table S15-01..40 in `.docs/progress.md`. Watch: each 0.8 m cell's epoch 0 near pedestrian 0.29 / car 0.76 (-h04 cells start lower, their upsampling layers are fresh); a cell ending without its `[eval]` line; the -h04 jobs near the 23:30 limit. Never resubmit a cell without Max.

Reruns of the attn -h04 cells (S15-08/16/24/32/40): single-cell jobs 1118136-1118140, each `afterany` its -h04 job (1116401/03/05/07, 1117963).

## 2d. S17 LitePT ablations (queued 2026-10-24 02:30)

13 cells (`configs/s17*`, grid floor, attention stages from `v2b/train/bev_attention.py`) in 4 `helma-batch.sbatch grid` jobs 1118119-1118122, each `afterany` one 0.8 m S15 job (1116400/02/04/06), so they start when those end (~15:45). Control: S15-09. Watch the first epochs of S17j (C-C-A-A) and S17l (conv E4): both spiked transiently in the smoke test. Poisson jobs are 1117962/1117963 (resubmitted after the Open3D fix).

## 2e. Training queue (from 2026-10-24 03:45)

Pending work lives in helma's `outputs/queue/` (todo/running/done/failed), pulled by `helma-worker.sbatch` jobs; check it each tick with `ssh helma 'cd ~/v2b && python3 v2b/scripts/v2b-queue.py list'` and report the counts as deltas. Workers 1118746-1118755 start as the S15 jobs end. The S17 jobs 1118119-22 and the rerun jobs 1118136-40 were cancelled (pending, Max's word) and their trainings queued. A training in failed/ is reported, not requeued, without Max's word. Worker log `outputs/logs/v2b-worker-<job>.out`.

## 3. Full-set evaluation of a finished training (routine)

Score under the run's **own** name so the run dir holds the checkpoint:

    EXTRA_ARGS='--eval-only --ap-samples -1' sbatch --job-name=eval-<run> v2b/slurm/<site>.sbatch configs/<run>.yaml <run>

The log then notes `eval of the run's checkpoint at epoch N` and `outputs/<run>/eval.json` is written. The handover's `<run>-eval` name does **not** work: `outputs/<run>-eval` has no checkpoint, so `--eval-only` falls back to the spec's `init_from` (s8e) and scores the baseline. That is what job 3050 did; the scoreboard's `s11f2-...-synth2-eval` row is s8e, not s11f2. Before recording any eval, check the `note :` line names the run's own checkpoint. Never start a job while another job of the same spec runs: both use `resources/data/generated/mixtures/<spec>-{train,val}`, and the newcomer rebuilds it under the running job (job 3069 died that way when 3070 started).

## 4. Rules

Never cancel or resubmit a training without Max; evaluations are routine. Progress log `.docs/progress.md`, commit one line `docs: ...`, never push. Push-notify on a finished or failed run.

## 5. Queue commands

cluster2: `squeue -u max -o "%.6i %.40j %.8T %.10M %R"`. helma: `squeue -u $USER -o "%.9i %.9P %.28j %.2t %.10M %.6D %R"`.
