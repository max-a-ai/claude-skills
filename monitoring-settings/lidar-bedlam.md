---
project: lidar-bedlam
repo: https://github.com/max-a-ai/lidar-bedlam
local: ~/Documents/lidar-bedlam
cluster: helma
status: active
updated: 2026-10-15
---

# Monitoring setting — lidar-bedlam

Converted on 2026-10-15 from the project's `monitor_handoff.md`, which is now a
pointer to this file. Earlier history: `git log -- monitor_handoff.md` in the
project repo.

## 0. Ground set — not repeated here

The invariant rules live in the skills and are assumed, never copied:

- `tick-it` — one pass: full-hour headline, labelled rows, verbatim queue block,
  collect in one backgrounded call, a sentinel on every remote probe, republish
  the artifact in place, leave the jobs alone.
- `run-monitoring` — the setup: this file is the single source of truth, `CronCreate`
  drives the tick (a Monitor dies at 30 minutes), one HTML scoreboard republished
  in place.
- `general-codebase` — any script written for this routine must pass it.

If something below contradicts a skill, the skill wins and this file is wrong;
fix it here in the same change.

## 1. Where things are

| | |
|---|---|
| online repo | https://github.com/max-a-ai/lidar-bedlam |
| local workspace | `~/Documents/lidar-bedlam` |
| cluster | `ssh -4 helma` (alias `lidar-bedlam` → `/hnvme/workspace/v103fe17-lidar-bedlam`) |
| wandb | https://wandb.ai/erik_hm/lidar-bedlam |
| scoreboard artifact | https://claude.ai/artifact/WAL7pLwJJYqjs4KKvUBtnK |
| run outputs | `outputs/<run>-000/` — `metrics.jsonl`, `val_*.json`, `DONE` |
| slurm logs | `outputs/slurm-<run>-*.out` |
| local mirror | `outputs/helma/runs/<run>/`, evals in `outputs/helma/eval/<run>-last.json` |

`ssh -4 helma` is flaky: retry up to four times with a short sleep, and treat a
dead hop as unknown rather than as an empty queue. `ssh helma sq` fails —
`.bash_aliases` is not read by a non-interactive shell, so send
`squeue -u $USER`.

## 2. Main trainings — the default bucket

**Any run not listed in section 3, 4 or 5 is a main training.** On DONE a main
training gets the full-set eval (section 6).

| run | what | on DONE |
|---|---|---|
| `m-boxhead` / `m-nobox` / `m-boxhead-kp` / `m-gate-none` / `m-chamfer` / `m-prior` (-000) | jobs 880923-880928; the six 15k mains under the box fix on one split (`configs/m_*.yaml`); resumable with `RUN_NAME=<run>` and `EXTRA_SET="optim.max_steps=N"` | val plots only; report Waymo MPJPE, transl, mAP |
| `m-boxhead-v3-000` | job 883008; run 7: box head on pseudo-GT v3 labels (`real/v1_pseudo3`, fitter with hip-centre term + joint offsets), same split as the six mains | val plots only; compare with `m-boxhead-000` and `m-boxhead-kp-000` |
| `b-full-mix80-000` | finished and fully evaluated | — |

All six m-series mains and `m-boxhead-v3-000` finished on 2026-09-22.
**`m-boxhead-kp-000` (keypoints only) wins Waymo at 59.8 mm**, with
`m-boxhead-v3-000` at 60.3 mm.

## 3. Ablation studies

| run | what | on DONE |
|---|---|---|
| `b-ratio-90/80/70/60-000` | ratio runs, corrected pseudo-GT v2 labels, full schedule | full-set eval |
| `b-ratio-90/80/70/60-001`, `b-ratio-50-000` | ablation 8 rerun under the box fix (`8df62e5`: box size term dropped on Waymo rows); 50/50 is new (jobs 874734-874738) | full-set eval |

Every `b-ratio-*-000` early-stopped at step 80000 = `min_steps`; evals verified
at that step.

## 4. Debug and realism experiments

Board group "Debug". These answer a question, they are not candidates — on DONE
they get **no eval job**, only the val plots.

