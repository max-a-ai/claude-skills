#!/usr/bin/env bash
#
# Stop hook — refuse to end the turn while Python or config changes sit
# un-audited, so `general-codebase` actually runs before "done" is claimed.
#
# Exit 0: nothing to audit, or already audited at this exact state.
# Exit 2: audit required — stderr tells Claude to run the skill.
#
# Deliberately narrow, because a Stop hook that fires constantly gets disabled:
#   - only in a git repo
#   - only when *.py / pyproject.toml / *.yaml differ from HEAD
#   - never twice for the same state (fingerprint marker)
#   - never when already re-entered (stop_hook_active)
#
# Escape hatches: SKIP_AUDIT=1, or a `.no-audit` file at the repo root.
#
set -uo pipefail
. "$(dirname "$(readlink "${BASH_SOURCE[0]}" || echo "${BASH_SOURCE[0]}")")/_audit_state.sh" 2>/dev/null \
  || . "$(dirname "${BASH_SOURCE[0]}")/_audit_state.sh"

input="$(cat)"
active="$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("stop_hook_active",False))' 2>/dev/null)"
[ "$active" = "True" ] && exit 0          # already re-entered; do not loop
[ "${SKIP_AUDIT:-0}" = "1" ] && exit 0

cwd="$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("cwd",""))' 2>/dev/null)"
[ -n "$cwd" ] || cwd="$PWD"

root="$(audit_repo_root "$cwd")"
[ -n "$root" ] || exit 0
[ -f "$root/.no-audit" ] && exit 0

changed="$(audit_relevant "$root")"
[ -n "$changed" ] || exit 0               # nothing auditable changed

marker="$(audit_marker "$root")"
now="$(audit_fingerprint "$root")"
[ -f "$marker" ] && [ "$(cat "$marker")" = "$now" ] && exit 0

{
  echo "audit gate: Python/config files changed but general-codebase has not run."
  echo
  echo "$changed"
  echo
  echo "Run the general-codebase skill, then clear the gate with:"
  echo "  ~/.claude/hooks/mark_audited.sh"
  echo "Skip once with SKIP_AUDIT=1, or permanently for this repo with .no-audit."
} >&2
exit 2
