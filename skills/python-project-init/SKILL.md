---
name: python-project-init
description: Scaffold a new Python project with UV + hatchling + ruff/mypy (strict) + Obsidian vault (canvas/progress/todo) + HANDOFF.md. Use when the user says "new python project", "init python project X", "scaffold a python project", "start a python project from scratch", or similar.
---

# python-project-init

Scaffold a slim, strictly-typed Python project with the user's standard
workflow: UV, src layout, ruff/mypy, and a `.vault-<name>/` dashboard
(Obsidian canvas + progress log + todo).

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
8. **Create `.vault-<name>/` with three files:**
   - `<name>.canvas` from [templates/canvas.json.tmpl](templates/canvas.json.tmpl).
     **Critical:** every node and edge MUST include `"styleAttributes": {}`
     or Obsidian ≥1.5 silently fails to render the canvas. This is the
     most common gotcha — double-check after generation.
   - `progress.md` from [templates/progress.md.tmpl](templates/progress.md.tmpl).
   - `todo.md` from [templates/todo.md.tmpl](templates/todo.md.tmpl).
9. **Create `instructions.md`** from [templates/instructions.md](templates/instructions.md)
   — the canonical coding standards, referenced by HANDOFF and agents.
10. **Create `HANDOFF.md`** from [templates/HANDOFF.md.tmpl](templates/HANDOFF.md.tmpl)
    with today's date (`date +%Y-%m-%d`) and the project name.
11. **Create `.gitignore`** from [templates/gitignore](templates/gitignore).
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
15. **Report** to the user: project tree (top-level only), Python version
    chosen, and a one-liner on how to open the canvas in Obsidian.

## Cautions

- **Don't promote project-specific choices into the template.** GUI
  toolkits (Tkinter, PyQt), specific integrations (ROS2), hardware
  notes — those belong in the per-project HANDOFF, never in this skill.
- **Dot-prefixed vault dir** (`.vault-<name>/`) may be hidden by Obsidian
  by default. Note this in the HANDOFF so the user can toggle "Show hidden
  files" in Obsidian if needed. Do NOT rename to `vault-<name>/` without
  asking — the leading dot keeps it out of most file browsers, which the
  user has adopted as convention.
- **Don't hardcode author name/email.** `uv init` populates these from
  `git config`. If overwriting `pyproject.toml`, preserve the authors
  block UV generated.
- **Strict mypy can flak on `__main__.py`** if the app module isn't ready
  yet. If the user wants a library scaffold, skip step 7 entirely.
