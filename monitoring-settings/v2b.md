---
project: v2b
repo: https://github.com/max-a-ai/v2b
local: ~/Documents/v2b
sites: cluster2, helma
status: open 2026-10-23 (handover from the main v2b chat)
updated: 2026-10-31
---

# Monitoring setting — v2b, Waymo ablations on cluster2 and helma

Taken over 2026-10-23 02:00 from the main v2b chat's handover, plus the
user's "go for helma" for the S13 arms and "fully utilise the helma
GPUs, start the trainings on your own". The 2026-10-16 helma s8e routine
this file held before is in git history.

## 0. Ground set — not repeated here

`tick-it` owns the pass and the layout, `run-monitoring` the setup and
`run-monitoring/defaults.md` everything every scoreboard does (queue on top,
folding, confirmation boxes, plots and their settings, the tick order, what
is routine); `general-codebase` any script. This file holds only what is
specific to v2b. If it contradicts a skill, the skill wins.

## 0a. Custom: metrics and tables

- **Metrics**: BEV AP per class at IoU 0.3 / 0.5 / 0.7, classes
  pedestrian / car / bicycle (truck on the old V2X-Real rows), mAP = mean of
  the three classes per IoU; higher is better. Headline: pedestrian AP@0.5.
  Per-epoch series: the trainer's subset validation (`val/ap_bev@<iou>/<class>`
  in `outputs/logs/v2b-*.out`); full set: `outputs/<run>/eval.json`. Also
  shown, not plotted: params, ms / sweep, message / frame (`capabilities.json`).
- **Tables** (`PAPER_TITLES`, `paper_tables`, `TRANSFER_BLOCKS` in
  `v2b/scripts/v2b-scoreboard.py`): paper tables A (Waymo validation), B
  (V2X-Real V2V, benchmark protocol), C (V2B zero-shot), D (ours and its
  levers), X (transferability, V2X-Real-only sources); then Table 1-3 per
  dataset, the subset table, published rows. Competitors first, then ours,
  each of our values with its change to the best competitor value of the block.
- **Plot scopes**: global; queue; paper -> paper/a, b, c, d, x. Default
  three columns: ped@0.3, ped@0.5, ped@0.7. Stored in `.docs/scoreboard-plots.json`.
- **Store**: artifact slug `cbc3289e-2d59-470e-bd87-10ffdb85e610`
  (capabilities db + user): `acks/*`, `plots/*`.

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

