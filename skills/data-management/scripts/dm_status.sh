#!/usr/bin/env bash
# Report the lifetime of every workspace and flag the ones running out.
#
#   ./scripts/dm_status.sh [pattern]
#
# Run this FIRST, before any other data-management action. A workspace is
# deleted when its time runs out, and extensions are finite -- when they
# hit zero no ws_extend will save it. Recovery is: allocate a fresh
# workspace and re-push from the NAS, which only works because the NAS
# copy is never touched.
set -euo pipefail

DAYS_WARN="${DM_DAYS_WARN:-14}"
EXT_WARN="${DM_EXT_WARN:-2}"

command -v ws_list >/dev/null 2>&1 || {
  echo "error: ws_list not found -- run this on a Helma, Alex or Fritz frontend" >&2
  exit 1
}

ws_list ${1+"$1"} | awk -v dw="$DAYS_WARN" -v ew="$EXT_WARN" '
  /^id:/                    { name = $2 }
  /workspace directory/     { dir  = $NF }
  /remaining time/          { days = $(NF-3) }
  /available extensions/    {
      ext = $NF
      flag = ""
      if (days + 0 < dw) flag = flag " LOW-TIME"
      if (ext  + 0 < ew) flag = flag " LOW-EXTENSIONS"
      if (flag != "") bad++
      printf "%-24s %4s d  %3s ext  %s%s\n", name, days, ext, dir, flag
      if (flag != "") cmds = cmds sprintf("    ws_extend %s 90\n", name)
  }
  END {
      if (bad > 0) {
          printf "\n%d workspace(s) need attention:\n%s", bad, cmds
          printf "\nIf extensions are exhausted: ws_allocate a new workspace"
          printf " under a fresh name\nand re-push from the NAS.\n"
          exit 1
      }
      print "\nall workspaces healthy"
  }
'
