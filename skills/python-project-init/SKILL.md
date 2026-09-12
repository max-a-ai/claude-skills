---
name: python-project-init
description: Scaffold a new Python project with UV + hatchling + ruff/mypy (strict), the flat package layout (repo/<module>/ with fixed subpackages), the .docs/ tree, config-global.json and HANDOFF.md. Use when the user says "new python project", "init python project X", "scaffold a python project", "start a python project from scratch", or similar.
---

# python-project-init

Scaffold a slim, strictly-typed Python project with the user's standard
workflow: UV, a flat package named after the repo, ruff/mypy, and the
`.docs/` documentation tree. Reference implementation:
`~/Documents/lidar-bedlam` (layout finalised 2026-09-12).

## Invariant defaults

- **Python: 3.13** (override to 3.12 on request for platform-constrained
  targets like ROS2 Humble, older Jetson, Ubuntu 24.04 base images, or
  CUDA wheels that lag).
- **Build backend:** hatchling. Never `uv_build`.
- **Line length: 79.** Ruff enforces, mypy strict enforces typing.
- **Flat layout, no `src/`:** the package lives at `<repo>/<module>/`, one
  folder named after the repo (`MODULE_NAME` = repo name with `-` -> `_`,
  because import names cannot contain a hyphen). Big-tech style
  (`sam3/sam3/`).
- **Top level stays minimal.** Everything that is code goes inside the
  package (including `scripts/` and `slurm/`); only the folders listed
  below may exist at the top level.
- **No GUI or runtime deps** by default — user chooses per project.

## The tree (`tree -L 2 -a`, what a fresh scaffold looks like)

```
<repo>/
├── <module>/                # THE package, flat, named after the repo            [tracked]
│   ├── data/                #   datasets, schema, loaders, augmentation          [mandatory]
│   ├── models/              #   architectures                                     [mandatory]
│   ├── losses/              #   training losses                                   [mandatory]
│   ├── metrics/             #   evaluation metrics and protocol                   [mandatory]
│   ├── train/               #   config, sampler, trainer                          [mandatory]
│   ├── utils/               #   io, viz, small helpers                            [mandatory]
│   ├── scripts/             #   CLIs: <repo>-main.py, <repo>-eval.py, dm_link.py  [mandatory, no __init__.py]
│   ├── slurm/               #   cluster job scripts                               [mandatory if a cluster is used]
│   ├── <domain>/ ...        #   project-specific subpackages, added as needed
│   └── __init__.py  __main__.py  app.py  py.typed
├── configs/                 # one yaml per experiment                            [tracked]
├── notebooks/               # one capabilities notebook: quick checks of the repo [tracked; *.executed.ipynb ignored]
├── tests/                   # pytest, one file per module group                  [tracked]
├── third_party/             # external repos as git submodules                   [tracked as gitlinks]
├── .docs/                   # the record of the work (hidden: needs `tree -a`)   [tracked]
│   ├── progress.md          #   timetable + log + todos, same section names
│   ├── figures/             #   generated figures (png, html, glb)
│   ├── latex-draft/         #   the paper, builds with plain `latexmk`
│   └── runs/                #   promoted run keepers (copied from outputs/)
├── resources/               # machine-dependent inputs, built by dm_link.py       [gitignored]
│   ├── data/                #   dataset links + generated/ (shards, tokens, extracted frames)
│   └── pretrained-checkpoints/  # links to pretrained weights
├── outputs/                 # one directory per run + background-job logs           [gitignored]
│   ├── mix80-000/           #   a training run, name = <experiment>-<NNN>; contains:
│   │   ├── config.json      #     the resolved config the run used
│   │   ├── metrics.jsonl    #     every logged row (step, epoch, losses, val metrics)
│   │   ├── val_0000500.json #     one file per evaluation
│   │   ├── last.pt  best.pt #     checkpoints (model, optimiser, step); best = best primary metric
│   │   ├── DONE             #     written when max_steps/max_epochs is reached
│   │   └── wandb/           #     wandb files if the run logged directly
│   ├── batchtest2-b1024/    #   a short test run, same layout, name = <experiment>-<tag>
│   └── logs/                #   stdout of background jobs: generation, tokens, rsync, slurm-*.out
├── config-global.json       # hosts, datasets, checkpoints, methods, smoke        [tracked]
├── pyproject.toml  uv.lock  .python-version
├── README.md  HANDOFF.md  instructions.md
└── .gitignore  .gitmodules
```

`tree -L 2` shows the top level and one level below it. Two things it
does **not** show: dot-folders (`.docs/`) unless you pass `-a`, and the
third level (the modules inside `<module>/data/`, the contents of
`.docs/latex-draft/`, `resources/data/generated/`, `outputs/<run>/`).

## Folder contract (what goes where, tracked or not)

