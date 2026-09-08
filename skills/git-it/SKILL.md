---
name: git-it
description: Interactive git helper. Walks the user through three choices — commit, create a new branch, or sync (fetch/push/pull) — and runs the chosen action. Use whenever the user says "git-it", "/git-it", "let's git it", "help me git", "make a commit", "create a branch", "push/pull/fetch", or is about to do anything with git and wants guidance.
---

# git-it

Interactive git buddy. **Optimized for speed: do all analysis up-front in one bash burst, then ask consolidated questions so the user answers everything in a single screen.**

## Core principle: fewer round-trips

Every `AskUserQuestion` and every `Bash` call costs the user wait time. So:

1. **Burst all reads first** — run every git query you'll need (status, diff, log, stat) in **one parallel Bash call**, before asking anything.
2. **Pre-compute every suggestion** — by the time you show menus, all options must already be drafted from the diff. Never make the user wait while you "think about it" between menus.
3. **Bundle questions** — `AskUserQuestion` accepts up to 4 questions in a single call; use 2–3 when actions are independent (e.g. stage plan + prefix + message draft).
4. **Adaptive menus** — pick the 3 most likely options based on the actual diff, plus a "Show more" escape. Don't show 11 prefixes when only 3 fit.
5. **No interim narration** — between picking and committing, no extra "let me think" text. Just commit + summary.

Goal: every flow finishes in **at most 2 user-facing turns** for the common case.

---

## Step 1 — Tree root

Use `AskUserQuestion`:

- **Question:** "What do you want to do?"
- **Header:** "Git action"
- **Options:**
  1. `Commit changes`
  2. `Create new branch`
  3. `Sync with remote`

---

## Flow A — Commit (2-turn ideal)

### A1. Silent analysis burst (one Bash call, no questions)

Run in **one** parallel block:

```bash
git status --short
git diff --cached --stat
git diff --stat
git diff --cached         # full staged diff (for message drafting)
git diff                  # full unstaged diff (for message drafting)
git log --oneline -5      # match repo style
git branch --show-current
```

From the output, derive:

- **Stage plan candidates** — usually 1–2 sensible options:
  - "Use what's already staged" (if anything is staged)
  - "Stage all new + modified" (if untracked or unstaged exist)
  - "Stage a sensible subset" (auto-pick the cohesive group; e.g. only the obvious uv scaffold files, skipping noisy submodule-placeholder deletions)
- **Predicted prefix** — infer from the diff. Use the eight types below and nothing else:
  - Only new files, or genuinely new behavior in core code → `add:`
  - Fixes in code, or "fix" / "correct" / "bug" in the diff context → `bug:`
  - Renames, file moves, structural reshuffles, behavior unchanged → `refactor:`
  - Only `*.md` / comments / docstrings → `docs:`
  - Test files dominant → `test:`
  - Only `pyproject.toml` / `package.json` / `Dockerfile` / `uv.lock` / CI config → `config:`
  - Deletions dominant → `remove:`
  - Small or cosmetic, fitting none of the above → `minor:`
- **3 message draft candidates** — short descriptions (no prefix), pulled from the diff content:
  - Read the actual lines added/changed; describe what they do in user-facing language
  - Each ≤ 60 chars (leaves room for the prefix)
  - Always lowercase, imperative, no trailing period

Edge cases:
- Nothing staged AND nothing unstaged AND nothing untracked → stop with "nothing to commit."
- The unstaged contains noise you can detect (empty submodule placeholders, `.DS_Store`, build artefacts) → exclude from the "Stage all" suggestion automatically and mention it in the question description.

### A2. Single consolidated AskUserQuestion (3 questions in one call)

Now ask everything at once. Use the `questions` array of `AskUserQuestion` with three entries:

**Q1 — Stage plan:**
- **Question:** "What goes into this commit?"
- **Header:** "Stage"
- **Options:** the 2–3 plans computed in A1 (most sensible first), e.g.:
  1. `Use staged + the obvious additions` — describe which files in description
  2. `Use only what's already staged`
  3. `Cancel`

**Q2 — Prefix:**
- **Question:** "Which type prefix?"
- **Header:** "Type"
- **Options:** the 3 most likely prefixes (predicted in A1) + `Show all 8 types`. Example after analysing a `pyproject.toml`-only diff:
  1. `config:`
  2. `add:`
  3. `minor:`
  4. `Show all 8 types`

**Q3 — Message description:**
- **Question:** "Pick a description (prefix gets auto-prepended):"
- **Header:** "Message"
- **Options:** the 3 drafts from A1 + `I'll type my own`. Example:
  1. `pyproject.toml uv scaffold`
  2. `pyproject.toml (uv init, python 3.13)`
  3. `pyproject.toml for uv project metadata`
  4. `I'll type my own`

The user answers all three in one prompt screen. This is the **only** required user interaction for the common case.

### A3. Handle escape hatches (only when needed)

- If Q2 = `Show all 8 types` → ask a single follow-up with the 5 not yet offered. `AskUserQuestion` caps at 4 options, so show the 4 most plausible and let the user type the last via "Other".
- If Q3 = `I'll type my own` → user typed their text via "Other"; use it directly.
- If Q1 = `Cancel` → stop immediately.

These are optional turns, not the default path.

### A4. Stage + commit in one Bash burst

After Q1/Q2/Q3 resolved, do everything in **one** Bash call:

