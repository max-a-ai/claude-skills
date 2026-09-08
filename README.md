# claude-skills

One skill repository, cloned once, available in every project.

Combines three sources:

| Set | Source | Contents |
|---|---|---|
| `skills/` | mine | 7 private skills — Python/ML workflow (ruff, mypy, wandb, project init, graphify, git-it, the standing-rules auditor) |
| `vendor/mattpocock-skills/` | [mattpocock/skills](https://github.com/mattpocock/skills) (submodule) | The engineering loop — grilling, spec/ticket flows, TDD, domain modelling, diagnosis |
| `vendor/research-skills/` | [saidwivedi/research-skills](https://github.com/saidwivedi/research-skills) (submodule) | `research-collaborator` (hypothesis falsification, 191 silent-bug patterns) and `results-to-slides` |

Plus `rules/CLAUDE.md` — standing rules that must hold on every turn, not just
when a skill is invoked.

## Install

```bash
git clone --recurse-submodules git@github.com:max-a-ai/claude-skills.git ~/.claude-skills
~/.claude-skills/install.sh
```

That is the whole setup. It is global — every project, every session, no per-repo cloning.

## Why an installer is needed

Claude Code discovers skills **exactly one level deep**:

```
~/.claude/skills/<name>/SKILL.md        personal — every project
<repo>/.claude/skills/<name>/SKILL.md   project  — that repo only
```

It does not recurse. The nested layout here (`vendor/mattpocock-skills/skills/engineering/tdd/`)
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
  first set wins, so `skills/` always beats a vendored skill. Clashes are reported,
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
