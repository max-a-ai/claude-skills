---
name: general-codebase
description: >
  Whole-lifecycle engineering-rules auditor and gate. Use BEFORE declaring work
  done, when reviewing a change, when starting a repo, or whenever the user says
  "check everything" / "make sure the rules were followed". Walks the standing
  rules (new-repo init, ruff/mypy clean, trainings logged to wandb, artifact
  hygiene, no secrets), reports PASS/FAIL with evidence and the owning skill, and
  clears the Stop audit gate when complete.
---

# general-codebase

The single contract + auditor for this user's standing engineering rules. The
rules are enforced by three layers — know which is which:

- **Hook (hard, automatic):** the harness runs it; cannot be skipped.
- **CLAUDE.md (always in context):** a rule Claude must follow.
- **This skill (audit):** verifies the above were actually honored; run as the
  final gate.

## The lifecycle contract

| Stage | Rule | Enforced by | Owning skill |
|-------|------|-------------|--------------|
| New Python repo | Scaffold with the project initializer (UV + ruff + mypy strict, etc.) before writing code | CLAUDE.md + this audit | `python-project-init` |
| Writing Python | ruff autofix on every edit; mypy must pass in repos that declare a mypy config | **PostToolUse hook** `lint_type_gate.sh` | `ruff-sweep`, `mypy-sweep` |
| Before training | every `main.py` training run passes `--wandb-project`/`--wandb-name` | **PreToolUse hook** `enforce_wandb_training.sh` | `wandb-training` |
| Single-frame trainings | log/checkpoint + eval every epoch (`save_interval: 1`, `eval_every_epoch: true`); sequential runs keep their cadence | configs | `wandb-training` |
| Before "done" | run this audit after code/config changes | **Stop hook** `audit_gate.sh` | this skill |
| Any commit | one-line `<prefix> <description>`, no Claude attribution | CLAUDE.md + this audit | `git-it` |
| Any push | the user pushes, never Claude — print the command instead | CLAUDE.md + this audit | `git-it` |

## Audit checklist (run these, cite evidence, report PASS/FAIL)

1. **New-repo init** — if this is a fresh/empty Python project, was it scaffolded
   via `python-project-init` (pyproject, ruff+mypy config, layout)? If an
   established repo, N/A.
2. **Lint/type** — do changed `*.py` pass `ruff check` and (if the repo has a
   mypy config) `mypy`? The PostToolUse hook enforces live; confirm it is wired
   in `~/.claude/settings.json` and not bypassed (`SKIP_TYPECHECK`/`.no-typecheck`).
3. **Training → wandb** — every `main.py` launch (incl. queue scripts, cron) has
   `--wandb-project`/`--wandb-name`; runs appear in wandb (entity `erik_hm`;
   single-frame → `action-aldenhoven-3dkp`, sequential → `action-aldenhoven-3dkp-over-T`);
   PreToolUse hook still wired; no wandb key hardcoded (auth via `~/.netrc`).
4. **Artifact hygiene** — finished+packaged runs trimmed to best+final checkpoint
   (+ config/log), no per-epoch `*_score.pkl`/`*_each_class_acc.csv` bloat;
   deliverable model folders self-contained.
5. **Secrets** — no credentials in tracked files; `wandb/` gitignored.
6. **Commit hygiene** — do commits made this session use a one-line
   `<prefix> <description>` subject drawn from the eight types (`add`, `bug`,
   `minor`, `refactor`, `docs`, `test`, `config`, `remove`)? Verify no commit
   carries a `Co-Authored-By:`, `Claude-Session:` or "Generated with" trailer:
   `git log --format='%H %s%n%b' origin/HEAD..HEAD | grep -niE 'co-authored|claude-session|generated with'`
   must return nothing. Verify nothing was pushed by Claude — the user pushes.
7. **Skill coverage** — for each skill in `~/.claude/skills/`, if its trigger
   occurred, confirm it was applied; flag any that should have fired.

## How to run
1. Scope: which stages apply to the current work.
2. Check concretely (grep launch commands, read settings.json, inspect work_dir,
   confirm wandb) — cite evidence.
3. Report a short PASS/FAIL table; for each FAIL give the fix + owning skill, and
   offer to fix.
4. **Final step (clears the Stop audit gate):** run
   `~/.claude/hooks/mark_audited.sh` from the repo. Do this only after the audit
   actually passed (or the user accepted the FAILs).

Keep this checklist in sync as new rules/skills/hooks are added — it is the
source of truth the Stop gate points to.
