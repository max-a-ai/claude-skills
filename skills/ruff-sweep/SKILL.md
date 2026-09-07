---
name: ruff-sweep
description: Run ruff across the current repo. Auto-fixes mechanical issues first (most disappear), pauses before applying unsafe fixes or formatting, dispatches up to 5 parallel fix-agents only for residue that ruff can't resolve mechanically. Use when the user says "ruff sweep", "lint the repo", "fix ruff errors", "/ruff-sweep", or similar.
---

# ruff-sweep

Linter sweep that prefers mechanical autofixes over LLM agents. Most ruff issues auto-resolve via `ruff check --fix` and `ruff format` — agents are dispatched only for the residue.

Two live artifacts under `.tmp/ruff/`:

- `files-table.md` — per-file status table with ✓ / ✗ / ⚠, issue counts, last-checked timestamp
- `current-issues.md` — flat list of issues remaining after auto-fix

## Invariants

- **Per-file granularity** — table rows are one per `.py` file.
- **Repo's existing ruff config wins** — read `pyproject.toml [tool.ruff]` / `ruff.toml` / `.ruff.toml`. Fall back to ruff defaults only if none exists.
- **Auto-fix before agents** — always run `ruff check --fix` first. Only the residue triggers agent dispatch.
- **Pause before unsafe fixes** — `--unsafe-fixes` can change behaviour, so confirm before applying.
- **Pause before format** — `ruff format` touches many files cosmetically; confirm before applying.
- **Up to 5 agents in parallel** — bounded pool. Each agent gets one file's worth of issues, chunked at ~5 issues per agent. Multiple agents may share a file (different chunks) but never run concurrently on the same file.
- **Re-validate after fixes** — re-run ruff check, refresh both artifacts, report regressions.
- **Stuck issues get ⚠** — agent that can't safely fix returns a `notes` string; skill marks the file ⚠ and lists those issues under "Manual review needed".

## Steps

### 1. Validate this is a suitable repo
- Confirm cwd is a git repo (`git rev-parse --show-toplevel` succeeds). If not, abort.
- Find `.py` files (same exclusions as mypy-sweep: `.venv`, `node_modules`, `__pycache__`, `build`, `dist`).
- If zero `.py` files: abort with "no Python source files found".

### 2. Detect ruff availability and config
- Check `ruff --version`. If missing, ask whether to install via `uv add --dev ruff` or `pip install ruff`.
- Check for config in this order: `pyproject.toml [tool.ruff]`, `ruff.toml`, `.ruff.toml`. Note source for the artifact header.

### 3. Create artifact directory
- `mkdir -p .tmp/ruff`
- Add `.tmp/` to `.gitignore` if not already excluded.

### 4. Initial scan (no fixes)
- Run `ruff check .` and capture full output.
- Parse issues. Ruff format is `path:line:col: code message`.
- Group by file. Count safe-fixable vs unsafe-fixable vs not-fixable (use `ruff check --statistics` for the breakdown, or run with `--show-fixes` to see what would change).

### 5. Show plan and pause for autofix decisions
- Print summary: total issues, safe-fixable count, unsafe-fixable count, not-fixable count, files affected.
- **Ask the user**:
  - "Apply safe autofixes? (`ruff check --fix .`) — recommended, will not change behaviour" [yes / no]
  - "Apply unsafe autofixes? (`ruff check --fix --unsafe-fixes .`) — may change behaviour, e.g. simplifying comprehensions" [yes / no / show diff first]
  - "Run formatter? (`ruff format .`) — cosmetic only, touches many files" [yes / no / show diff first]
- Skip questions for empty buckets (e.g. don't ask about formatter if no formatting issues).

### 6. Apply autofixes per the user's choices
- Run the chosen subset of: `ruff check --fix .`, `ruff check --fix --unsafe-fixes .`, `ruff format .`.
- Capture output of each.

### 7. Re-scan and assess residue
- Run `ruff check .` again.
- Parse remaining issues. Most may be gone.
- Write initial artifacts:
  - `files-table.md`: top row with timestamp + ruff version + config-source + summary of what autofix resolved. Then per-file table.
  - `current-issues.md`: top row with timestamp. Then flat list of residual issues grouped by file.

### 8. If residue exists, dispatch fix-agents
- If `ruff check .` is now clean: skip to step 10 with a "all resolved by autofix" report.
- Otherwise: chunk residue (≤5 issues per chunk, one file per chunk), compute agent count, batch into ≤5 parallel.
- **Pause and ask**: "Dispatch K fix-agents for the N residual issues? [yes / show plan / abort]"
- On approval, dispatch. Each agent receives:
  - File path.
  - The exact ruff issue lines for its chunk.
  - Instructions: "Fix the listed ruff issues in `<file>`. Most have a code like E501, F401, etc. — look up the rule if needed. Don't change behaviour. If unsure, leave it and explain why. Report FIXED / SKIPPED / NEW."
- Two agents must not work on the same file in the same batch — schedule across batches.

### 9. Re-validate
- Run `ruff check .` once more.
- Compare against post-autofix state:
  - Newly clean files → success.
  - Lingering issues → likely the agent skipped them (mark file ⚠) or fix didn't take.
  - Issues not in pre-fix set → flag as regressions.
- Update both artifacts.

### 10. Report summary
- Concise text:
  ```
  Ruff sweep complete.
  Initial: 184 issues across 22 files.
  After safe autofix:   12 issues across 4 files.
  After unsafe autofix:  8 issues across 3 files.
  After format:          8 issues across 3 files (formatting touched 17 files).
  After agents:          0 issues (8 fixed by agents).
  Files modified: 31 total.
  Artifacts: .tmp/ruff/files-table.md, .tmp/ruff/current-issues.md
  ```
- If regressions > 0, recommend re-running.

## Notes

- **Order matters**: autofix → format → agents → re-validate. Running format before autofix can mask issues; running agents before autofix wastes LLM cost on mechanical fixes.
- The skill is idempotent. Re-running on an already-clean repo finishes in seconds and writes timestamped artifacts.
- For commits: best practice is to run `/ruff-sweep` then `/mypy-sweep` (ruff first because formatting changes can introduce trivial typing issues, and we want mypy to see the final shape).
- If the user has aggressive ruff rules enabled (e.g. `D` docstring rules) and the residue is large, suggest narrowing the rule set in `pyproject.toml` rather than dispatching agents to write docstrings.
