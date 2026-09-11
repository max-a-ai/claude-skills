#!/usr/bin/env bash
# Add (or refresh) this repo's navigation aliases in ~/.bash_aliases.
#
#   ./scripts/dm_alias.sh
#
# Writes a single delimited block that is rewritten wholesale on every
# run. Hand-written lines outside the block are never touched, and the
# file is backed up first -- a broken .bash_aliases breaks your login
# shell, so this never does a free-form in-place edit.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFG="$ROOT/config-global.json"
[[ -f "$CFG" ]] || { echo "error: no config-global.json at $ROOT" >&2; exit 1; }

REPO="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["repo"])' "$CFG")"
TARGET="$ROOT"

# On a cluster the repo root IS the workspace root; prefer the resolved
# workspace path so the alias keeps working if the workspace is re-created.
if command -v ws_find >/dev/null 2>&1; then
  WS="$(python3 - "$CFG" <<'PY'
import json, sys, pathlib, subprocess
cfg = json.loads(pathlib.Path(sys.argv[1]).read_text())
for host in ("helma", "alex"):
    name = cfg.get("workspaces", {}).get(host)
    if not name:
        continue
    out = subprocess.run(["ws_find", name], capture_output=True, text=True)
    if out.returncode == 0 and out.stdout.strip():
        print(out.stdout.strip())
        break
PY
)"
  [[ -n "$WS" ]] && TARGET="$WS"
fi

FILE="$HOME/.bash_aliases"
BEGIN="# >>> data-management: $REPO >>>"
END="# <<< data-management: $REPO <<<"

touch "$FILE"
cp "$FILE" "$FILE.bak"

python3 - "$FILE" "$BEGIN" "$END" "$REPO" "$TARGET" <<'PY'
import pathlib, sys

path, begin, end, repo, target = (
    pathlib.Path(sys.argv[1]), *sys.argv[2:6]
)
block = "\n".join([
    begin,
    f"alias cd{repo}='cd {target}'",
    f"alias out{repo}='cd {target}/outputs'",
    f"taillast{repo}() {{ f=$(ls -t {target}/outputs/*/*.txt 2>/dev/null "
    "| head -n 1); echo \"CHECKING: $f\"; tail -n 20 -f \"$f\"; }",
    end,
])

lines = path.read_text(encoding="utf-8").splitlines()
if begin in lines and end in lines:
    i, j = lines.index(begin), lines.index(end)
    lines[i : j + 1] = block.splitlines()
else:
    if lines and lines[-1].strip():
        lines.append("")
    lines.extend(block.splitlines())
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

echo "updated $FILE (backup at $FILE.bak)"
echo "  cd$REPO -> $TARGET"
echo "run 'source ~/.bash_aliases' or open a new shell"
