#!/usr/bin/env bash
#
# PreToolUse hook (Bash) — git guard.
#
# Hard rules (no escape hatch by design; the user asked for this):
#   1. Claude never pushes. Any `git push` is refused; print the command for the
#      user instead.
#   2. Commits are one line: `<prefix> <description>` with prefix in
#      add|bug|minor|refactor|docs|test|config|remove, <= 72 chars, no body,
#      no second -m, no -F/--file, no heredoc, and never a Co-Authored-By /
#      Claude-Session / "Generated with" trailer.
#   3. The author stays the user: no --author, no -c user.name/user.email
#      overrides, no `git config user.*` changes.
#
# Exit 0: allowed.  Exit 2: blocked — stderr goes back to Claude.
#
set -uo pipefail

cmd="$(cat | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null)"
[ -n "$cmd" ] || exit 0
printf '%s' "$cmd" | grep -qE '(^|[^A-Za-z0-9_.-])git([[:space:]]|$)' || exit 0

block() {
  printf 'git guard: %s\n\n%s\n' "$1" "$2" >&2
  exit 2
}

# --- 1. never push -----------------------------------------------------------
# Deliberately coarse: any whole-word `push` after a `git` word is refused, no
# matter which global flags (-C dir, -c k=v, --git-dir ...) sit in between.
if printf '%s' "$cmd" | grep -qE '(^|[^A-Za-z0-9_.-])git[[:space:]]+(.*[[:space:]])?push([^A-Za-z0-9_-]|$)'; then
  block "Claude never runs 'git push' (plain, -u, --force, --force-with-lease, --tags, --mirror ...)." \
"Print the exact command in a fenced code block and let the user run it, e.g.
  git push -u origin <branch>"
fi

# --- 3. author stays the user ------------------------------------------------
if printf '%s' "$cmd" | grep -qE -- '--author[= ]|user\.name=|user\.email=|git[[:space:]]+config[[:space:]]+(--global[[:space:]]+|--local[[:space:]]+)?user\.'; then
  block "commits are authored by the user, never with an overridden name/email." \
"Drop --author / -c user.name / -c user.email / git config user.* from the command."
fi

# --- 2. commit message shape -------------------------------------------------
printf '%s' "$cmd" | grep -qE '(^|[^A-Za-z0-9_.-])git[[:space:]]+(.*[[:space:]])?commit([[:space:]]|$)' || exit 0

if printf '%s' "$cmd" | grep -qiE 'co-authored-by|claude-session|generated with'; then
  block "commit messages never carry Co-Authored-By / Claude-Session / 'Generated with' trailers." \
"Use exactly one line:  git commit -m \"<prefix> <description>\""
fi
if printf '%s' "$cmd" | grep -qE -- '(^|[[:space:]])(-F|--file)([[:space:]=]|$)|<<'; then
  block "commit messages are one line; no -F/--file and no heredoc bodies." \
"Use exactly one line:  git commit -m \"<prefix> <description>\""
fi
if printf '%s' "$cmd" | grep -qE -- '(^|[[:space:]])(-m|--message)([[:space:]=])'; then
  n_m="$(printf '%s' "$cmd" | grep -oE -- '(^|[[:space:]])(-m|--message)([[:space:]=])' | wc -l)"
  [ "$n_m" -le 1 ] || block "more than one -m creates a multi-paragraph message; one line only." \
"Use exactly one line:  git commit -m \"<prefix> <description>\""
  msg="$(printf '%s' "$cmd" | python3 -c '
import re,shlex,sys
cmd=sys.stdin.read()
try: toks=shlex.split(cmd, posix=True)
except ValueError: toks=cmd.split()
for i,t in enumerate(toks):
    if t in ("-m","--message") and i+1<len(toks): print(toks[i+1]); break
    if t.startswith("-m") and len(t)>2 and not t.startswith("--"): print(t[2:]); break
    if t.startswith("--message="): print(t[len("--message="):]); break
' 2>/dev/null)"
  if [ -n "$msg" ]; then
    case "$msg" in *$'\n'*)
      block "the -m text contains a line break; one line only." "Subject only, no body." ;;
    esac
    if ! printf '%s' "$msg" | grep -qE '^(add|bug|minor|refactor|docs|test|config|remove): [a-z0-9]'; then
      block "subject must be '<prefix> <description>' with prefix in add|bug|minor|refactor|docs|test|config|remove, lowercase after the colon." \
"Got:  $msg
e.g.  git commit -m \"add: sanitized public export of lif\""
    fi
    if [ "${#msg}" -gt 72 ]; then
      block "subject is ${#msg} chars; keep it <= 72." "Got:  $msg"
    fi
    if printf '%s' "$msg" | grep -qE '\.$'; then
      block "no trailing period in the subject." "Got:  $msg"
    fi
  fi
fi

exit 0
