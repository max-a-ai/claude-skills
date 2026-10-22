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
The `dm_*` scripts that build the gitignored part live in [[data-management]].

[[general-codebase]] runs the audit below alongside ruff, mypy and wandb.

## The tree

```
<repo-name>/                     ← on Helma/Alex this IS the workspace root
├── pyproject.toml               uv + hatchling, ruff 79 cols, mypy strict
├── uv.lock
├── .python-version
├── config-global.json           nas_root, machines, workspaces, datasets, checkpoints, methods, smoke
├── .gitignore
├── README.md
├── HANDOFF.md
├── instructions.md              coding standards
│
├── <module>/                    THE package: flat, named after the repo
│   ├── data/  models/  losses/  metrics/  train/  utils/   mandatory subpackages
│   ├── scripts/                 CLIs + dm_*.py/sh from [[data-management]]; no __init__.py
│   ├── slurm/                   sbatch job scripts (only if a cluster is used)
│   ├── <domain>/                project-specific subpackages, added as needed
│   └── __init__.py  __main__.py  app.py  py.typed
│
├── third_party/                 methods from config-global.json: submodule,
│   └── <method>/                  clone, or symlink to an existing checkout
│
├── configs/                     experiment yaml
├── notebooks/                   numbered; *.executed.ipynb ignored
│   ├── 000-capabilities.ipynb   the repo tour: executes + visualises
│   ├── 001-<slug>.ipynb         one question per notebook
│   ├── ipynb-assets/            nb001_<slug>.py holds the cell bodies
│   └── README.md                generated index, committed
├── tests/
│
├── resources/     ┐ gitignored, machine-dependent, built by [[data-management]]
│   ├── data/      │   datasets (+ generated/ for derived data, _smoke/ subset)
│   └── pretrained-checkpoints/
├── outputs/       ┘ one directory per run: outputs/<run-name>/, plus logs/
│
└── .docs/
    ├── progress.md              COMMITTED — the single source of truth
    ├── figures/                 curated images / lidar renders
    ├── latex-draft/             the paper; bib/bib_long.def + bib/bib_short.def (start with bib_long)
    └── runs/<run-name>/         COMMITTED — runs promoted out of outputs/
```

### Rules the tree encodes

0. **Bibliography venue macros:** `.docs/latex-draft/bib/` holds
   `bib_long.def` and `bib_short.def` (from `python-project-init/templates/
   latex-draft/bib/`). A paper always starts with `bib_long.def`; it switches
   to `bib_short.def` only to meet the page limit. Both define the same macros.

1. **All code lives in `<module>/`** — one flat package named after the
   repo (`-` → `_`), no `src/`, never loose `.py` beside `pyproject.toml`.
   `scripts/` and `slurm/` are inside it; the top level holds only the
   folders drawn above.
2. **`.docs/` is the entire documentation tree.** One notes directory, named
   exactly that, dot-prefixed by convention.
3. **`resources/` and `outputs/` are gitignored and always present** —
   `resources/data/` and `resources/pretrained-checkpoints/` are built by
   `dm_link.py`; create them empty so code has no reason to invent another
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

## Notebooks

The failure this prevents is a folder of notebooks whose purpose nobody
remembers.

### Naming

Notebooks are numbered, because they are read in order:
`001-lift-splat-depth.ipynb` (three digits, hyphen, hyphenated slug).
Every other `.py` in the repo is plain `snake_case.py` with no number.

### The first markdown cell

Exactly this shape, in this order:

```markdown
# is depth learnable without lidar supervision

## Checks
- [ ] frustum features land in the right pillar
- [ ] depth histogram is not uniform

**Verdict:**

<free text from here on>
```

The `#` heading is the question the notebook answers, around ten words.
It becomes the index's "Asks" column. `## Checks` holds only checkboxes,
ticked off as you go; unticked boxes are fine and mean "still open".
`**Verdict:**` is one line saying what came out, filled in when the last
box is ticked. That line is what future-you reads instead of reopening
the notebook, so a fully ticked notebook without one is an audit FAIL.

### Cells stay one line

The code is not meant to be read in the notebook. Each cell is the
parameters it varies, then one call:

```python
from nb001_lift_splat_depth import plot_depth_histogram

data_path: str = "resources/data/waymo"
n_bins: int = 24
plot_depth_histogram(data_path, n_bins)
```

The body lives in `notebooks/ipynb-assets/nb001_lift_splat_depth.py`,
one function per cell, **always with a docstring**: hovering the call is
how the code gets read.