| run | what | report |
|---|---|---|
| `d-token-prior-kp` / `d-token-prior-v3` / `d-token-head-kp` / `d-token-head-v3` (-000) | jobs 883044 (prior chain) and 883045 (head chain); token-manifold prior (option 1) and token pose head (option 2), each on keypoints-only and on pseudo-GT v3; two chained jobs (`CONFIGS=` in `train.sbatch`) | Waymo MPJPE, transl, mAP and hands |
| `d-bev-dummy-000` | job 1022051, 2026-10-15; dummy of the BEV route (`8c60386`): the person's returns go through HEAL's frozen PointPillars (OPV2V checkpoint, `body_models/heal_pointpillars.pth`) to a 256-channel BEV map, the 4x4 cells around the person feed the usual SMPL heads; no image; `configs/d_bev_dummy.yaml`, 5k steps, batch 1024, v3 labels, main split | Waymo / SLOPER4D / 3DPW MPJPE against `m-boxhead-v3-000`; a BEV-only trunk is expected to lose on limbs |

`d-bev-dummy-000` finished its 5000 steps: Waymo 224.2 mm / transl 0.128 / mAP
0.279, SLOPER4D 148.4, 3DPW 212.7, against 60.3 / 0.074 / 0.637 / 47.3 / 48.9
for `m-boxhead-v3-000`. Waymo `pve` came back NaN.

## 5. Short tests

Nine to fifteen thousand steps, hand-artefact questions. No eval job ever.

| run | what | report |
|---|---|---|
| `t-short-real-000` | 9k-step hand test, real Waymo returns | val plots only |
| `t-short-simlidar-000` | 9k-step hand test, Waymo returns simulated on the pseudo-GT mesh | val plots only; also logs `waymo_val_sim` |
| `t-short-boxhead-000` | 15k-step test of the padded box head (`d473c55`): the Waymo box loss trains a residual head on the detached mesh box; mixture 75 % BEDLAM + all real | Waymo wrist bend, transl, mAP together |
| `t-short-nobox-000` | 9k-step hand test, `t_short_real` recipe with `loss.box3d=0` (Waymo box labels are padded 0.9 x 1.0 m, the mesh box is 0.6 x 0.6 m; suspected cause of the bent hands) | Waymo wrist bend |

Both `t-short-*` finished at step 9000. They are the block-0 prerequisite of
`.docs/retrain_schedule.md`: **nothing beyond them starts until the Waymo hand
problem is settled.**

## 6. Evaluation parameters

Validation sources, in report order: `waymo_val`, `sloper4d_test`,
`threedpw_test`, `bedlam`.

Metrics per source: `mpjpe`, `pa_mpjpe`, `abs_mpjpe`, `pve`, `transl_err`,
`map`, `mean_iou`. The three that are quoted in a tick are **Waymo MPJPE (mm),
`transl_err` (m), `map`** — pose, placement and detection, because on this
project they have come apart before (the v2-label runs held MPJPE and lost
placement).

Full-set eval, for mains and ablations only. `RUNS` must be space-separated and
quoted; commas evaluate only the first run:

    ssh -4 helma 'cd /hnvme/workspace/v103fe17-lidar-bedlam && sbatch --export=ALL,FORCE=1,RUNS="<run>" lidar_bedlam/slurm/eval_runs.sbatch'

Check the `step` field in `outputs/helma/eval/<run>-last.json` is the run's final
step before trusting a scoreboard row.

Arrow thresholds (errors, so **down is good**): `⇘` ≤ −3 %, `↘` −3 … −0.5 %,
`→` ±0.5 %, `↗` +0.5 … +3 %, `⇗` ≥ +3 %. Calibrated here: consecutive
evaluations of the b-ratio runs swing about ±4 % on Waymo MPJPE, so ±0.5 % is
genuinely flat and past 3 % outruns the noise. A lone `⇗` is not a regression;
if the arrows flap, rerun with `--smooth 3`. Change `STRONG`, `WEAK` or
`EVAL_OVERHEAD_S` at the top of `running_table.py`, and note it here.

