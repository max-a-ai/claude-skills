---
name: mypy-sweep
description: Run mypy across the current repo, list all errors per-file, dispatch up to 5 parallel fix-agents (each handling one file's errors in chunks of ~5), then re-validate. Pauses for user approval before dispatching agents. Use when the user says "mypy sweep", "type-check the repo", "fix mypy errors", "/mypy-sweep", or similar.
---

# mypy-sweep

Iterative mypy check + fix loop. Produces two live artifacts under `.tmp/mypy/` that the user keeps open in a side pane:

- `files-table.md` — per-file status table with ✓ (clean) / ✗ (errors) / ⚠ (stuck), error counts, last-checked timestamp
- `current-errors.md` — flat list of all current errors, refreshed after every agent finishes

Both files have a top row showing the timestamp of the most recent sweep.

## Invariants

- **Per-file granularity** — table rows are one per `.py` file, not per function.
- **Repo's existing mypy config wins** — read `pyproject.toml [tool.mypy]`, `mypy.ini`, or `setup.cfg [mypy]`. Fall back to `mypy <repo-root>` with default flags only if none exists.
- **Pause before dispatching agents** — always show the user the plan (file groups, agent count) and wait for explicit approval.
- **Up to 5 agents in parallel** — bounded pool. Each agent gets one file's worth of errors, chunked at ~5 errors per agent. If a file has more than 5 errors, dispatch multiple agents for the same file (one chunk each).
- **Re-validate after fixes** — re-run mypy, refresh both artifacts, report newly-introduced errors.
- **Stuck errors get ⚠** — agent that can't safely fix an error returns a `notes` string explaining why; skill marks the file ⚠ and lists those errors in a "Manual review needed" section in `current-errors.md`.

## Steps

### 1. Validate this is a suitable repo
- Confirm cwd is a git repo (`git rev-parse --show-toplevel` succeeds). If not, abort with a clear message.
- Find `.py` files: `find . -type f -name '*.py' -not -path '*/\.*' -not -path '*/.venv/*' -not -path '*/venv/*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' -not -path '*/build/*' -not -path '*/dist/*'`
- If zero `.py` files: abort with "no Python source files found — mypy-sweep is not applicable".

### 2. Detect mypy availability and config
- Check `mypy --version`. If missing, ask the user whether to install via `uv add --dev mypy` (preferred when `pyproject.toml` and `uv.lock` are present) or `pip install mypy`.
- Check for config in this order: `pyproject.toml` (look for `[tool.mypy]`), `mypy.ini`, `setup.cfg` (look for `[mypy]`). Note which one is found (or "none — using defaults") for the artifact header.

### 3. Create artifact directory
- `mkdir -p .tmp/mypy`
- Add `.tmp/` to `.gitignore` if not already excluded.

### 4. Run mypy and parse errors
- Run mypy from repo root. With existing config: just `mypy` (it picks up files from config). Without config: `mypy <repo-root>`.
- Parse the output. Mypy's default format is `path:line: severity: message  [error-code]`.
- Group errors by file path.

### 5. Write initial artifacts
- `files-table.md`: top row with last-sweep timestamp + mypy version + config-source. Then a markdown table:

  | File | Status | Errors | Last checked |
  |------|--------|-------:|--------------|
  | bike_motions/foo.py | ✗ | 3 | 2026-05-04 14:23 |
  | bike_motions/bar.py | ✓ | 0 | 2026-05-04 14:23 |

- `current-errors.md`: top row with timestamp. Then a flat list grouped by file:

  ```
  ## bike_motions/foo.py (3 errors)
  - L42: error: Argument 1 to "foo" has incompatible type "str"; expected "int"  [arg-type]
  - L57: error: ...
  ```

### 6. Show the plan and pause for approval
- Compute file groups: each file with >0 errors becomes one or more chunks of up to 5 errors.
- Total agents = number of chunks (capped per parallel batch at 5).
- Print a summary: `N files have errors; M total errors; will dispatch K agents in batches of ≤5.`
- **Stop and ask the user: "Dispatch fix-agents? [yes / show plan / abort]"**.
  - "show plan" = print the file→agent mapping in detail.
  - "abort" = exit gracefully, leave artifacts in place.
  - "yes" = proceed to step 7.

### 7. Dispatch fix-agents (≤5 in parallel)
- Use the Agent tool with `subagent_type: general-purpose` (or specialised if appropriate).
- Each agent receives:
  - The file path (one file per agent for a given chunk).
  - The exact mypy error lines for its chunk.
  - Instructions: "Fix the listed mypy errors in `<file>`. Do not change behaviour. If an error cannot be fixed without a design decision or risks behaviour change, leave it and return a `notes` field explaining why. Report back: (a) which errors you fixed, (b) which you skipped and why, (c) any new errors you introduced if you noticed them."
- Run agents in parallel by issuing multiple Agent tool calls in a single message, capped at 5 concurrent.
- After each batch returns, refresh `current-errors.md` based on the agents' reports (don't re-run mypy yet — that comes in step 8).

### 8. Re-validate
- Run mypy again from scratch.
- Compare new error set against the pre-fix set:
  - Errors that disappeared → success.
  - Errors that remain → either the agent skipped them (mark file ⚠ if any agent returned `notes` for that error) or the fix didn't take.
  - New errors not in the pre-fix set → flag prominently as "regressions introduced by fixes".
- Update both artifacts with the new state and a fresh timestamp.

### 9. Report summary
- Concise text summary to the user:
  ```
  Sweep complete.
  Before: 47 errors across 12 files.
  After:  8 errors across 3 files (39 fixed, 8 stuck/manual).
  New regressions: 0.
  Artifacts: .tmp/mypy/files-table.md, .tmp/mypy/current-errors.md
  ```
- If regressions > 0, recommend running the skill again.

## Notes

- The user keeps `.tmp/mypy/current-errors.md` open in a side pane — every artifact rewrite refreshes their view.
- Skill is idempotent: subsequent invocations produce a fresh sweep. Old data is overwritten, not appended.
- If the user wants to keep a sweep history, that's a future extension (suggest writing dated copies to `.tmp/mypy/history/` only if the user asks).
- Stuck errors stay in `current-errors.md` under a "Manual review needed" section after each sweep — they don't get retried automatically.
