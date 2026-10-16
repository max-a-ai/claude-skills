---
project: v2b
repo: https://github.com/max-a-ai/v2b
local: ~/Documents/v2b
cluster: helma (this routine), cluster2 (watched by the bev-v2b-monitoring chat)
status: active
updated: 2026-10-16
---

# Monitoring setting — v2b, Waymo to helma pipeline

Drafted 2026-10-16 15:40 from the user's instruction "pack it up and send
it over, tick it every 1 hour to give me the progress, start on helma as
soon as ready". The cluster2 stage-1 runs (s8a, s8b, s8c) are the
bev-v2b-monitoring chat's business and are not reported here.

## 0. Ground set — not repeated here

`tick-it` owns the pass and the layout, `run-monitoring` the setup,
`general-codebase` any script. If this file contradicts a skill, the
skill wins.

## 1. Where things are

| | |
|---|---|
| online repo | https://github.com/max-a-ai/v2b |
| local workspace | `~/Documents/v2b` |
| cluster2 (export + packing) | `ssh cluster2`, checkout `~/v2b`, NAS `/mnt/nas/methods/max/v2b-derived/waymo`, shards `/mnt/nas/methods/max/v2b-packed/waymo-opv2v` |
| helma (training) | `ssh helma`, checkout `/home/hpc/v103fe/v103fe17/v2b`, workspace `/hnvme/workspace/v103fe17-bev-v2b/shards/<dataset>` (expires 2026-10-17 15:29 unless extended) |
| wandb | https://wandb.ai/erik_hm/v2b |
| scoreboard artifact | none; text ticks in the chat |
| run outputs on helma | `outputs/<run>/` with `net_epoch*.pth`, logs `outputs/logs/v2b-<job>.out` |

## 2. The pipeline being ticked, in order

1. Waymo export on cluster2: `logs/waymo-{validate,train}-<i>.log`, done when every log ends in a `{"frames": ...}` summary and `export-<i>of<n>.json` exists in the split folder.
2. Packing on cluster2: `v2b/scripts/dm_pack.py waymo-opv2v --out /mnt/nas/methods/max/v2b-packed/waymo-opv2v --only '*.pcd' '*.yaml' 'export*.json'` (LiDAR-only shards for the m1 run).
3. Push from the workstation: `v2b/scripts/dm_push.sh waymo-opv2v helma /hnvme/workspace/v103fe17-bev-v2b`, verified by `sha256sum -c`.
4. HEAL env on helma: `outputs/logs/helma-bootstrap.log` ends in `HEAL-ENV-DONE`.
5. Job on helma: `sbatch v2b/slurm/helma.sbatch configs/s8e-heal-m1-waymo-3cls-init.yaml s8e-heal-m1-waymo-3cls-init` from the checkout, submitted by this chat once 3 and 4 hold (the user's word: "start on helma as soon as ready"). Resume across the 24 h limit with `RESUME=1 sbatch ...` (also pre-authorised by that instruction).

## 2b. State 2026-10-16 17:22

Export done 16:32 (8 069 validate / 31 880 train frames). Shards packed on cluster2 (validate 15.3 GB, train 60.4 GB, LiDAR-only) and verified on helma under `shards/waymo-opv2v/{validate,train}`. HEAL env done. **Job 1036386** (`s8e-heal-m1-waymo-3cls-init`) submitted 17:22, pending on priority. Workspace still at 22 h / 3 extensions, user asked to `ws_extend bev-v2b 90`.

## 3. Mains and ablations

Main: `s8e-heal-m1-waymo-3cls-init` (20 epochs, eval every epoch, AP@0.5 per class in the log and wandb). Later: `s8f-heal-m1-nusc-av2-waymo-3cls` needs nuScenes and Argoverse shards first.

## 4. Queue command

`squeue -u $USER -o "%.9i %.9P %.28j %.2t %.10M %.6D %R"` on helma (no alias in non-interactive ssh).
