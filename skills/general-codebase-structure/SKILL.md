---
name: general-codebase-structure
description: >
  The canonical directory layout every repository must have, plus the audit
  that checks a repo against it. Use when starting a repo, when asked "is this
  repo laid out correctly", when deciding where a new file belongs, or when
  general-codebase runs its full audit. Owns the tree, config-global.json,
  .docs/ and progress.md; python-project-init writes what this skill defines.
---

# general-codebase-structure

**This skill is the contract, not the scaffolder.** It states the layout and
audits a repo against it. [[python-project-init]] *writes* the files; if the two
ever disagree, this skill wins and the initializer is wrong.

It is one of the checks [[general-codebase]] runs, alongside ruff, mypy and
wandb.

## The tree

```
<repo-name>/                     ← on Helma/Alex this IS the workspace root
│                                  (/hnvme/workspace/<user>-<repo-name>/)
├── pyproject.toml               uv + hatchling, ruff 79 cols, mypy strict
├── uv.lock
├── .python-version
├── config-global.json           datasets, checkpoints, methods, smoke recipe
├── .gitignore
├── README.md
├── HANDOFF.md
├── instructions.md              coding standards
│
├── src/<module>/                ALL main code. Nothing loose at the root.
│
├── third_party/                 methods from config-global.json: submodule,
│   └── <method>/                  clone or symlink to an existing checkout
│
├── configs/                     experiment yaml
├── scripts/                     dm_pack.py, dm_push.sh, dm_status.sh, dm_link.py
├── slurm/                       sbatch job scripts
├── tests/
│
├── data/          ┐ GITIGNORED, machine-dependent, built by [[data-management]]
├── checkpoints/   ├─
├── outputs/       ┘ one directory per run: outputs/<run-name>/
│
└── .docs/
    ├── progress.md              COMMITTED — the single source of truth
    ├── figures/                 curated images / lidar renders
    ├── latex-draft/             empty, ready for a paper
    └── runs/<run-name>/         COMMITTED — runs promoted out of outputs/
```

### Rules the tree encodes

1. **`src/<module>/` holds all code.** Never a package directory named after
   the repo at the root, never loose `.py` files beside `pyproject.toml`.
2. **`.docs/` is the entire documentation tree.** There is no `docs/`, no
   `.vault-<name>/`, no second notes directory. Dot-prefixed by convention.
3. **`data/`, `checkpoints/`, `outputs/` are always gitignored** and always
   present (create them empty rather than letting code invent new names).
4. **`.docs/` is never gitignored** — `progress.md`, `figures/` and `runs/`
   are the record of the work and must survive in git.
5. **Every training run writes to `outputs/<run-name>/`.** A run worth keeping
   is *promoted* by copying its keepers into `.docs/runs/<run-name>/`. Nothing
   is ever moved out of `outputs/` — promotion is a copy.
6. **`<run-name>` is one string used in four places**: `--wandb-name`,
   `outputs/<run-name>/`, `.docs/runs/<run-name>/`, and the progress.md
   timetable row. [[wandb-training]] owns the naming convention.
7. **No `.venv` inside an HPC workspace.** See the environment rule below.

### Deliberately not in the tree

- **`adr/`** — not wanted. If [[domain-modeling]] is used it may write
  `CONTEXT.md` at the repo root, but ADR files are not part of this layout.
- **An Obsidian canvas** — deferred to [[obsidian-canvas]], which is a
  placeholder and does nothing today.

## progress.md — the single source of truth

Extremely concise. Three sections, in this order, in one file:

1. **Timetable** — a mermaid `gantt` at the top, plus one line saying where
   things currently stand. The gantt's `section` names are the vocabulary for
   the whole file.
2. **`# Log`** — `## <section>` sub-headings that match the gantt sections
   exactly. Each entry starts with a date, a time and the git commit it
   corresponds to, so any line can be traced back to a diff.
3. **`# Todos`** — grouped under the same section names, so there is always a
   ripe task under whichever block is active.

