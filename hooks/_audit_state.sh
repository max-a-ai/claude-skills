#!/usr/bin/env bash
# Shared by audit_gate.sh and mark_audited.sh so the two can never disagree
# about what "the current state" means.

# Only these files can trip the gate. A docs-only change must never fire it.
AUDIT_PATHS=('*.py' 'pyproject.toml' 'mypy.ini' '*.yaml' '*.yml')

# audit_repo_root <dir> — prints the git root, or nothing if not a repo.
audit_repo_root() { git -C "$1" rev-parse --show-toplevel 2>/dev/null; }

# audit_relevant <root> — the relevant files that differ from HEAD, for display.
audit_relevant() {
  git -C "$1" status --porcelain -- "${AUDIT_PATHS[@]}" 2>/dev/null
}

# audit_fingerprint <root> — hash of HEAD plus the *content* of every relevant
# change. Hashing `git status` alone is not enough: its output is unchanged when
# an already-modified file is edited again, which would let the gate stay
# cleared while more code is written.
audit_fingerprint() {
  local root="$1"
  {
    git -C "$root" rev-parse HEAD 2>/dev/null
    git -C "$root" diff HEAD -- "${AUDIT_PATHS[@]}" 2>/dev/null
    git -C "$root" ls-files --others --exclude-standard -- "${AUDIT_PATHS[@]}" 2>/dev/null \
      | while IFS= read -r f; do shasum "$root/$f" 2>/dev/null; done
  } | shasum | awk '{print $1}'
}

audit_marker() { echo "$1/.git/claude-audit-state"; }