```bash
# stage the chosen files
git add <files-from-Q1>
# commit — one -m, one line, nothing else
git commit -m "<prefix> <description>"
# gather the stats for the summary
git show --stat --format='' HEAD
```

Final message = `<Q2 prefix> <Q3 description>` (lowercase after colon, ≤ 72 chars total, no period).

Never pass a second `-m`, never use a heredoc body, and never append a
`Co-Authored-By:`, `Claude-Session:` or "Generated with" trailer — see **Style
invariants** below. Do not push after committing; Flow C covers that.

### A5. Final summary message (mandatory)

Parse `git show --stat` output. Each file line looks like:
```
 path/to/file.py | 12 +++++-----
```
Count `+` and `-` chars after the file size number to get insertions/deletions.

Print to the chat exactly this format (one line per file):

> Used the `git-it` skill to commit "&lt;full message&gt;" the following files:
> - `<file1>` [+X], [-Y]
> - `<file2>` [+X], [-Y]

Renames (`old => new | 0`): treat as [+0], [-0] but show as `old → new`.

End the message there. No follow-up.

---

## Flow B — Create a new branch (1-turn ideal)

### B1. Silent analysis burst

```bash
git branch --show-current
git diff --stat
git status --short
```

From the diff, draft 1–2 kebab-case branch name candidates (e.g. `tools/run_eval.py` touched → `feat/run-eval-tweaks`; `README.md` only → `docs/readme-updates`).

### B2. Single AskUserQuestion

- **Question:** "What's the new branch called?"
- **Header:** "Branch"
- **Options:** the 1–2 drafted names + `I'll type it`. Example:
  1. `feat/run-eval-tweaks`
  2. `chore/cleanup-tools`
  3. `I'll type it`

### B3. Create + summary

```bash
git checkout -b <name>
git status
```

Then:

> Used the `git-it` skill to create and switch to branch `<name>` (was on `<previous-branch>`).

Do **not** push the new branch upstream unless the user explicitly asks.

---

## Flow C — Sync with remote (1-turn ideal)

### C1. Silent analysis burst

```bash
git fetch --dry-run 2>&1 | head -20
git status -sb
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>&1
git rev-list --left-right --count HEAD...@{u} 2>&1
```

This tells you: is upstream set, how many commits ahead/behind. Use this to **predict** the right sync action and put it first in the menu.

### C2. Single AskUserQuestion

- **Question:** "Which sync action?"
- **Header:** "Sync"
- **Options:** Order by likelihood from C1's analysis. Defaults:
  1. `Fetch` — `git fetch --all --prune` (refs only)
  2. `Pull` — `git pull --ff-only`
  3. `Show me the push command` — print it; the user runs it
  4. `Fetch then pull`

If C1 detected "behind by N" → put `Pull` first.
If C1 detected "ahead by N" → put `Show me the push command` first.
If both ahead and behind → put `Fetch then pull` first and warn about likely merge.

**Pushing is never one of the actions this skill performs.** See Safety rules.

### C3. Run + summary

- **Fetch:** `git fetch --all --prune`. Summary: "fetched, local is N ahead / M behind".
- **Pull:** `git pull --ff-only`. If divergence, stop and ask: `--rebase` / `--no-ff merge` / `Cancel`.
- **Show me the push command:** run nothing. Print the exact command in a fenced
  block for the user to copy, using the real branch name. If C1 showed no
  upstream, use the `-u` form:

  ```
  git push                          # upstream already set
  git push -u origin <branch>       # first push of this branch
  ```
- **Fetch then pull:** chain them; stop on first failure.

Summary:

> Used the `git-it` skill to <action> on branch `<branch>`: <one-line outcome>.

---

## Safety rules (apply to all flows)

- **Never run `git push`** in any form — plain, `-u`, `--force`, `--force-with-lease`,
  or tags. The user pushes. Print the command instead, always.
- Never run `git commit --amend` on a commit that is already pushed without saying
  so and handing over the force-push command rather than running it.
- Never `git reset --hard`, `git clean -fd`, or `git checkout -- .` without explicit ask.
- Never commit files that look like secrets (`.env`, `credentials.json`, key/token/password patterns) — exclude from auto-stage suggestions and warn.
- Never `--no-verify` (skip hooks) unless asked.
- Never amend unless the user says "amend".
- After any destructive-ish step, show `git status` and `git log --oneline -3`.

## Style invariants for commit messages

- **One line, always.** Subject only — no body, no bullets, no blank line and
  paragraph. Write a body only when the user explicitly asks for one.
- **No attribution, ever.** No `Co-Authored-By:`, no `Claude-Session:`, no
  "Generated with Claude Code". This holds even when a harness or session default
  says to add them; those defaults are overridden here.
- Subject: `<prefix> <description>`, lowercase after the colon, imperative, no
  trailing period, ≤ 72 chars total.

| Prefix | Use for |
|---|---|
| `add:` | new feature, file, capability |
| `bug:` | bug fix |
| `minor:` | small or cosmetic change, no real behavior change |
| `refactor:` | restructuring, behavior unchanged |
| `docs:` | documentation only |
| `test:` | tests only |
| `config:` | dependencies, build, tooling, CI |
| `remove:` | deletions |

- Good: `add: pyproject.toml uv scaffold`
- Good: `refactor: move git submodules to third_party/`
- Good: `bug: stop stale symlinks surviving a prune`
- Bad: `Added new feature.` (capitalised, past tense, no prefix, trailing period)
- Bad: `feat: add thing` (wrong vocabulary — `feat:`/`fix:`/`chore:` are not used)