Adding a gantt section means adding the matching `##` heading under both
`# Log` and `# Todos`. The three section lists must stay identical — that is
what makes the file navigable, and the audit checks it.

Template: [templates/progress.md.tmpl](templates/progress.md.tmpl).

## config-global.json

One per repo, at the root, **committed**. It declares what this repo needs;
paths per machine are resolved at link time, so the same committed file works
on every machine.

Template: [templates/config-global.json.tmpl](templates/config-global.json.tmpl).

| Key | Owner | Meaning |
|---|---|---|
| `repo` | this skill | repo name = workspace name on Helma/Alex |
| `workspaces` | [[data-management]] | workspace name per cluster |
| `datasets` | [[data-management]] | NAS path + shard count per dataset |
| `checkpoints` | [[data-management]] | NAS path per checkpoint |
| `methods` | this skill | git URL + ref, materialized into `third_party/` |
| `smoke` | [[data-management]] | subset size and per-source mix |

`third_party/` is populated from `methods`: a git submodule by default, a plain
clone when the repo must stay out of `.gitmodules`, or a symlink to a checkout
that already exists on the machine.

## Environment: never a .venv in a workspace

The NVMe Lustre workspaces on Helma and Alex are limited by **inodes**, not
volume — roughly 50 000 soft / 75 000 hard per user *across all workspaces*
([quota docs](https://doc.nhr.fau.de/data/workspaces/#quota)). A single venv
with torch is 30 000–60 000 files and can consume the entire budget.

| Machine | Environment |
|---|---|
| workstation, cluster1, cluster2 | uv `.venv` in the repo |
| Helma, Alex | env in **`$HOME`** (~500 000 inode budget, and `$HOME` *is* mounted on Helma GPU nodes — `$WORK` is not) |

NHR@FAU's own recommendation is stronger: *"Due to restriction in inodes on
Helma, it is highly recommended to use apptainer to run your jobs."*
([Helma docs](https://doc.nhr.fau.de/clusters/helma/#python-conda-conda-environments)).
An Apptainer `.sif` is one file and costs one inode. Treat it as the documented
upgrade path; `$HOME` is the accepted default because it needs no workflow
change.

**A `.venv/` found under `/hnvme/workspace/` or `/anvme/workspace/` is a hard
FAIL** — it silently starves every other workspace of inodes.

## Audit checklist

Report PASS/FAIL per line with evidence. Read-only unless asked to fix.

1. **Code location** — `src/<module>/` exists; no package dir named after the
   repo at the root; no loose `*.py` beside `pyproject.toml` (except
   `scripts/`, `slurm/`, `tests/`).
2. **Required directories** — `src/`, `configs/`, `scripts/`, `tests/`,
   `third_party/`, `.docs/figures/`, `.docs/latex-draft/`, `.docs/runs/`
   all exist. `slurm/` required only if the repo runs on Helma/Alex.
3. **Gitignore** — `data/`, `checkpoints/`, `outputs/` ignored;
   `.docs/` **not** ignored. `git check-ignore -v <path>` for each.
4. **config-global.json** — present, parses, and every `datasets` /
   `checkpoints` entry resolves on this machine (delegate to
   `scripts/dm_link.py --check`).
5. **progress.md** — exists, is tracked by git, and its gantt `section` names
   match the `##` headings under `# Log` and `# Todos` exactly.
6. **Run bookkeeping** — every directory in `.docs/runs/` has a matching
   timetable row in `progress.md`; flag any `outputs/<run>/` older than 30 days
   that was never promoted or pruned (ties into the artifact-hygiene rule in
   [[general-codebase]]).
7. **Environment** — no `.venv/` under a workspace path; on a cluster, the
   active env is in `$HOME` or an Apptainer image.
8. **third_party/** — every `methods` entry in config-global.json is
   materialized, and nothing in `third_party/` is missing from the config.

## When a new file has nowhere to go

Do not invent a directory. Either it belongs in one above, or the tree is
wrong and this file changes first — then [[python-project-init]] and the audit
follow. That ordering is the whole point of splitting contract from scaffolder.