Store fold-in per defaults.md section 4: `.venv/bin/python v2b/scripts/v2b-scoreboard.py ack <run ...>` (every `run` of `acks`) and `... plots SCOPE=a,b,c ...` (every `plots` doc with cols; scope ids use `~` for `/`). Seed repeats (`-repN`, Max 2026-11-06): the script lists one in the to-confirm box only when its car or ped AP@0.5 is more than 0.03 off seed 1 (or off the other seeds' mean when seed 1 has no result), `SEED_CHECK_GAP`; agreeing repeats skip the box, so do not list them in the report either. Never seed acks again (`--seed-from` ran once on 2026-10-31 with 148 results); never delete the acks docs. Render: `.venv/bin/python v2b/scripts/v2b-scoreboard.py render --in <cluster2.json> <helma.json> --queue cluster2=<dump> helma=<dump> --out <html>`.

## 2. Runs

cluster2, started by the main chat: 3052 `s11k2` hag2, 3058 `s11i2` rebase3 (confirms the re-base gain: full-set target pedestrian >= 0.427, car >= 0.80), 3066 `s12b` mpv64. 3067/3068 (s12a drop2/floor1, zero-shot) done.

helma, S13 pooling arms, each 20 epochs, warm start from s8e, control s11b: `s13b` pool-attn **finished** (1108131, 3 h 17 m, bestval at19, subset ped 0.404 / car 0.786 at 0.5; full set 1109521: ped 0.503 / 0.397 / 0.055, car 0.789); `s13c` pool-hist (1109519, **finished**, bestval at18, full set 1111058: ped 0.505 / 0.405 / 0.054, car 0.785) and `s13a` pool-meanmax (1109520, **finished**, bestval at20, full set 1111059: ped 0.506 / 0.406 / 0.056, car 0.788) resubmitted 2026-10-23 08:30 after the shared-link race (first tries 1108085, 1108130 failed), one H100 each. The loader caps an H100 at ~33 % busy and helma allows 32 cores per GPU, so one arm per GPU in parallel is the maximum with the current code. Epoch 0 of each must read about pedestrian 0.29 / car 0.76 on the subset; far below means the warm start did not take — report, do not submit more.

Parallel helma jobs need 4b0bbf4 or later (own `$TMPDIR/data` link tree via `V2B_DATA_ROOT`). Submit on helma through a login shell, or `module` is missing in the job and it dies in 7 s with exit 127:

    ssh helma 'bash -lc "cd /home/hpc/v103fe/v103fe17/v2b && sbatch v2b/slurm/helma.sbatch configs/<run>.yaml <run>"'

## 2c. S15 sweep (2026-10-23 22:30)

40 cells (floor raw/grid/delaunay/alpha/poisson x pooling max/meanmax/hist/attn x head 0.8 m / 0.4 m `-h04`) in 10 `helma-batch.sbatch` jobs 1116400-1116409, one floor x head each, 4 cells in succession, each trained then scored on the full set in the same job. Batch log `outputs/logs/v2b-batch-<job>.out` (staging, derive, cell starts, TRAIN-FAILED / EVAL-FAILED), cell logs `outputs/logs/v2b-c<k>-<job>.out`. Cell table S15-01..40 in `.docs/progress.md`. Watch: each 0.8 m cell's epoch 0 near pedestrian 0.29 / car 0.76 (-h04 cells start lower, their upsampling layers are fresh); a cell ending without its `[eval]` line; the -h04 jobs near the 23:30 limit. Never resubmit a cell without Max.

Reruns of the attn -h04 cells (S15-08/16/24/32/40): single-cell jobs 1118136-1118140, each `afterany` its -h04 job (1116401/03/05/07, 1117963).

From e051196 a claim holds a per-spec lock (`outputs/queue/locks/<spec>`), so a spec never trains twice. Eval-only tasks: `v2b-queue.py add <spec> --eval-only`; `v2b-queue.py requeue <failed task>` only with Max's word. S15-39 eval: one-task queue `outputs/queue-eval`, worker 1126138.

## 2d. S17 LitePT ablations (queued 2026-10-24 02:30)

13 cells (`configs/s17*`, grid floor, attention stages from `v2b/train/bev_attention.py`) in 4 `helma-batch.sbatch grid` jobs 1118119-1118122, each `afterany` one 0.8 m S15 job (1116400/02/04/06), so they start when those end (~15:45). Control: S15-09. Watch the first epochs of S17j (C-C-A-A) and S17l (conv E4): both spiked transiently in the smoke test. Poisson jobs are 1117962/1117963 (resubmitted after the Open3D fix).

## 2e. Training queue (from 2026-10-24 03:45)

Pending work lives in helma's `outputs/queue/` (todo/running/done/failed), pulled by `helma-worker.sbatch` jobs; check it each tick with `ssh helma 'cd ~/v2b && python3 v2b/scripts/v2b-queue.py list'` and report the counts as deltas. Workers 1118746-1118755 start as the S15 jobs end. The S17 jobs 1118119-22 and the rerun jobs 1118136-40 were cancelled (pending, Max's word) and their trainings queued. A training in failed/ is reported, not requeued, without Max's word. Worker log `outputs/logs/v2b-worker-<job>.out`.

## 2f. Develop handover fb5d2c8 (started 2026-10-25 15:00, Max's go)

cluster2: V2X-Real cooperative baselines s10a/b/c (3092-3094, 20 epochs; old dirs kept in `outputs/superseded/<run>-try1`), then the full-set eval of each under its own name (routine) and its capabilities line. CooPre chain 3095 pretrain, 3096 ft-scratch, 3097 ft-pre (afterok 3095), 3098/3099 evals; rows from `outputs/coopre/<run>/eval.yaml`, protocol "CooPre's own eval". Capabilities 3100-3134 (`outputs/<run>/capabilities.json`, log `logs/cap-<job>.out`); their ms are taken on a shared node, not the idle benchmark. helma queue: s18a (worker 1129586, Poisson derive first), s19a (`--no-eval`, pretraining: watch train/recon_count, train/recon_profile, train/masked_cells ~1200 per batch; bestval = lowest val/loss), s19c (control). After s19a is done: `v2b-queue.py add s19b-heal-m1-waymo-3cls-attn-rebase3-ft-pretrain` (expect "280/286 tensors adopted"). Not started: s15a/s15b (CodeFilling still broken), s19d/s19e (schwind split on neither site).