The asset name is mechanical, so the audit can check the pairing both
ways: `001-lift-splat-depth.ipynb` pairs with `nb001_lift_splat_depth.py`
(prefix `nb`, hyphens to underscores). That prefix and those underscores
are what make it importable, and a statically resolvable import is what
makes hover work. `importlib.import_module("001-lift-splat-depth")` also
runs, but it types as `ModuleType`, so hover, signature help and
autocomplete all go dead, which defeats the point of the split.

Do not design around collapsing a cell by hand. VS Code keeps collapse
state as editor view state keyed by cell index and never writes it into
the file ([vscode#237074](https://github.com/microsoft/vscode/issues/237074)),
so no notebook can ship collapsed. A one-line cell needs no collapsing.

Code used anywhere outside its notebook belongs in `<module>/`, not in
`ipynb-assets/`.

### 000-capabilities.ipynb

Every repo has one, and it is the entry point for anyone new. It executes
and visualises the repo's most important capabilities in the order they
were built, so running it top to bottom both proves the repo still works
and shows what was done. Someone joining reads `.docs/progress.md` for
the narrative and runs this for the demonstration.

It links to progress.md rather than restating it. When a capability
lands, add it here: its `## Checks` box is that capability, and the
`**Verdict:**` line is "all N capabilities execute as of <date>".

A fresh repo has no capabilities to demonstrate, so this notebook is
required only once the repo has any other notebook.

### notebooks/README.md

Generated, committed, never hand-edited:

```bash
python3 <module>/scripts/nb_index.py          # rewrite
python3 <module>/scripts/nb_index.py --check  # audit
```

One row per notebook: linked number, what it asks, its verdict, ticked
checks, created date, last run, cell count. Every column is derived from
the notebook or from git, so nothing is maintained by hand. Regenerate it
whenever a notebook is added or edited, before the turn ends; the audit
re-checks it as a backstop.

**Last run is only trustworthy after a headless run.** VS Code records no
execution timestamps at all, so the script reads the `*.executed.ipynb`
sibling that `nbconvert --execute` writes, which sets `metadata.execution`
by default. With no sibling the column falls back to the file mtime and is
marked `*`. It reads the sibling rather than the notebook deliberately: a
notebook executed headlessly once and re-run in VS Code afterwards keeps
stale timestamps in its own metadata, and VS Code leaves them untouched.

## Audit

Give every line a verdict and cite the command output behind it. A line you
could not check is N/A **with the reason** — never silently dropped. Report
read-only unless asked to fix.

1. **Code location** — `<module>/` (repo name, `-` → `_`) exists at the
   root with `__init__.py`; no `src/`; no loose `*.py` beside
   `pyproject.toml`; nothing at the top level beyond the tree above.
2. **Directories** — `<module>/{data,models,losses,metrics,train,utils,scripts}/`,
   `configs/`, `notebooks/ipynb-assets/`, `tests/`, `third_party/`,
   `.docs/figures/`, `.docs/latex-draft/`, `.docs/runs/` present. `<module>/slurm/` only if
   the repo runs on Helma/Alex. `<module>/scripts/` has no `__init__.py`.
3. **Gitignore** — `git check-ignore -v` confirms `resources/`, `outputs/`
   and `notebooks/*.executed.ipynb` ignored, and `.docs/` plus
   `notebooks/README.md` tracked.
4. **config-global.json** — parses, and every entry resolves on this machine:
   `python3 <module>/scripts/dm_link.py --check`.
5. **progress.md** — tracked by git, and its gantt sections match the `##`
   headings under `# Log` and `# Todos` exactly.
6. **Runs** — every `.docs/runs/<run>/` has a timetable row; flag any
   `outputs/<run>/` older than 30 days never promoted or pruned.
7. **Environment** — `find <workspace> -name .venv` is empty; on a cluster
   the active env is `$HOME` or an Apptainer image.
8. **third_party/** — matches `methods` in both directions.
9. **Notebooks** — `python3 <module>/scripts/nb_index.py --check` exits 0.
   It covers the three-digit name, the `#` heading, the `## Checks` boxes,
   a fully ticked notebook with no `**Verdict:**`, asset pairing in both
   directions, and a stale index. Also confirm `000-capabilities.ipynb`
   exists once the repo has any other notebook.

## When a new file has nowhere to go

Every file belongs in one of the directories above. When none fits, the tree
is wrong: change this file first, then [[python-project-init]] and the audit
follow. That ordering is the point of splitting contract from scaffolder.
