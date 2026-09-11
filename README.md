# claude-skills

One skill repository, cloned once, available in every project.

Combines three sources:

| Set | Source | Contents |
|---|---|---|
| `skills/` | mine | 10 private skills — Python/ML workflow (ruff, mypy, wandb, project init, repo layout, HPC data management, graphify, git-it, the standing-rules auditor) |
| `third_party/mattpocock-skills/` | [mattpocock/skills](https://github.com/mattpocock/skills) (submodule) | The engineering loop — grilling, spec/ticket flows, TDD, domain modelling, diagnosis |
| `third_party/research-skills/` | [saidwivedi/research-skills](https://github.com/saidwivedi/research-skills) (submodule) | `research-collaborator` (hypothesis falsification, 191 silent-bug patterns) and `results-to-slides` |

Plus `rules/CLAUDE.md` — standing rules that must hold on every turn, not just
when a skill is invoked.

## Install (including on a new machine)

```bash
git clone --recurse-submodules git@github.com:max-a-ai/claude-skills.git ~/.claude-skills
~/.claude-skills/install.sh
```

That is the whole setup, on any machine. It installs three things into `~/.claude/`:

| | |
|---|---|
| `~/.claude/skills/` | 36 skills, symlinked back here |
| `~/.claude/CLAUDE.md` | standing rules, symlinked to `rules/CLAUDE.md` |
| `~/.claude/hooks/` + `hooks` entries in `settings.json` | the three enforcement hooks |

Everything lands in your **home directory**, never in a project. Your code repos
get no `.claude/` directory, no gitignore entry, and nothing to commit — `git
status` in them is unaffected. Only this repo tracks the skills.

The one prerequisite is [uv](https://docs.astral.sh/uv/). `ruff` and `mypy` do
**not** need to be on PATH; the hook runs them through uv.

## Why an installer is needed

Claude Code discovers skills **exactly one level deep**:

```
~/.claude/skills/<name>/SKILL.md        personal — every project
<repo>/.claude/skills/<name>/SKILL.md   project  — that repo only
```

It does not recurse. The nested layout here (`third_party/mattpocock-skills/skills/engineering/tdd/`)
is invisible to it, so `install.sh` flattens every leaf skill into `~/.claude/skills/`
as a symlink back into this repo.

Symlinks mean the repo stays the single source of truth: edit a skill here and it is
live everywhere immediately.

## Updating

```bash
git -C ~/.claude-skills pull --recurse-submodules && ~/.claude-skills/install.sh
```

Re-running `install.sh` is only needed when a set gains or loses a skill; edits to
existing skills are picked up through the symlinks with no action at all.

## Mirroring into a single repo

Only needed when collaborators or CI must get the skills without cloning this repo.
`--project` **copies** rather than symlinks, so the target is self-contained:

```bash
~/.claude-skills/install.sh --project ~/code/some-repo
```

## Enforcement hooks

Skills and `CLAUDE.md` state the rules; these three make them binding by failing
the tool call when one is broken. `install.sh` symlinks them into
`~/.claude/hooks/` and registers them in `settings.json` (idempotently).

| Hook | Event | Blocks |
|---|---|---|
| `lint_type_gate.sh` | `PostToolUse` on `Write\|Edit\|MultiEdit` | a `*.py` edit that leaves ruff or mypy errors |
| `enforce_wandb_training.sh` | `PreToolUse` on `Bash` | a `main.py` launch without `--wandb-project`/`--wandb-name` |
| `audit_gate.sh` | `Stop` | ending the turn with Python/config changes `general-codebase` has not audited |

`mark_audited.sh` clears the Stop gate after an audit passes; it re-arms on the
next Python edit. `_audit_state.sh` is the shared fingerprint library — both use
it so they cannot disagree about what "audited" means.

### The ruff/mypy gate

`hooks/lint_type_gate.sh` runs as a `PostToolUse` hook on `Write|Edit|MultiEdit`.
After Claude touches any `*.py` file inside a project with a `pyproject.toml` it:

1. runs `ruff check --fix` then `ruff format` — most issues vanish mechanically;
2. runs `mypy` when the project declares a config **and** has a venv;
3. exits non-zero on anything left, feeding the errors back so Claude must fix
   them before continuing.

Tools resolve through uv: a project with `uv.lock` or `.venv` uses its own pinned
versions, otherwise ruff runs ephemerally via `uvx`. Mypy is skipped without a
project env, because type-checking with the dependencies missing reports noise
rather than real errors — run `uv sync` first.

Escape hatches: `SKIP_TYPECHECK=1`, or a `.no-typecheck` file at the repo root.

### The wandb gate

Blocks any `main.py` launch that would not be logged. It also opens any `*.sh`
queue script named on the command line and rejects it if a job inside is missing
the flags — the classic "curves missing from wandb" bug, where the wrapper passes
them for the first job only. It cannot see into a script invoked indirectly.

Escape hatches: prefix `NO_WANDB=1` for a deliberate throwaway run, or use
`--phase test` for evaluation.

### The audit gate

Deliberately narrow, because a Stop hook that fires constantly gets turned off.
It only fires in a git repo, only when `*.py`/`pyproject.toml`/`*.yaml` differ
from HEAD, and never twice for the same state. The fingerprint hashes the
*content* of the changes, so editing an already-modified file re-arms the gate.
The marker lives in `.git/`, so it is never committed.

Escape hatches: `SKIP_AUDIT=1`, or a `.no-audit` file at the repo root.

Skip installing all hooks with `./install.sh --no-hooks`.

To get a *new* project set up with the matching config (uv, src layout, ruff at
line-length 79, mypy strict), run the `python-project-init` skill in it. The
`pyproject.toml` it writes **is** committed to that project — it is the project's
own config, not skill content.

## Repo layout and research data

Three private skills form a chain, split so that the rules have exactly one home:

| Skill | Role |
|---|---|
| `general-codebase-structure` | **the contract** — the canonical tree (`src/<module>/`, `.docs/`, `config-global.json`, gitignored `data/`+`checkpoints/`+`outputs/`) and the audit that checks a repo against it |
| `python-project-init` | **the scaffolder** — writes what the contract defines |
| `data-management` | **the data** — moves datasets and checkpoints onto NHR@FAU's Helma/Alex workspaces, and materialises `data/` differently on each machine |

`general-codebase` calls the structure audit alongside ruff, mypy and wandb, so
layout drift fails the same gate as a type error.

`data-management` exists because the NVMe Lustre workspaces on Helma and Alex
are limited by **inodes, not volume** (~50k soft / 75k hard per user, across all
workspaces). An unpacked image dataset blows that on its own, so the NAS stays
the single unpacked source of truth and the cluster only ever sees `.tar.zst`
shards that a job unpacks into `$TMPDIR`. Its `scripts/` are copied into each
project, not symlinked, so the version used for a run is committed beside it.

`obsidian-canvas` is a deliberate placeholder (`disable-model-invocation: true`)
holding the canvas template that `python-project-init` used to generate.

## Standing rules

A skill only loads when something triggers it, so a rule that must hold on *every*
turn cannot live in one. `rules/CLAUDE.md` is symlinked to `~/.claude/CLAUDE.md`
by the installer, which Claude Code reads into context in every session.

It currently fixes the git convention: one-line commit messages prefixed with one
of eight types (`add:`, `bug:`, `minor:`, `refactor:`, `docs:`, `test:`, `config:`,
`remove:`), no Claude attribution trailers, and no pushing — the owner pushes.

The commit convention is enforced in three layers: `rules/CLAUDE.md` states it,
`git-it` implements the interactive flow around it, and `general-codebase` audits
that commits actually followed it.

Skip the symlink with `./install.sh --no-rules`. An existing non-symlink
`~/.claude/CLAUDE.md` is never overwritten.

## Other commands

```bash
./install.sh --list      # what would be installed, grouped by set
./install.sh --dry-run   # print actions, touch nothing
./install.sh --prune     # also remove links left by skills that no longer exist
./install.sh --agents    # additionally link into ~/.agents/skills (Codex et al.)
```

## Configuration

Both lists live at the top of `install.sh`:

- **`SETS`** — which directories are scanned. Applied in order; on a name clash the
  first set wins, so `skills/` always beats a third-party skill. Clashes are reported,
  never silent.
- **`SKIP`** — skills to leave out. Currently `code-review`, because Matt's version
  would shadow Claude Code's built-in `/code-review` (which has `ultra` mode).

Deliberately not installed from `mattpocock-skills`: `deprecated/`, `in-progress/`,
`misc/` (TypeScript/Husky-specific) and `personal/`. Add a line to `SETS` to pull any
of them in. Not installed from `research-skills`: `token-usage`, superseded by the
built-in `/usage`.

## Note on the plugin

`mattpocock/skills` also ships as a Claude Code plugin. Do not enable it alongside
this repo — every skill would appear twice, once flat and once namespaced as
`mattpocock-skills:*`. This repo is the symlink route; pick one.
