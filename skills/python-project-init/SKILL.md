---
name: python-project-init
description: Scaffold a new Python project with UV + hatchling + ruff/mypy (strict) + the .docs/ tree + config-global.json + HANDOFF.md. Use when the user says "new python project", "init python project X", "scaffold a python project", "start a python project from scratch", or similar.
---

# python-project-init

Scaffold a slim, strictly-typed Python project with the user's standard
workflow: UV, src layout, ruff/mypy, and the `.docs/` documentation tree.

**This skill is the scaffolder; [[general-codebase-structure]] is the
contract.** It defines the tree, `config-global.json` and the shape of
`progress.md`. If the two disagree, that skill wins and this one is wrong —
read it before changing anything here.

## Invariant defaults

- **Python: 3.13** (override to 3.12 on request for platform-constrained
  targets like ROS2 Humble, older Jetson, Ubuntu 24.04 base images).
- **Build backend:** hatchling. Never `uv_build` (newer, less documented).
- **Line length: 79.** Ruff enforces, mypy strict enforces typing.
- **src/ layout** always.
- **No GUI or runtime deps** by default — user chooses per project.

## Steps

1. **Confirm the project name** (kebab-case) if not obvious from the user's
   message. Derive `MODULE_NAME` as `snake_case` of the project name.
2. **Check the target directory.** If it's the cwd, ensure it's empty or
   only contains a HANDOFF / README the user wrote. If not, ask before
   overwriting.
3. **Check prereqs:** `uv --version` must succeed.
4. **Initialize:**
   ```bash
   uv init --python 3.13 --package --name <PROJECT_NAME> --no-readme .
   ```
5. **Rewrite `pyproject.toml`** from [templates/pyproject.toml.tmpl](templates/pyproject.toml.tmpl),
   substituting `{{PROJECT_NAME}}`, `{{MODULE_NAME}}`, `{{PYTHON_VERSION}}`
   (e.g. `3.13`), `{{PYTHON_TAG}}` (e.g. `py313`), `{{PYTHON_UPPER}}`
   (e.g. `3.14` for the exclusive upper bound), and `{{DESCRIPTION}}`
   (ask the user for a one-liner).
6. **Replace `src/<module>/__init__.py`** with a docstring + `__version__ = "0.1.0"`.
7. **Create `src/<module>/__main__.py`** that imports and calls `main`
   from `<module>.app` — but only if the user wants an `app.py` entry.
   For a library, skip this and remove the `[project.scripts]` block.
8. **Create the `.docs/` tree** — the whole documentation tree, committed:
   - `.docs/progress.md` from
     [../general-codebase-structure/templates/progress.md.tmpl](../general-codebase-structure/templates/progress.md.tmpl).
     One file: gantt timetable at the top, `# Log` in the middle, `# Todos`
     at the bottom, all three using the **same section names**. It replaces
     the old `progress.md` + `todo.md` pair.
   - `.docs/figures/`, `.docs/latex-draft/`, `.docs/runs/` — created empty
     (with a `.gitkeep` so they survive a clone).
   - No Obsidian canvas: deferred to [[obsidian-canvas]], which is a
     placeholder.

8b. **Create `config-global.json`** from
   [../general-codebase-structure/templates/config-global.json.tmpl](../general-codebase-structure/templates/config-global.json.tmpl),
   substituting `{{PROJECT_NAME}}`. Leave the `_example_` entries in place as
   documentation — [[data-management]] skips `_`-prefixed keys.

8c. **Create the remaining directories:** `configs/`, `scripts/`, `slurm/`,
   `tests/`, `third_party/`, and the gitignored `data/`, `checkpoints/`,
   `outputs/`.
9. **Create `instructions.md`** from [templates/instructions.md](templates/instructions.md)
   — the canonical coding standards, referenced by HANDOFF and agents.
10. **Create `HANDOFF.md`** from [templates/HANDOFF.md.tmpl](templates/HANDOFF.md.tmpl)
    with today's date (`date +%Y-%m-%d`) and the project name.
11. **Create `.gitignore`** from [templates/gitignore](templates/gitignore).
    It must ignore `data/`, `checkpoints/`, `outputs/` and must NOT ignore
    `.docs/`.
12. **Create `README.md`** from [templates/README.md.tmpl](templates/README.md.tmpl).
13. **Sync and verify:**
    ```bash
    uv sync
    uv run ruff check src/
    uv run ruff format --check src/
    uv run mypy src/
    ```
    All three must return zero errors. Fix any issues before reporting done.
14. **Offer `git init`** if the directory isn't already a repo.
15. **Verify the layout** by running the [[general-codebase-structure]]
    audit checklist against the fresh repo. It must pass before reporting
    done.
16. **Report** to the user: project tree (top-level only), Python version
    chosen, and where `.docs/progress.md` lives.

## Cautions

- **Don't promote project-specific choices into the template.** GUI
  toolkits (Tkinter, PyQt), specific integrations (ROS2), hardware
  notes — those belong in the per-project HANDOFF, never in this skill.
- **`.docs/` is dot-prefixed** and may be hidden by Obsidian and by file
  browsers. Note this in the HANDOFF so the user can toggle "Show hidden
  files". Do NOT rename it to `docs/` — the leading dot is the convention,
  and [[general-codebase-structure]] audits for exactly this name.
- **`.docs/` is never gitignored.** `data/`, `checkpoints/` and `outputs/`
  always are. Getting this backwards loses the record of the work.
- **Don't hardcode author name/email.** `uv init` populates these from
  `git config`. If overwriting `pyproject.toml`, preserve the authors
  block UV generated.
- **Strict mypy can flak on `__main__.py`** if the app module isn't ready
  yet. If the user wants a library scaffold, skip step 7 entirely.
