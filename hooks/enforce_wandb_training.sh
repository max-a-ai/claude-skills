#!/usr/bin/env bash
#
# PreToolUse hook (Bash) — refuse to launch a training run that would not be
# logged to Weights & Biases.
#
# Exit 0: allowed.
# Exit 2: blocked — stderr goes back to Claude, which must re-issue the command
#         with the flags.
#
# Escape hatches, per the wandb-training skill:
#   NO_WANDB=1 <command>   deliberate throwaway debug run
#   --phase test           evaluation only, no training
#
set -uo pipefail

cmd="$(cat | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null)"
[ -n "$cmd" ] || exit 0

# Deliberate opt-outs, checked before anything else.
case "$cmd" in
  *NO_WANDB=1*)   exit 0 ;;
  *--phase\ test*) exit 0 ;;
esac

block() {
  printf 'wandb gate: %s\n\n%s\n' "$1" "$2" >&2
  echo "Escape hatches: prefix NO_WANDB=1 for a throwaway debug run, or use --phase test for eval." >&2
  exit 2
}

# --- 1. A direct main.py launch -------------------------------------------
if printf '%s' "$cmd" | grep -qE '(^|[[:space:]/])main\.py([[:space:]]|$)'; then
  if ! printf '%s' "$cmd" | grep -q -- '--wandb-project'; then
    block "this launches main.py without --wandb-project, so the run would not appear in wandb." \
"Add both flags:
  --wandb-project action6 --wandb-name <descriptive-run-name>"
  fi
  if ! printf '%s' "$cmd" | grep -q -- '--wandb-name'; then
    block "--wandb-project is set but --wandb-name is missing." \
"An unnamed run is nearly impossible to find later. Add:
  --wandb-name <descriptive-run-name>"
  fi
fi

# --- 2. A queue/batch script that launches main.py inside ------------------
# The classic "curves missing from wandb" bug: the wrapper passes the flags for
# the first job only, or not at all. The hook cannot see inside a running
# script, so inspect it before it starts.
for tok in $cmd; do
  case "$tok" in
    *.sh) ;;
    *) continue ;;
  esac
  [ -f "$tok" ] || continue
  grep -qE '(^|[[:space:]/])main\.py' "$tok" || continue
  bad="$(grep -nE '(^|[[:space:]/])main\.py' "$tok" | grep -v -- '--wandb-project' || true)"
  if [ -n "$bad" ]; then
    block "$tok launches main.py without --wandb-project on these lines:" \
"$bad

Every job in a queue needs its own --wandb-project/--wandb-name, not just the first."
  fi
done

exit 0
