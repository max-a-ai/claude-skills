# NHR@FAU facts (Helma, Alex)

Sourced from the official docs. These are expensive lookups, cached here
because they decide the whole data-management design. Re-verify a number
before acting on it if the design hangs on it.

## Quotas

Workspaces are **inode-bound**, not volume-bound:

| Filesystem | Volume | Inodes (per user) |
|---|---|---|
| `/hnvme` (Helma), `/anvme` (Alex) | "only inodes" | **50k soft / 75k hard** |
| `$HOME` | 100 GB | ~500k soft / 1000k hard |
| `$HPCVAULT` | 1000 GB | ~200k / 400k |
| `$WORK` (atuin) | project quota | ~3000k / 3200k (per **group**) |
| `$TMPDIR` | no quota | — |

The workspace figure is per user **across all workspaces**, and comes from the
example output on the [workspace quota
page](https://doc.nhr.fau.de/data/workspaces/#quota) — check the live value
with `lfs quota /hnvme` or `lfs quota /anvme`.
[Filesystem overview](https://doc.nhr.fau.de/data/filesystems/#quotas).

**`$WORK` is not mounted on Helma GPU nodes** — only `$HOME`, hnvme
workspaces and `$TMPDIR` are.
[Helma filesystems](https://doc.nhr.fau.de/clusters/helma/#filesystems).

## Node-local scratch

`$TMPDIR` is a per-job directory on a node-local NVMe SSD, created at job
start and removed at the end. Capacity is **15 TB** on Helma h100/h200 and
**14 TB** on Alex a100 — but it is shared between all jobs on the node, so
check before extracting. Undefined on frontend nodes (use `mktemp -d` there).
[Node-local `$TMPDIR`](https://doc.nhr.fau.de/data/filesystems/#node-local-job-specific-directory-tmpdir),
[staging patterns](https://doc.nhr.fau.de/data/staging/).

## Node hardware

| Cluster | Partition | Cores/node | GPUs/node | Cores per GPU |
|---|---|---|---|---|
| Helma | `h100` | 128 | 4 × H100 94 GB | 32 |
| Helma | `h200` | 128 | 4 × H200 141 GB (AI.BAY only) | 32 |
| Helma | `cpu` | 384 | — | — |
| Alex | `a40` | 128 | 8 × A40 48 GB | 16 |
| Alex | `a100` | 128 | 8 × A100 40 or 80 GB | 16 |
| Alex | `rtxpro6k` | 256 | 8 × RTX Pro 6000 96 GB | 32 |

**Alex has no H100 partition.** A `--gres=gpu:h100:1` script is Helma-only.
SMT is disabled on Helma. Helma's default partition is `preempt` (H100,
guaranteed 2 h then preemptible).
[Helma](https://doc.nhr.fau.de/clusters/helma/),
[Alex](https://doc.nhr.fau.de/clusters/alex/).

## Datasets: the documented pattern

> "keep them packed in an archive like tar or zip and only unpack them to
> `$TMPDIR` when your job starts"

[Datasets](https://doc.nhr.fau.de/data/datasets/#datasets-containing-massive-amounts-of-files).
This is exactly what `dm_pack.py` produces and what the sbatch script consumes.

## Environments: containers

> "It is suggested to wrap your python environment into a container, because
> the virtual environments usually contain large number of inodes, leading to
> massive problems on the file system."
> — [Apptainer](https://doc.nhr.fau.de/environment/apptainer/)

> "Due to restriction in inodes on Helma, it is highly recommended to use
> apptainer to run your jobs."
> — [Helma / Python & conda](https://doc.nhr.fau.de/clusters/helma/#python-conda-conda-environments)

Apptainer is available on all NHR@FAU systems and builds on the AlmaLinux
frontends (Helma, Alex, Fritz, Woody). Sandbox builds belong in `$TMPDIR` —
"In workspaces, the inodes are not sufficient and in `$HOME` it crowds the
space." Cache defaults to `$HOME/.apptainer/cache`; move it with
`$APPTAINER_CACHEDIR`. Not suited to multi-node MPI.

Documented fallbacks if containers are too big a change: move conda
`pkgs_dirs`/`envs_dirs` to `$WORK`, set `PYTHONUSERBASE`, or use the Spack
stack. **`conda-pack` and staging a packed environment to `$TMPDIR` are not
documented** — tarball staging is documented for datasets only, and venvs
carry absolute paths.

## Transfer

`csnhr.nhr.fau.de` is the dialog server and the SSH jump host to the cluster
frontends; `$HOME`, `$HPCVAULT` and `$WORK` are mounted there — **workspaces
are not**, and `ws_find` only runs on the Helma/Alex/Fritz frontends. So
target a frontend directly and let the existing `~/.ssh/config` ProxyJump
handle the hop.

rsync is the recommended tool for large or numerous files, with
`--append-verify` for resumable transfers. Compression is counterproductive
here: "Using compression `-z` when transferring files between NHR@FAU systems
might increase duration."
[Copying data](https://doc.nhr.fau.de/data/copying/#rsync),
[access overview](https://doc.nhr.fau.de/access/overview/#file-transfer).