## 2g. S21 grid (queued 2026-10-25 16:10, Max's go)

Eight cells on Poisson + 0.8 m head in helma's queue, workers 1129812-1129815 (plus the three of 2f): s21a/b S17e backbone with attn / mean+max pooling (controls S15-36 / S15-34), s21c S17i backbone with attn, s21d-g repeats of S15-36 and S15-34 (spread), s21h S15-36 for 40 epochs. Each worker derives the Poisson split first (3-5 h). Epoch 0 of the warm-started cells must read near the S15 Poisson cells' epoch 0; s21h's row is its epoch-40 checkpoint. Report the pooling and backbone verdicts against the repeat spread, not against one run.

## 2h. Table 2, V2X-Real (develop handover 2026-10-26)

Static rule: when a row lands, copy ped / car / bic AP@0.5, mAP@0.5, params, ms and message bytes into `.docs/tables/table2-v2xreal.md` with the date, commit, never touch the row again. Chain (local background task): cluster2 `dm_pack` of v2xreal-opv2v (log `logs/pack-v2xreal.log`) -> `dm_push.sh` to helma shards -> one-off job `derive-v2xreal-poisson` (log `outputs/logs/derive-v2xreal-poisson-<job>.out`, ends `DERIVE-PACK-DONE`). Then submit the handover's s20z (eval-only) and s20a-d lines with `helma.sbatch`, own-name evals, capabilities on cluster2. s10a-c rows come from cluster2 3092-3094. s16b/c/d wait for a schwind OPV2V export (none exists).

## 2i. DDP validation s22a (2026-10-25 21:30)

Chain on helma: 1132901 derive + pack `shards/waymo-opv2v-rebase-poisson` (log `outputs/logs/derive-waymo-poisson-<job>.out`, ends `DERIVE-PACK-DONE`), 1132902 `helma-ddp.sbatch` s22a on 4 H100 (log `outputs/logs/v2b-ddp-<job>.out`; must print "DDP over 4 GPUs, 2 per GPU, SyncBatchNorm"), 1132903 its own-name full-set eval. Pass: full-set pedestrian / car within +-0.007 of 0.463 / 0.865; report minutes per epoch against S15-36's 1-GPU log. Only after a pass: single long runs on `helma-ddp.sbatch`; S21 repeats and s19b stay on 1 GPU.
**2026-10-26 01:00: s22a failed** (NCCL timeout after epoch 0, mismatched collective on rank 0); 1132903 cancelled. Nothing runs on `helma-ddp.sbatch` until develop fixes it and Max gives the word.

## 2j. S24 (queued 2026-10-26 07:40, Max's go)

**08:05: moved to 4-GPU `helma-ddp.sbatch` jobs** (Max): s22a 1141447 / eval 1141448, s24d 1141449 / 1141450, s24b 1141469 -> s24c 1141470 / eval 1141471, grid pack 1141452 -> s24a 1141453 / eval 1141454 (all afterok). The queue tasks of the 1-GPU tries are in `failed/` (moved, not failed); s24c is chained, no manual add. Report minutes per epoch (wandb `_runtime`) against the 1-GPU reference once epochs land.

helma queue, workers 1141406-1141408: s24a (s19c for 35 epochs; compare s19b 0.467 / s19c 0.441), s24b (`--no-eval`, pretraining on Poisson; watch train/recon_count, train/recon_profile, train/masked_cells), s24d (A-A-A for 40 epochs; compare s21c, s21h). **When s24b is done:** `v2b-queue.py add s24c-heal-m1-waymo-3cls-attn-poisson-ft-pretrain-e40 --est-h 8` (expect ~284/290 tensors adopted; compare s21h 0.479 / 0.871).

## 2k. S28 (develop, cluster2, from 2026-10-28)

