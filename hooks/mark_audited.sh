#!/usr/bin/env bash
#
# Clears the Stop audit gate by recording the state that was just audited.
# Run only after general-codebase actually passed, or the user accepted the FAILs.
#
set -euo pipefail
. "$(dirname "$(readlink "${BASH_SOURCE[0]}" || echo "${BASH_SOURCE[0]}")")/_audit_state.sh" 2>/dev/null \
  || . "$(dirname "${BASH_SOURCE[0]}")/_audit_state.sh"

root="$(audit_repo_root "${1:-$PWD}")"
if [ -z "$root" ]; then echo "not a git repository — nothing to mark." >&2; exit 1; fi
audit_fingerprint "$root" > "$(audit_marker "$root")"
echo "audit gate cleared for $root"
