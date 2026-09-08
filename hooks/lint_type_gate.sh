#!/usr/bin/env bash
#
# PostToolUse hook — ruff autofix + format, then mypy, on every Python file
# Claude writes or edits.
#
# Exit 0: clean, or genuinely not applicable.
# Exit 2: problems remain — stderr is fed back to Claude, which must fix them
#         before continuing. This is what makes "ruff/mypy clean" a rule rather
#         than a suggestion.
#
# ruff and mypy are deliberately NOT required on PATH: they are run through uv.
# A project with its own venv/lock uses its pinned versions; otherwise ruff runs
# ephemerally via uvx. mypy is skipped when there is no project environment,
# because type-checking without the project's dependencies installed produces
# noise rather than signal.
#
# Escape hatches: SKIP_TYPECHECK=1 in the environment, or a `.no-typecheck`
# file at the repo root.
#
set -uo pipefail

input="$(cat)"
file="$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)"

[ -n "$file" ] || exit 0
case "$file" in *.py) ;; *) exit 0 ;; esac
[ -f "$file" ] || exit 0
[ "${SKIP_TYPECHECK:-0}" = "1" ] && exit 0

# Walk up for the project root; without a pyproject.toml this is not a uv project.
root="$(cd "$(dirname "$file")" && pwd)"
while [ "$root" != "/" ] && [ ! -f "$root/pyproject.toml" ]; do
  root="$(dirname "$root")"
done
[ -f "$root/pyproject.toml" ] || exit 0
[ -f "$root/.no-typecheck" ] && exit 0

if ! command -v uv >/dev/null 2>&1; then
  echo "lint/type gate: uv is not on PATH, so ruff/mypy cannot run." >&2
  echo "Install it (https://docs.astral.sh/uv/) or set SKIP_TYPECHECK=1." >&2
  exit 2
fi

has_env=0
{ [ -f "$root/uv.lock" ] || [ -d "$root/.venv" ]; } && has_env=1

# Run TOOL from the project env when it is available there, else ephemerally.
run_tool() {
  local tool="$1"; shift
  if [ "$has_env" = 1 ] && (cd "$root" && uv run --quiet "$tool" --version) >/dev/null 2>&1; then
    (cd "$root" && uv run --quiet "$tool" "$@" 2>&1)
  else
    (cd "$root" && uvx --quiet "$tool" "$@" 2>&1)
  fi
}

rel="${file#"$root"/}"
problems=""

# 1. Ruff — no imports needed, so this always runs.
run_tool ruff check --fix --quiet "$rel" >/dev/null 2>&1
run_tool ruff format --quiet "$rel"      >/dev/null 2>&1
if ! out="$(run_tool ruff check "$rel")"; then
  problems="$problems

ruff:
$out"
fi

# 2. Mypy — only where configured AND a project env exists to resolve imports.
if grep -q '^\[tool\.mypy\]' "$root/pyproject.toml" 2>/dev/null \
   || [ -f "$root/mypy.ini" ] || [ -f "$root/.mypy.ini" ]; then
  if [ "$has_env" = 1 ]; then
    if ! out="$(run_tool mypy "$rel")"; then
      problems="$problems

mypy:
$out"
    fi
  else
    echo "lint/type gate: mypy configured but $root has no venv — run 'uv sync'." >&2
  fi
fi

if [ -n "$problems" ]; then
  printf 'lint/type gate failed for %s%s\n\nFix these before moving on.\n' "$rel" "$problems" >&2
  exit 2
fi
exit 0
