---
name: data-management
description: >
  Training data, checkpoints and environments across the NAS, the lab boxes
  and the NHR clusters. Use when moving a dataset to Helma or Alex, packing a
  dataset into shards, wiring up data/ on any machine, building a smoke
  subset, checking whether a workspace is about to expire, or when a job
  cannot find its data. Hard rule: the NAS is read-only, the clusters hold
  only shards.
---

# data-management

**Treat the NAS as read-only. The clusters hold only shards.**

The workspaces on Helma (`/hnvme`) and Alex (`/anvme`) are **inode-bound** —
roughly 50k files per user across *all* workspaces, with volume effectively
free. An unpacked image dataset is 10^5–10^7 files, so it cannot live there
at all, and NHR@FAU prescribe the same fix: archives, unpacked into `$TMPDIR`
at job start. Numbers, node specs, transfer rules and sources:
[reference/nhr-facts.md](reference/nhr-facts.md).

## Where things live

| | workstation (`mbwm`) | `cluster1` / `cluster2` | Helma / Alex |
|---|---|---|---|
| `data/<ds>` | symlink → NAS | real copy | `.tar.zst` shards |
| `checkpoints/` | symlink → NAS | symlink → NAS | real copy |
| `outputs/` | real | real | real |
| environment | uv `.venv` in repo | uv `.venv` in repo | `$HOME`, or Apptainer |
| `data/_smoke/` | built | built | — (smoke runs are local) |

On Helma and Alex **the repo root is the workspace root** — clone into
`$(ws_find <repo>)`. That keeps the tree identical everywhere, so moving a run
between machines changes only `DATA_ROOT`. The tree itself is owned by
[[general-codebase-structure]].

## The scripts

Copied into the repo's `scripts/`, so the version used for a run is committed
beside it. Stdlib Python 3 and bash, because they run on login nodes with no
venv. Each script's `--help` is the source of truth for its flags.

| Script | Runs on | Does |
|---|---|---|
| `dm_status.sh` | Helma / Alex | days **and extensions** left, per workspace |
| `dm_pack.py` | workstation | dataset → 24 `.tar.zst` shards + manifest + checksums |
| `dm_push.sh` | workstation | rsync shards to a workspace, verify checksums remotely |
| `dm_link.py` | any | materialise `data/`, `checkpoints/`, `outputs/`, `.gitignore`, smoke subset |
| `dm_alias.sh` | any | `cd<repo>` aliases as one rewritable block in `~/.bash_aliases` |

## Workspaces: check first, allocate never

Start every data action with `dm_status.sh`. A workspace is deleted when its
time runs out, and extensions are finite — `available extensions : 3` means
three more `ws_extend` calls, ever. When they are gone, the data goes with
them. Recovery is a fresh workspace plus a re-push from the NAS, which works
only because the NAS is read-only: that rule is load-bearing, not tidiness.

Resolve targets with `ws_find`. When one is missing, stop and print the
command for the user to run — a guessed name burns a scarce extension or
writes terabytes into the wrong filesystem:

```bash
ws_allocate <name> 90 -r 7 -m <your-email>    # 90 = the documented maximum
```

## What the scripts already get right

Cached here because the reasons are invisible in the code, and each one was a
real bug in the predecessor scripts:

- **Shards are assigned by `blake2b(relative_path) % 24`, not `split -l`.**
  Under a sequential split, one file added at the front reshuffles every shard
  and forces a full repack. `split -l` also produced an N+1'th chunk whenever
  the file count was not a multiple of N, and those files were silently never
  archived.
- **Deletions stop the packer.** Files vanishing from a read-only NAS mean a
  half-mounted share; `--allow-deletions` is the deliberate override.
- **`.tar.zst`, with paths relative to the dataset root.** gzip is
  single-threaded and buys nothing on JPEGs; relative paths make extraction a
  single `tar -xf … -C $TMPDIR` with no intermediate copy.
- **Transfers run uncompressed.** The payload is already zstd, and NHR warn
  that `-z` can make their transfers slower.
- **24 shards** matches the 32 cores a 1-GPU Helma job receives.

## Smoke subsets

A smoke run catches a broken loader in minutes. `dm_link.py --smoke` builds
`data/_smoke/` from the `smoke` block of `config-global.json` — a
deterministic every-*k*-th sample, symlinked.

Default recipe: **90% synthetic, 10% real** (Waymo + SLOPER), reported as
**one metric per source**. Three separate curves is the point: a blended
metric hides the source whose loader broke.

Flip `DATA_ROOT` between `data/` and `data/_smoke/`; nothing else changes.

## Environments

A torch venv is 30k–60k files and would consume a whole workspace's inode
budget. On a cluster the environment lives in `$HOME` (~500k inodes, and
mounted on Helma GPU nodes where `$WORK` is not), or in an Apptainer `.sif` —
one file, one inode, and what NHR recommend.

**Guardrail: a `.venv` under `/hnvme/workspace` or `/anvme/workspace` is a
hard FAIL.** It starves every other workspace of inodes.

## The job side belongs to the sbatch script

Staging into `$TMPDIR` is the job's business (and eventually its own skill).
The shards extract in one step:

```bash
STORAGE_DIR="$(ws_find <repo>)"
find "$STORAGE_DIR/data/<dataset>" -name '*.tar.zst' \
  | xargs -P 24 -I{} tar -xf {} -C "$TMPDIR"
export DATA_ROOT="$TMPDIR"
```

`$TMPDIR` is shared between jobs on a node, so check capacity first; a
multi-node job stages once per node with `srun --ntasks-per-node=1`.

## Checklist

Every box ticked, with the command output that proves it:

- [ ] `dm_status.sh` — no workspace low on days or extensions
- [ ] dataset declared in `config-global.json` with its NAS path
- [ ] `dm_pack.py <dataset>` — shards + manifest + checksums on the NAS
- [ ] `dm_push.sh <dataset> <helma|alex>` — remote checksum verify passed
- [ ] `dm_link.py --check` on the target machine — exit 0
- [ ] `dm_alias.sh` — `cd<repo>` works in a new shell
- [ ] `find <workspace> -name .venv` — empty
- [ ] smoke run converges on all three metrics before the real run

Related: [[general-codebase-structure]] owns the tree and `config-global.json`;
[[wandb-training]] owns run names; [[general-codebase]] audits all of it.