**If this section is missing from a setting**, fill it from the newest run's
`config.json`: every `val/<source>/<metric>` key present in its `metrics.jsonl`
becomes a source and metric, the first source is the headline, and no eval job
is submitted until the user confirms.

## 7. Specified wishes

What this user asked for on this project, beyond the ground set:

- Ticks land on the **full clock hour** (2026-09-21). The headline is the hour,
  never the minute the scheduler fired.
- The report is **labelled markdown rows, not a code block** (2026-09-21), with
  live links, and the scoreboard as a clickable row of its own.
- The queue block is **verbatim**: no added column, no filtered row, no prose
  inside it. An empty queue is the header line alone. Run-name mapping goes in
  the interpretation.
- **This session monitors.** Ask before using it for anything else
  (2026-09-22); running the tick, submitting an eval for a finished run and
  editing this file need no question.
- Deltas, not absolutes. One line if nothing changed.
- `--out` writes the **compact interactive page**; `--classic` is only on request.

## 8. The hourly routine

From the project root, `S` = the session scratchpad:

    for i in 1 2 3 4; do bash lidar_bedlam/scripts/pull_helma_results.sh >$S/pull.log 2>&1 && break; sleep 20; done
    RUNS=$(ssh -4 helma 'cd /hnvme/workspace/v103fe17-lidar-bedlam && ls -d outputs/[btavmd]*-[0-9][0-9][0-9] outputs/v2-*-[0-9][0-9][0-9] 2>/dev/null | xargs -n1 basename')
    for r in $RUNS; do mkdir -p outputs/helma/runs/$r; rsync -4 -az helma:/hnvme/workspace/v103fe17-lidar-bedlam/outputs/$r/metrics.jsonl outputs/helma/runs/$r/; done
    find outputs/helma/runs -type d -empty -delete
    ssh -4 helma 'bash -s' < lidar_bedlam/slurm/capture_squeue.sh > $S/squeue.txt   # appends RUN <jobid> <run-name>
    .venv/bin/python lidar_bedlam/scripts/running_table.py --squeue-file $S/squeue.txt --update monitor_handoff.md
    uv run python lidar_bedlam/scripts/build_scoreboard.py --stamp "$(date '+%Y-%m-%d %H:%M')" --out $S/scoreboard.html --schedule-md .docs/retrain_schedule.md --squeue-file $S/squeue.txt

Plus, each tick: the DONE-marker check (a finished run with no
`outputs/eval/<run>-last.json`) and a traceback grep over the 30 newest slurm
logs. Both need a sentinel, both have failed as a dead hop and been misread as
"all clear".

`uv run` exits 120 without a TTY; call `.venv/bin/python` directly if that
happens. `pull_helma_results.sh` does not pick up `b-*` or `t-*`, hence the
explicit rsync — add new prefixes to that list as they start. The glob
`[btavmd]*` is what makes `d-*` runs visible; widen it for a new letter.

The live running table is regenerated into the project's `monitor_handoff.md`
between its `RUNNING` markers — never hand-edited, and deliberately kept out of
this file so that an hourly rewrite does not churn the skills repo.

## 9. The scoreboard

`lidar_bedlam/scripts/build_scoreboard.py` is the only source of the page.
`--out` writes the compact interactive page (`pocket_board.py`: one metric at a
time, groups fold, a tapped row shows every metric plus sparklines, the wide
table switches on by itself from 800 px). `--classic <path>` writes the old
static wide page. Same loaders, identical numbers.

Layout: headline table (mains against the published pipelines), "Main runs",
ablations 1, 2, 3, 4, 5, 7, 8, and the Debug group. Ablation 6 and every
camera-frame / 50-40-10 run were removed on 2026-09-18 — **do not add them
back.** First column "pseudo-GT" is derived from each run's `config.json`
(`WAYMO_LABEL_DIRS` maps the Waymo training source to v2 / v1 / lhmr / pedgen;
`real/v1` = keypoints only = red cross); runs without a `config.json` show an
empty cell. Runs in the `RETRAIN` dict render grey, keep their numbers, are
excluded from the best/second/third colours and show a reason — to grey or
ungrey a row, edit `RETRAIN`, never the HTML. The `SCHEDULE` list renders the
"Retraining schedule" table and `--schedule-md` writes it to
`.docs/retrain_schedule.md`. `a-full-mix80-000` closes every ablation table as
the reference.

