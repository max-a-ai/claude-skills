#!/usr/bin/env bash
#
# Flattens every skill in this repo into a directory Claude Code actually reads.
#
# Claude Code discovers skills exactly one level deep:
#     ~/.claude/skills/<name>/SKILL.md      (personal — every project, every session)
#     <repo>/.claude/skills/<name>/SKILL.md (project  — that repo only)
#
# It does NOT recurse, so the nested layout in this repo (skills/, vendor/*/skills/
# engineering/…) is invisible to it. This script bridges that gap.
#
# Usage:
#   ./install.sh                  symlink all skills into ~/.claude/skills
#   ./install.sh --project PATH   COPY all skills into PATH/.claude/skills
#   ./install.sh --agents         also link into ~/.agents/skills (Codex et al.)
#   ./install.sh --list           show what would be installed, grouped by set
#   ./install.sh --dry-run        print actions without touching anything
#   ./install.sh --prune          also remove stale links left by earlier runs
#
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# What gets installed. Each entry is "<label>:<glob of directories>".
# A directory qualifies only if it contains a SKILL.md.
# ---------------------------------------------------------------------------
SETS=(
  "private:$REPO/skills/*"
  "mattpocock:$REPO/vendor/mattpocock-skills/skills/engineering/*"
  "mattpocock:$REPO/vendor/mattpocock-skills/skills/productivity/*"
  "research:$REPO/vendor/research-skills/plugins/research-collaborator/skills/*"
  "research:$REPO/vendor/research-skills/plugins/results-to-slides/skills/*"
)

# Skills to leave out. Add or remove a line and re-run.
SKIP=(
  code-review   # shadows Claude Code's built-in /code-review (which has ultra mode)
)

# Sets are applied in order; on a name clash the FIRST set wins, so your own
# skills always beat a vendored one. Clashes are reported, never silent.
# ---------------------------------------------------------------------------

MODE=link
PROJECT=""
DRY=0
PRUNE=0
LIST=0
DESTS=("$HOME/.claude/skills")

while [ $# -gt 0 ]; do
  case "$1" in
    --project) MODE=copy; PROJECT="${2:-}"; shift 2
               [ -n "$PROJECT" ] || { echo "error: --project needs a path" >&2; exit 1; }
               DESTS=("${PROJECT%/}/.claude/skills") ;;
    --agents)  DESTS+=("$HOME/.agents/skills"); shift ;;
    --dry-run) DRY=1; shift ;;
    --prune)   PRUNE=1; shift ;;
    --list)    LIST=1; shift ;;
    -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "error: unknown flag $1" >&2; exit 1 ;;
  esac
done

skipped() { local n="$1"; for s in "${SKIP[@]}"; do [ "$s" = "$n" ] && return 0; done; return 1; }

# --- collect -----------------------------------------------------------------
names=(); srcs=(); labels=()
claimed=""   # newline-separated "name<TAB>label" of what we've already taken

for entry in "${SETS[@]}"; do
  label="${entry%%:*}"; glob="${entry#*:}"
  for dir in $glob; do
    [ -f "$dir/SKILL.md" ] || continue
    name="$(basename "$dir")"
    skipped "$name" && continue
    prior="$(printf '%s\n' "$claimed" | awk -F'\t' -v n="$name" '$1==n {print $2; exit}')"
    if [ -n "$prior" ]; then
      echo "clash: '$name' provided by both '$prior' and '$label' — keeping '$prior'" >&2
      continue
    fi
    claimed="$claimed"$'\n'"$name"$'\t'"$label"
    names+=("$name"); srcs+=("$dir"); labels+=("$label")
  done
done

if [ "$LIST" = 1 ]; then
  for set_label in private mattpocock research; do
    printf '\n%s\n' "$set_label"
    for i in "${!names[@]}"; do
      [ "${labels[$i]}" = "$set_label" ] && printf '  %s\n' "${names[$i]}"
    done
  done
  printf '\n%d skills. skipped: %s\n' "${#names[@]}" "${SKIP[*]:-none}"
  exit 0
fi

# --- install -----------------------------------------------------------------
for DEST in "${DESTS[@]}"; do
  # A symlinked DEST that resolves back into this repo would make us write the
  # per-skill links into our own working tree. Refuse rather than corrupt it.
  if [ -L "$DEST" ]; then
    resolved="$(cd "$(dirname "$DEST")" && cd "$(readlink "$DEST")" && pwd)"
    case "$resolved" in
      "$REPO"|"$REPO"/*)
        echo "error: $DEST is a symlink into this repo ($resolved). rm it and re-run." >&2
        exit 1 ;;
    esac
  fi

  [ "$DRY" = 1 ] || mkdir -p "$DEST"
  echo "→ $DEST  (${MODE})"

  for i in "${!names[@]}"; do
    name="${names[$i]}"; src="${srcs[$i]}"; target="$DEST/$name"
    if [ "$DRY" = 1 ]; then
      echo "   would $MODE $name"
      continue
    fi
    rm -rf "$target"
    if [ "$MODE" = copy ]; then
      cp -R "$src" "$target"          # copies, so collaborators/CI don't need this repo
    else
      ln -sfn "$src" "$target"        # symlink, so `git pull` is the whole update story
    fi
    printf '   %-34s %s\n' "$name" "${labels[$i]}"
  done

  if [ "$PRUNE" = 1 ] && [ "$MODE" = link ]; then
    for target in "$DEST"/*; do
      [ -L "$target" ] || continue
      dest_of="$(readlink "$target")"
      case "$dest_of" in "$REPO"/*) [ -e "$target" ] || { rm -f "$target"; echo "   pruned $(basename "$target")"; };; esac
    done
  fi
done

echo
echo "${#names[@]} skills installed. Skipped: ${SKIP[*]:-none}"
[ "$MODE" = link ] && echo "Update everything later with: git -C \"$REPO\" pull --recurse-submodules && \"$REPO/install.sh\""
