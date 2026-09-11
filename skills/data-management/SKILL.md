---
name: data-management
description: >
  Where training data, checkpoints and environments live on each machine,
  and how to get them there. Use when moving a dataset to Helma or Alex,
  allocating or checking an HPC workspace, packing data into archives for
  $TMPDIR, setting up data/ on a workstation or lab box, building a smoke
  subset, or when a job cannot find its data. Encodes the hard rule: the
  NAS is static, the cluster only ever sees archives.
---

# data-management

**Hard rule: the NAS is the single unpacked source of truth and nothing is
ever deleted from it. The clusters only ever see packed archives.**

This is not a preference. The NVMe Lustre workspaces on Helma (`/hnvme`) and
Alex (`/anvme`) are limited by **inodes, not volume** — roughly 50 000 soft /
75 000 hard **per user across all workspaces**
([quota docs](https://doc.nhr.fau.de/data/workspaces/#quota)). An unpacked
image dataset is 10^5–10^7 files and blows that budget on its own. NHR@FAU
prescribe the same fix:

> "keep them packed in an archive like tar or zip and only unpack them to
> `$TMPDIR` when your job starts"
> — [Datasets](https://doc.nhr.fau.de/data/datasets/#datasets-containing-massive-amounts-of-files)

## Where things live

| | workstation (`mbwm`) | `cluster1` / `cluster2` | Helma / Alex |
|---|---|---|---|
| `data/<ds>` | symlink → NAS | **real copy** | `.tar.zst` shards, never unpacked here |
| `checkpoints/` | symlink → NAS | symlink → NAS | **real copy** (small, no symlink target) |
| `outputs/` | real | real | real (workspace NVMe) |
| environment | uv `.venv` in repo | uv `.venv` in repo | `$HOME` or Apptainer — **never a workspace** |
| smoke subset | `data/_smoke/` | `data/_smoke/` | n/a (smoke tests run locally) |

On Helma and Alex **the repo root is the workspace root** — clone straight
into `$(ws_find <repo>)`. That is what makes the tree identical everywhere, so
a run only changes `DATA_ROOT`. The layout itself is owned by
[[general-codebase-structure]].

## The scripts

Copied into the target repo's `scripts/`, so the version used for a run is
committed next to it. Stdlib-only Python 3 and bash: they must work on a login
node with no venv.

| Script | Runs on | In | Out |
|---|---|---|---|
| `dm_status.sh` | Helma / Alex | — | every workspace's remaining days **and extensions**, flagging what is running out |
| `dm_pack.py` | workstation | a dataset declared in `config-global.json` | 24 `.tar.zst` shards + `manifest.tsv` + `sha256sums.txt` under `<nas>/_packed/<dataset>/` |
| `dm_push.sh` | workstation | a packed dataset + a target cluster | shards rsynced into `$(ws_find …)/data/<dataset>/`, checksums verified remotely |
| `dm_link.py` | any | `config-global.json` | `data/`, `checkpoints/`, `outputs/` materialised for **this** machine, `.gitignore` updated, `data/_smoke/` built |
| `dm_alias.sh` | any | `config-global.json` | an idempotent delimited block of `cd<repo>` aliases in `~/.bash_aliases` |

### Always run `dm_status.sh` first

A workspace is **deleted** when its time runs out, and extensions are finite —
`available extensions : 3` means three more `ws_extend` calls, ever. When they
are gone, no command saves the data. Recovery is: allocate a fresh workspace
under a new name and re-push from the NAS. That only works because the NAS
copy is never touched, which is why the static-NAS rule is load-bearing rather
than tidy.

### This skill never allocates a workspace

It resolves targets with `ws_find` and **stops** if one is missing, printing
the command for you to run:

```bash
ws_allocate <name> 90 -r 7 -m <your-email>   # 90 = the documented maximum
```

Allocating is the user's hand, not the agent's: a wrong guess burns a scarce
extension or writes terabytes into the wrong filesystem.

## Packing: 24 shards, hash-assigned, incrementally repacked

`dm_pack.py` assigns each file to a shard by `blake2b(relative_path) % 24`.
This matters more than it looks: with a sequential split (`split -l`, the
obvious approach) adding one file at the front reshuffles every shard and
forces a full repack. With a path hash, adding files touches only the shards
they land in.

`manifest.tsv` records `relpath / size / mtime / shard`. A re-run diffs the
live NAS tree against it and repacks only the dirty shards. `--all` forces a
full repack.

**Deletions are a hard stop.** Files vanishing from a static NAS almost always
means a half-mounted share, so the packer refuses rather than silently
shrinking your dataset; `--allow-deletions` overrides.

Format is `.tar.zst` (`zstd -T0 -3`, multithreaded), falling back to plain
`.tar` if `zstd` is absent. **Not** gzip: on JPEGs and pickles gzip is
single-threaded and buys almost nothing. Paths inside are relative to the
dataset root, so extraction is a single `tar -xf … -C $TMPDIR` with no
intermediate copy.

Why 24: a 1-GPU Helma job gets **32 cores** (h100 nodes are 128 cores / 4
GPUs), so 24 parallel extractions fit with headroom.

## Transfer

`dm_push.sh` runs `rsync -a --partial --append-verify` from the workstation to
`helma:` / `alex:`, which ProxyJump through `csnhr.nhr.fau.de` via the existing
`~/.ssh/config` entries. Then it verifies `sha256sums.txt` remotely and refuses
to report success until it passes.

**Never `rsync -z`** — the payload is already zstd, and NHR@FAU warn that
compression can make transfers between their systems *slower*
([rsync docs](https://doc.nhr.fau.de/data/copying/#rsync)). Workspaces are not
mounted on `csnhr` itself (`ws_find` only runs on the Helma/Alex/Fritz
frontends), so the transfer targets a frontend directly.

## Smoke subsets

A smoke run exists to catch a broken data-loading path in minutes, not to
train. `dm_link.py --smoke` builds `data/_smoke/<dataset>/` from the `smoke`
block in `config-global.json`: a deterministic every-*k*-th sample, symlinked,
reproducible.

Default recipe: **90% synthetic, 10% real** (Waymo + SLOPER mixed), evaluated
with **one metric per source** — synthetic, Waymo, SLOPER reported separately.
Three separate curves is the point: a single blended metric hides a source
whose loader is broken.

Flip `DATA_ROOT` between `data/` and `data/_smoke/`; nothing else changes.

## The job side is not this skill's job

Staging from the workspace into `$TMPDIR` belongs to the sbatch script (and
eventually its own skill). For reference, the archives this skill produces
extract in one step:

```bash
STORAGE_DIR="$(ws_find <repo>)"
find "$STORAGE_DIR/data/<dataset>" -name '*.tar.zst' \
  | xargs -P 24 -I{} tar -xf {} -C "$TMPDIR"
export DATA_ROOT="$TMPDIR"
```

`$TMPDIR` is node-local NVMe — 15 TB on Helma h100, 14 TB on Alex a100 — but
it is *shared between jobs on a node*, so check capacity before extracting.
Multi-node jobs need `srun --ntasks-per-node=1` to stage once per node.

## Environments: never a .venv in a workspace

A torch venv is 30 000–60 000 files and would consume the entire workspace
inode budget. `$HOME` has roughly a 500 000 inode budget and **is** mounted on
Helma GPU nodes (`$WORK` is not), so it is the accepted default. NHR@FAU
recommend going further:

> "Due to restriction in inodes on Helma, it is highly recommended to use
> apptainer to run your jobs."
> — [Helma](https://doc.nhr.fau.de/clusters/helma/#python-conda-conda-environments)

An Apptainer `.sif` is one file and one inode — the documented upgrade path.
Do **not** try to pack a venv as a tarball: it is undocumented and venvs carry
absolute paths.

## Checklist

- [ ] `dm_status.sh` — no workspace low on days or extensions
- [ ] dataset declared in `config-global.json` with its NAS path
- [ ] `dm_pack.py <dataset>` — shards + manifest + checksums on the NAS
- [ ] `dm_push.sh <dataset> <helma|alex>` — remote checksum verify passed
- [ ] `dm_link.py` on the target machine — exit 0
- [ ] `dm_alias.sh` — `cd<repo>` works in a new shell
- [ ] no `.venv/` anywhere under `/hnvme/workspace` or `/anvme/workspace`
- [ ] smoke run converges on all three metrics before the real run

Related: [[general-codebase-structure]] owns the tree and `config-global.json`;
[[wandb-training]] owns run names; [[general-codebase]] audits all of it.