Publishing: pass `url` set to the artifact above and a label `Hourly tick HH:00`.
Publishing without `url` creates a separate artifact, which is wrong. On a
refusal because another session published a newer version, read the artifact and
publish once more — never force.

## 10. Known traps

**wandb mirror, a run without images.** The login-node mirror hit NFS "Stale
file handle" on 2026-09-22 and uploaded `m-boxhead-v3-000` without its
`image/val_plot_*` rows (PNGs present, history rows absent). Fix: delete the
wandb run, pull `outputs/<run>/{metrics.jsonl,config.json,DONE,vis/}` into
`outputs/helma/runs/<run>/`, drop its `.mirror_offset`/`.mirror_id`, re-mirror
from a scratch root that symlinks only that run:

    WANDB_MIRROR_DIR=$S/remirror/wandb .venv/bin/python lidar_bedlam/scripts/wandb_mirror.py --root $S/remirror --once

The re-mirrored run gets a `-m<digits>` id suffix; the name stays. Confirm with
the wandb API that `scan_history(keys=["image/val_plot_waymo_val"])` returns one
row per evaluation before telling the user it is fixed.

**Code reaches Helma by git, never rsync** (2026-09-18). The workspace was once
an rsync copy over a stale checkout, 150 commits behind on `1429370`, live code
untracked, every pull failing on "untracked working tree files would be
overwritten". It is now a clean checkout of `origin/main`. Claude pushes only
after the user's explicit go in the chat, then pulls on Helma and confirms:

    ssh -4 helma 'cd /hnvme/workspace/v103fe17-lidar-bedlam && git pull --ff-only'
    ssh -4 helma 'cd /hnvme/workspace/v103fe17-lidar-bedlam && git log --oneline -1 && git status -sb | head -1'

Helma's HEAD must equal local `origin/main` with no divergence; report both
hashes. If the pull refuses, stop and tell the user — never clear the way with
`checkout -f`, `reset --hard`, `restore`, `clean`, `rm` or `mv`. A pull also
brings `pyproject.toml` and `uv.lock`: compute nodes have no internet, so a
changed lock makes `uv run` try to install. New shard directories go to
`resources/data/generated/<dir>` on Helma (npz only) with `.tokens.npy`
sidecars hard-linked from `real/v1`; add the directory to `STAGE_DIRS` when
submitting.

**A Monitor cannot drive an hourly loop.** Whatever `timeout_ms` or
`persistent` is passed, the harness expires it after 30 minutes, so a script
that sleeps 3600 s between passes emits one event on arming and dies before the
second. `CronCreate` is session-only, auto-expires after 7 days firing once
more, and fires only while the session is idle. The `schedule` skill is wrong
for this: it creates cloud agents, which have neither this repo nor SSH.

## 11. Not monitored

- `notebooks/003-bedlam-v1-vs-v2.ipynb` (cell bodies in
  `notebooks/ipynb-assets/nb003_bedlam_v1_vs_v2.py`) compares the two BEDLAM
  releases from the NAS copies, caching under `outputs/bedlam2_cache`. No
  cluster side, nothing for a tick.
- The bike nuScenes data question: `data_inspection_handoff.md`, worked in its
  own session.

## 12. Standing rules (hooks enforce them)

- Claude pushes only after an explicit go in the chat; force pushes blocked.
  Commits are one line, `<prefix>: <description>`, one `-m`, ≤ 72 characters,
  lowercase after the colon, prefix in
  add|bug|minor|refactor|docs|test|config|remove.
- Never launch a training without `--wandb-project` and `--wandb-name`
  (`train.sbatch` sets them). Never train on the workstation. **Do not launch,
  restart, resubmit or cancel a Helma job without the user's word** — the
  schedule of what comes next is `.docs/retrain_schedule.md`.
- After any Python or config edit run the `general-codebase` audit, then
  `~/.claude/hooks/mark_audited.sh`.
- Keep this file current: any change to the routine, the builder's options or
  the artifact rules is written here in the same change.
