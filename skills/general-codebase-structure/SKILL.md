---
name: general-codebase-structure
description: >
  The canonical directory tree every repository has, and the audit that
  checks a repo against it. Use when starting a repo, deciding where a new
  file belongs, writing or reading .docs/progress.md, or when
  general-codebase runs its full audit.
---

# general-codebase-structure

**This skill is the contract, not the scaffolder.** It states the layout and
audits a repo against it; [[python-project-init]] writes the files. When the
two disagree, this skill wins and the initializer is the thing to fix.

[[general-codebase]] runs the audit below alongside ruff, mypy and wandb.

## The tree

```
<repo-name>/                     ← on Helma/Alex this IS the workspace root
├── pyproject.toml               uv + hatchling, ruff 79 cols, mypy strict
├── uv.lock
├── .python-version
├── config-global.json           datasets, checkpoints, methods, smoke recipe
├── .gitignore
├── README.md
├── HANDOFF.md
├── instructions.md              coding standards
│
├── src/<module>/                ALL main code
│
├── third_party/                 methods from config-global.json: submodule,
│   └── <method>/                  clone, or symlink to an existing checkout
│
├── configs/                     experiment yaml
├── scripts/                     dm_pack.py, dm_push.sh, dm_status.sh, ...
├── slurm/                       sbatch job scripts
├── tests/
│
├── data/          ┐ gitignored, machine-dependent, built by [[data-management]]
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

1. **All code lives in `src/<module>/`** — never a package named after the
   repo at the root, never loose `.py` beside `pyproject.toml`.
2. **`.docs/` is the entire documentation tree.** One notes directory, named
   exactly that, dot-prefixed by convention.
3. **`data/`, `checkpoints/` and `outputs/` are gitignored and always
   present** — create them empty, so code has no reason to invent a fourth
   name for the same idea.
4. **`.docs/` stays committed.** It is the record of the work.
5. **Every training run writes to `outputs/<run-name>/`.** A run worth
   keeping is **promoted**: its keepers are *copied* into
   `.docs/runs/<run-name>/`, and the original stays put.
6. **`<run-name>` is one string in four places** — `--wandb-name`,
   `outputs/`, `.docs/runs/`, and the progress.md timetable row.
   [[wandb-training]] owns the convention.
7. **Environments live outside a workspace** on Helma and Alex; those
   filesystems are inode-bound. Rule and reasons: [[data-management]].

Two things are deliberately absent: **ADR files** (if [[domain-modeling]]
runs, `CONTEXT.md` goes at the repo root, and that is all), and an **Obsidian
canvas** (deferred to [[obsidian-canvas]], a placeholder).

## progress.md

Extremely concise, and the first file to read in any repo. Three sections in
one file, sharing **one set of section names**:

1. **Timetable** — a mermaid `gantt` at the top, plus one line on where
   things stand. Its `section` names are the vocabulary for the whole file.
2. **`# Log`** — `##` headings matching those sections. Entries open with
   `### YYYY-MM-DD HH:MM — <what> (<commit>)`, so any line traces to a diff.
3. **`# Todos`** — the same headings again, so there is always a ripe task
   under whichever block is active.

Adding a gantt section means adding the matching `##` under both `# Log` and
`# Todos`. Those three lists staying identical is what makes the file
navigable, and the audit checks it.

Template: [templates/progress.md.tmpl](templates/progress.md.tmpl).

## config-global.json

One per repo, at the root, committed. It declares what this repo needs; paths
resolve per machine at link time, so the same committed file works
everywhere. [templates/config-global.json.tmpl](templates/config-global.json.tmpl)
is the source of truth for its keys.

This skill owns `methods`, which populates `third_party/` — a git submodule
by default, a plain clone when it must stay out of `.gitmodules`, or a
symlink to a checkout already on the machine. [[data-management]] owns
`workspaces`, `datasets`, `checkpoints` and `smoke`.

## Audit

Give every line a verdict and cite the command output behind it. A line you
could not check is N/A **with the reason** — never silently dropped. Report
read-only unless asked to fix.

1. **Code location** — `src/<module>/` exists; no repo-named package at the
   root; no loose `*.py` beside `pyproject.toml`.
2. **Directories** — `src/`, `configs/`, `scripts/`, `tests/`,
   `third_party/`, `.docs/figures/`, `.docs/latex-draft/`, `.docs/runs/`
   present. `slurm/` only if the repo runs on Helma/Alex.
3. **Gitignore** — `git check-ignore -v` confirms `data/`, `checkpoints/`,
   `outputs/` ignored and `.docs/` tracked.
4. **config-global.json** — parses, and every entry resolves on this machine:
   `python3 scripts/dm_link.py --check`.
5. **progress.md** — tracked by git, and its gantt sections match the `##`
   headings under `# Log` and `# Todos` exactly.
6. **Runs** — every `.docs/runs/<run>/` has a timetable row; flag any
   `outputs/<run>/` older than 30 days never promoted or pruned.
7. **Environment** — `find <workspace> -name .venv` is empty; on a cluster
   the active env is `$HOME` or an Apptainer image.
8. **third_party/** — matches `methods` in both directions.

## When a new file has nowhere to go

Every file belongs in one of the directories above. When none fits, the tree
is wrong: change this file first, then [[python-project-init]] and the audit
follow. That ordering is the point of splitting contract from scaffolder.