`cluster2-s28.sh` chains s28a-h pretraining -> fine-tune (afterok) and the from-scratch control s28z (4 epochs, `subset: 0.5`, grid floor) but no eval: when a fine-tune or s28z finishes, submit its own-name full-set eval (`EXTRA_ARGS="--eval-only --ap-samples -1" sbatch --job-name=eval-<run> v2b/slurm/cluster2.sbatch configs/<run>.yaml <run>`), routine. s28z eval: 3994.

## 2l. S29 dark-box evals and S30 fusion trunk (develop, from 2026-10-29 14:50)

Launched by develop (c8fd80b, 96963d9), not here. cluster2: s29c/d/e (4025-4027) are eval-only rows (dark-box filter at 0.10/0.12 on S15-10, 0.10 on s8e); compare each with its source row. helma: smoke-fusion-trunk 1176179 gates s30a-f (1176180-85, afterok). s30a-c = AttFuse / F-Cooper / V2X-ViT with the single-agent trunk, ours (attn + Poisson), s30d-f = the same, HEAL (raw); V2X-Real VC, benchmark protocol. Pair a vs d, b vs e, c vs f. Whether they need a separate eval job is unconfirmed: check the specs before submitting one.
2026-10-29 17:00: s29c-e done (filter costs ped 0.03-0.06, car unchanged). Smoke passed; s30a/b/d/e running; s30c/f (V2X-ViT) failed on a 4x cls/anchor size mismatch, and CooPre eval-pre 1169453 failed on a stale /tmp/1169452.helma dataset path in the run config. Both handed to develop; resubmit nothing for them until develop's fix lands and Max says so.
s30 trains with per-epoch val only, so each finished s30 run gets its own-name full-set eval on helma (routine, `bash -lc`, `helma.sbatch`, section 3): s30a 1177950, s30d 1177953 (2026-10-29 18:00, done 18:35); s30b 1178281, s30e 1178282 (19:00).
2026-10-30 00:00: develop fixed both (15977b7, 4de0c17) and resubmitted: CooPre eval-pre 1179930 done (CooPre's own protocol, all ranges vehicle / ped / truck 0.672 / 0.302 / 0.542, mAP 0.505); s30c 1179931, s30f 1179932 rerun. When each finishes, submit its own-name full-set eval (routine): s30c 1184634, s30f 1184635 (2026-10-30 10:04).

2026-10-30 19:00: s30c/f full-set done (ours 0.488 mAP vs HEAL 0.379); all three s30 pairs closed.

## 2m. CooPre second fusions, CooPre Waymo chain, S24e and S31 (develop, helma, from 2026-10-30 ~15:00)

Launched by develop (6c30a32, ad38a9b, 22ef4b0, d343dfe), not here. CooPre chains (coopre-waymo-*, coopre-v2v-* incl. -fcooper-/-v2xvit-) carry their own eval jobs as afterok dependencies: do not submit evals for them. s24e and s31a-h are v2b trainings: when one finishes without its own eval.json, section 3 applies. Never cancel or resubmit any of them without Max's word.

2026-10-31 01:00: s24e, s31a, s31b, s31c done; own-name full-set evals 1188142, 1188139, 1188140, 1188141 (routine).

2026-10-31 02:00: evals done; s24e 0.499 / 0.866 / 0.078 (ped / car / bic), s31a-c in progress.md. s26h runs on cluster2 as 4086 (develop).

2026-10-31 11:00: s31d-h done; own-name full-set evals s31d 1189562, s31e 1189563, s31f 1189564, s31g 1189565, s31h 1189566 (routine). Cron 7076d88b hourly from 11:00.

2026-10-31 13:00: develop launched s24f 1189668 (raw-floor pretraining, done 13:08, no eval) and s24g 1189669 (fine-tune, 20 ep). When s24g finishes: own-name full-set eval (routine).

## 2o. V2X-Real yaw bug and S32 bicycle table (develop, from 2026-10-31 14:00)

Every V2X-Real export before 9e5b903 wrote box yaw = raw + 2 x ego yaw. Car and truck AP of all HEAL-recipe V2X-Real rows (s10, s20, s25, s27, s30, s31) are on wrong labels; pedestrian (square boxes) and CooPre rows (raw labels) are unaffected. Never report s30/s31 car or truck numbers as final. Table B moves to car / bicycle / pedestrian: data chain on cluster2 (4090-4119, export, Poisson, packs), a helma node job v2xreal-bike 1189833, then dm_push to helma and s32a-h (helma-ddp, Max gave the go 2026-10-31) with their own-name full-set evals (routine). Who submits s32a-h: ask develop or Max before launching.

2026-10-31 16:00: s24g full-set done (0.462 / 0.871 / 0.072). Develop c7fceb6/4b7c479: s32 series is V2X-Real-only (no Waymo init); v2b/slurm/helma-s32-chain.sh runs trainings + their full-set evals + s33/s34 zero-shot evals itself, so do not submit evals for s32/s33/s34. Bike shards packed on helma 16:13 (1189833).

2026-11-01 (develop b086728): the near-zero V2X-Real bicycle AP is not a bug in the data but a size-class artefact: heal_data.box_classes classes boxes by anchor footprint, not obj_type, so the V2X-Real "bicycle" set is mostly oversized pedestrians and parked motorcycles and scooter riders count as pedestrians. Report V2X-Real as car + pedestrian (riders included), mAP over two classes; do not flag the bicycle column as an open problem.

## 2q. Fusion-fix batch S37, S24h, S38, S26f (develop f6ce5fe / 9fcf404, from 2026-11-02 00:45, Max's go)

helma: s37a-h trainings 1196833/35/37/39/41/43/45/47 with their own evals 1196834-48 (even), s24h 1196849 + eval 1196850, s38a-c eval-only 1196851/53/54, s26f eval 1196855 (done). Every training here carries its own chained eval: submit none. s37a-c HEAL + AttFuse/F-Cooper/V2X-ViT on the augmented fused frame, s37d-f ours the same, s37g ours AttFuse frozen trunk, s37h ours AttFuse proj_first without augmentation; compare s37 against s32b-d / s32f-h. s38a-c rescore s32a/i/e on the union labels. s24h = raw-floor twin of s24e. Max asked (2026-11-02 00:44) for ticks every full hour for at least 24 h, until this batch is done.

2026-11-02 01:00: develop added the s39 truck chain (cda313b): s39a-i car / truck / pedestrian on V2X-Real V2V from s32p/s32q, trainings 1197362-70, own evals 1197371-79 (submit none), scoreboard Table B2. s38a-c done (union labels). s26f done.

## 3. Full-set evaluation of a finished training (routine)

Score under the run's **own** name so the run dir holds the checkpoint:

    EXTRA_ARGS='--eval-only --ap-samples -1' sbatch --job-name=eval-<run> v2b/slurm/<site>.sbatch configs/<run>.yaml <run>

The log then notes `eval of the run's checkpoint at epoch N` and `outputs/<run>/eval.json` is written. The handover's `<run>-eval` name does **not** work: `outputs/<run>-eval` has no checkpoint, so `--eval-only` falls back to the spec's `init_from` (s8e) and scores the baseline. That is what job 3050 did; the scoreboard's `s11f2-...-synth2-eval` row is s8e, not s11f2. Before recording any eval, check the `note :` line names the run's own checkpoint. Never start a job while another job of the same spec runs: both use `resources/data/generated/mixtures/<spec>-{train,val}`, and the newcomer rebuilds it under the running job (job 3069 died that way when 3070 started).

## 4. Rules

The scoreboard opens with **Main results** (8f89108): the paper's quantitative tables, Waymo (baselines, then ours step by step against s8e) and V2X-Real (each fusion as published, then on our agent). Rows are the `MAIN_WAYMO` / `MAIN_V2XREAL` lists in `v2b-scoreboard.py`; when a new best or a final run lands, add it there (a code change, audited) rather than relying on the best table.

Times on the scoreboard page and in tick headlines are GMT+1 (Max, 2026-10-25); the snapshots keep `collected_utc` in UTC and the page converts (30c2aa1). Ticks land on the full GMT+1 hour.

Progress log `.docs/progress.md`.

## 5. Queue commands

cluster2: `squeue -u max -o "%.6i %.40j %.8T %.10M %R"`. helma: `squeue -u $USER -o "%.9i %.9P %.28j %.2t %.10M %.6D %R"`.

**Table X and the S32 chain (2026-10-31):** every V2X-Real row of Table B and the transfer Table X comes from the s32 series (V2X-Real V2V only, bicycle as the third class, helma-s32-chain.sh, resubmitted as 1190102-1190127 after a catalogue fix) plus the CooPre V2V checkpoint zero-shot evals 1190101 (Waymo, rerun) / 1190013 (V2B, done). All evals run on helma while cluster2 has no memory (a colleague holds 250 GB until 2026-11-02); the cluster2 jobs 4090-4119 are the same bike export for the NAS and may stay queued. The old V2X-Real rows (s10, s20, s25, s27, s30, s31) rest on labels with a doubled ego yaw (fixed in 9e5b903) and are not paper material.

**CooPre Waymo fine-tune (2026-10-31 23:10):** 1186147-51 cancelled on Max's go, resubmitted as 1191335-37 (three resume segments) + eval 1191338 with the loader fix 612798f (one thread per worker); expect about 34 min per epoch again.

**Table X2 (WOD based, 2026-11-01):** the Waymo-only checkpoints scored zero-shot on V2X-Real V2V (s35a-c, jobs 1193170-72) and V2B (s36a-c, 1193173-75), plus the CooPre Waymo checkpoint through its own evaluator on the same two sets (run-dir copies coopre-waymo-ft-pre-v2xreal 1193176 and -v2b 1193177). All eval-only on helma, submitted by v2b/slurm/helma-s35-wod-transfer.sh; their rows read "missing" in Table X2 until eval.json lands, then collect + render + republish as usual. Nothing to resubmit on failure without the develop chat; report it.

2026-11-02 (develop): the fusion fix batch goes through v2b/slurm/helma-s37-fusion-fix.sh, which submits the trainings s37a-h and s24h with their own full-set evals plus the eval-only rows s38a-c and s26f, so do not submit evals for s37 / s38 / s24h / s26f. Rows land in Table B (s37, s38), Table A (s24g, s24h) and Table C (s26f) and get "new" boxes as usual. On V2X-Real the bicycle column is n/a by design (Table B's note); do not read it as a missing result.
2026-11-02 01:45 CET: fusion-fix batch submitted on helma: s37a 1196833 (eval 1196834), s37b 1196835 (1196836), s37c 1196837 (1196838), s37d 1196839 (1196840), s37e 1196841 (1196842), s37f 1196843 (1196844), s37g 1196845 (1196846), s37h 1196847 (1196848), s24h 1196849 (1196850); eval-only s38a 1196851, s38b 1196853, s38c 1196854, s26f 1196855. Trainings 1 to 2 h each on 4 H100 once they start; the evals follow by dependency.
2026-11-02 02:40 CET: s39 truck-class V2V chain submitted on helma (v2b/slurm/helma-s39-truck-chain.sh, the s32 series with car / truck / pedestrian, Table B2): s39a 1197362, s39e 1197363, s39i 1197364, s39b 1197365, s39c 1197366, s39d 1197367, s39f 1197368, s39g 1197369, s39h 1197370; evals 1197371-79 (s39a-i in order) by dependency, so do not submit evals for s39. The s37/s38/s24h batch is still queued.
2026-11-02 06:00 CET (develop): the fusion-fix batch (s37a-h, s24h, s38a-c, s26f) is done and on the board (version 1793595926-c14a). The s39 truck series trains on the pre-fix yaw labels (notes section 19): its rows stay on the board in Table B2 as a superseded group, do not read their car numbers as results. Corrected export job 1198089 (v2xreal-truck, ~2 h) on helma, then the s40a-i series through v2b/slurm/helma-s40-truck-chain.sh once Max gives the go; s40 trainings carry their own evals, submit none. Leave the running s39 jobs alone.

2026-11-02 23:30 CET (develop): s41a-c (LitePT-S as the m1 encoder on the raw / grid / Poisson floors, notes section 21) are prepared, launcher v2b/slurm/helma-s41-litept-chain.sh, not launched, needs Max's go; each training carries its own full-set eval, submit none. Controls are the s15 max-pooling rows. The s40 chain is still waiting for Max's go too; helma queue empty.
2026-11-03 (develop): on Max's go both chains submitted on helma. s40 truck series (corrected yaws, Table B2 replaces the s39 group): s40a 1204953, s40e 1204954, s40i 1204955, s40b 1204956, s40c 1204957, s40d 1204958, s40f 1204959, s40g 1204960, s40h 1204961; evals 1204962-70 (s40a-i in order) by dependency. s41 LitePT series (Table with the s15 max-pooling controls): s41a 1204971, s41b 1204972, s41c 1204973; evals 1204974-76 by dependency. Submit no evals for s40 / s41; rows read "missing" until eval.json lands. Expect s41 steps ~6x the pillar trunk (notes section 21), so 20 epochs take several hours per run.
2026-11-03 (Max): tick notes are committed once a day, not every tick (run-monitoring defaults.md step 6): append to progress.md as before, commit at the first tick after midnight as `docs: <date> ticks`; idle ticks append nothing. Launches, finished runs and failures may be committed when they happen.
2026-11-03 09:20 (develop): the queue table now has a "what" column (token meanings of the run name, tooltip = the spec's first sentence) and the full spec description in every job's detail row, also for jobs without a scored row (commit 220315d, the render script in the repo; no change to the tick routine). Local main was rebased to one tick commit per day; Max force-pushes it himself, helma then needs `git fetch && git reset --hard origin/main`. Until that push, do not pull or push from this checkout.
2026-11-03 09:50 (develop): new paper table E "Encoder-agnostic floor re-base" (commit 5816e70): s15 max-raw, s15 max-poisson, s41a, s41c, Poisson rows with their change to the raw row of their own encoder, raw LitePT with its change to raw pillars. Plot scope paper/e comes with it. The s41 full-set evals (1204974-76) were still running at 09:20; their rows fill in once eval.json lands, the s41b grid row stays in the S15-style tables only.
2026-11-03 11:20 (develop): Table E rebuilt as Table D's lever chain on both encoders with params and ms columns; the s41a/b/c and s15 max-poisson run files are on the NAS under v2b-outputs now (config, eval.json, bestval), so the cluster2 collector picks them up; every Table E row has a fresh capabilities.json from the idle local 4090 (old cluster2 files kept as capabilities-cluster2.json). s42a-c (LitePT levers: attention pooling, pretraining, fine-tune) prepared, launcher v2b/slurm/helma-s42-litept-levers-chain.sh, not launched, needs Max's go; s42a and s42c carry their evals, s42b is a pretraining run with no eval, submit none.
2026-11-03 12:10 (develop): s42 chain submitted on helma on Max's go: s42a 1208940 (eval 1208943), s42b 1208941 (pretraining, no eval, bestval = lowest val/loss), s42c 1208942 afterok s42b (eval 1208944). Submit no evals for s42. helma's checkout is on branch deploy-main at origin/main 655d3aa (its old local main at a791faf was left in place; Max may reset it); pull on helma with `git pull --ff-only` on that branch.

2026-11-04 (develop): s43a-heal-m1-v2xreal-v2v-proto-attn-poisson-truckz on helma, job 1215060 (helma-ddp.sbatch, 20 epochs, about 4 h) with its full-set eval 1215061 afterok; a main training, no further eval to submit. The truck anchor centred at -0.45 m (per-class anchor z, 87c7c55); control s40e, read truck AP@0.5 against .227 (car .897, ped .443). Row in Table B2 under s40i. helma deploy-main at 87c7c55 = origin/main. The s42 chain finished (s42a ped .538 / car .861, s42c .555 / .880); s42a and s42c still need their run files on the NAS and a local 4090 timing for Table E's cost columns.

2026-11-04 (develop, later): s43a done (truck .283 vs s40e .227 at IoU 0.5, car / ped unchanged); run files on the NAS, its Table B2 row filled. Table D has the cost columns (5b83efc); the run files of s24g, s21c, s24d, s42a, s42c were copied from helma to the NAS and timed locally (capabilities.json; earlier files kept as capabilities-before-2026-11-04.json). Capabilities timing needs `V2B_FORK=heal` in the environment. fit_ground is batched (fa87889), same field, 14 ms per sweep.