| Folder | Tracked | Use |
|---|---|---|
| `<module>/` | yes | all code; nothing importable lives outside it |
| `<module>/data/` | yes | dataset classes, sample schema, loaders, augmentation, shard formats |
| `<module>/models/` | yes | model architectures and their building blocks |
| `<module>/losses/` | yes | loss functions and weights |
| `<module>/metrics/` | yes | metrics and the evaluation protocol |
| `<module>/train/` | yes | training config dataclasses, samplers, the trainer loop |
| `<module>/utils/` | yes | io readers, plotting, small helpers |
| `<module>/scripts/` | yes | command-line entry points: `<repo>-main.py` (training, must carry `--wandb-project`/`--wandb-name`), `<repo>-eval.py`, `dm_link.py`, data preparation; no `__init__.py`, so hyphenated names are fine |
| `<module>/slurm/` | yes | sbatch job scripts and login-node helpers (e.g. a wandb mirror) |
| `<module>/<domain>/` | yes | project-specific subpackages (e.g. `geometry/`, `lidar/`, `rigs/`) |
| `configs/` | yes | experiment yaml, one per run type; ablations as copies with one change |
| `notebooks/` | yes | one `capabilities.ipynb` that shows what the repo can do on real data; executed copies are ignored |
| `tests/` | yes | pytest unit tests; `uv run pytest` must pass before "done" |
| `third_party/` | gitlinks | baseline / external repos as submodules, never edited in place |
| `.docs/` | yes | the record: `progress.md` (timetable, log, todos), notes, `figures/`, `latex-draft/`, `runs/` |
| `resources/` | **no** | per-machine inputs built by `dm_link.py` from `config-global.json`: `data/` (links to datasets, `generated/` for derived data), `pretrained-checkpoints/` (links to weights) |
| `outputs/` | **no** | one directory per run, named `<experiment>-<NNN>` (or `-<tag>` for tests), each holding `config.json`, `metrics.jsonl`, `val_<step>.json`, `last.pt`, `best.pt`, `DONE` (see the tree); `outputs/logs/` for background-job stdout and Slurm output files; keepers are *copied* to `.docs/runs/` |

## Steps

1. **Confirm the project name** (kebab-case) if not obvious from the user's
   message. Derive `MODULE_NAME` as `snake_case` of the project name.
2. **Check the target directory.** If it's the cwd, ensure it's empty or
   only contains a HANDOFF / README the user wrote. If not, ask before
   overwriting.
3. **Check prereqs:** `uv --version` must succeed.
4. **Initialize (flat layout):**
   ```bash
   uv init --python 3.13 --name <PROJECT_NAME> --no-readme .
   rm -f main.py hello.py
   mkdir -p <MODULE_NAME>
   ```
5. **Rewrite `pyproject.toml`** from [templates/pyproject.toml.tmpl](templates/pyproject.toml.tmpl),
   substituting `{{PROJECT_NAME}}`, `{{MODULE_NAME}}`, `{{PYTHON_VERSION}}`
   (e.g. `3.13`), `{{PYTHON_TAG}}` (e.g. `py313`), `{{PYTHON_UPPER}}`
   (e.g. `3.14`), and `{{DESCRIPTION}}` (ask the user for a one-liner).
6. **Create the package skeleton:** `<MODULE_NAME>/__init__.py` (docstring +
   `__version__ = "0.1.0"`), `__main__.py` calling `app.main`, `app.py`
   (prints the version), `py.typed`, and the mandatory subpackages
   `data/ models/ losses/ metrics/ train/ utils/` each with an
   `__init__.py` docstring, plus `scripts/` and `slurm/` (no `__init__.py`,
   `.gitkeep`). Entry-point files `scripts/<PROJECT_NAME>-main.py` and
   `scripts/<PROJECT_NAME>-eval.py` start as argparse stubs.
7. **Create the `.docs/` tree** — committed: `.docs/progress.md` (gantt
   timetable at the top, `# Log` in the middle, `# Todos` at the bottom,
   all three using the **same section names**), `.docs/figures/`,
   `.docs/latex-draft/`, `.docs/runs/` with `.gitkeep`.
8. **Create `config-global.json`** with `hosts`, `datasets`, `checkpoints`,
   `methods`, `smoke` blocks and `_example_` entries as documentation
   (keys starting with `_` are skipped), and `scripts/dm_link.py` that
   materialises `resources/data/<name>`, `resources/pretrained-checkpoints/<name>`
   and `outputs/` for the current host (`--check`, `--smoke`). Copy both
   from the reference implementation and adapt the names.
9. **Create the remaining top-level folders:** `configs/`, `notebooks/`,
   `tests/`, `third_party/` (tracked, `.gitkeep`), and the gitignored
   `resources/`, `outputs/`.
10. **Create `instructions.md`** from [templates/instructions.md](templates/instructions.md).
11. **Create `HANDOFF.md`** from [templates/HANDOFF.md.tmpl](templates/HANDOFF.md.tmpl)
    with today's date (`date +%Y-%m-%d`) and the project name.
12. **Create `.gitignore`** from [templates/gitignore](templates/gitignore).
    It must ignore `resources/`, `outputs/`, `notebooks/*.executed.ipynb`
    and must NOT ignore `.docs/`.
13. **Create `README.md`** from [templates/README.md.tmpl](templates/README.md.tmpl).
14. **Sync and verify:**
    ```bash
    uv sync
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy
    ```
    All three must return zero errors. Fix any issues before reporting done.
15. **Offer `git init`** if the directory isn't already a repo.
16. **Verify the layout** against the folder contract above: every
    mandatory folder exists, nothing else at the top level, gitignore
    matches the table.
17. **Report** to the user: the `tree -L 2 -a` output, the Python version
    chosen, and where `.docs/progress.md` lives.

## Cautions

- **Don't promote project-specific choices into the template.** GUI
  toolkits, ROS2, hardware notes belong in the per-project HANDOFF.
- **`.docs/` is dot-prefixed** and hidden by Obsidian and file browsers;
  say so in the HANDOFF. Never rename it to `docs/`.
- **`.docs/` is never gitignored; `resources/` and `outputs/` always are.**
  Getting this backwards loses the record of the work.
- **Don't hardcode author name/email.** `uv init` populates these from
  `git config`; preserve the authors block when overwriting `pyproject.toml`.
- **Hyphenated script names** (`<repo>-main.py`) only work because
  `scripts/` has no `__init__.py`; keep it that way.
- **wandb hook:** the user's `enforce_wandb_training.sh` hook matches the
  training entry point by name; keep `<repo>-main.py` and make sure the
  hook regex covers `*-main.py`.
