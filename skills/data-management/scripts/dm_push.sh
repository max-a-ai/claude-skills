#!/usr/bin/env bash
# Push a packed dataset to its workspace on Helma or Alex and verify it.
#
#   ./scripts/dm_push.sh <dataset> <helma|alex>
#
# Runs from the workstation. The ssh aliases in ~/.ssh/config already
# ProxyJump through csnhr.nhr.fau.de, so nothing extra is needed here.
# Deliberately no `rsync -z`: the payload is already zstd, and NHR@FAU
# warn that compression can make transfers between their systems slower.
set -euo pipefail

DATASET="${1:?usage: dm_push.sh <dataset> <helma|alex>}"
HOST="${2:?usage: dm_push.sh <dataset> <helma|alex>}"

case "$HOST" in
  helma | alex) ;;
  *) echo "error: host must be helma or alex, got '$HOST'" >&2; exit 1 ;;
esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFG="$ROOT/config-global.json"
[[ -f "$CFG" ]] || { echo "error: no config-global.json at $ROOT" >&2; exit 1; }

read -r NAS PACKROOT WS < <(python3 - "$CFG" "$DATASET" "$HOST" <<'PY'
import json, sys
from pathlib import Path

cfg = json.loads(Path(sys.argv[1]).read_text())
dataset, host = sys.argv[2], sys.argv[3]
nas = Path(cfg.get("nas_root", "~/nas_drive")).expanduser()
pack = cfg.get("pack_root", "_packed")
workspaces = cfg.get("workspaces", {})
if dataset not in cfg.get("datasets", {}):
    sys.exit(f"dataset {dataset!r} is not declared in config-global.json")
if host not in workspaces:
    sys.exit(f"no workspaces.{host} entry in config-global.json")
print(nas, pack, workspaces[host])
PY
)

SRC="$NAS/$PACKROOT/$DATASET"
[[ -d "$SRC" ]] || { echo "error: $SRC not found -- run dm_pack.py first" >&2; exit 1; }
[[ -f "$SRC/sha256sums.txt" ]] || { echo "error: $SRC has no sha256sums.txt" >&2; exit 1; }

echo "resolving workspace '$WS' on $HOST ..."
WSPATH="$(ssh "$HOST" "ws_find $WS" | tr -d '\r')"
if [[ -z "$WSPATH" ]]; then
  echo "error: workspace '$WS' does not exist on $HOST. Allocate it yourself:" >&2
  echo "    ws_allocate $WS 90 -r 7 -m <your-email>" >&2
  exit 1
fi
DEST="$WSPATH/data/$DATASET"
echo "destination: $HOST:$DEST"

ssh "$HOST" "mkdir -p '$DEST'"
rsync -a --partial --append-verify --info=progress2 \
  -e ssh "$SRC/" "$HOST:$DEST/"

echo "verifying checksums on $HOST ..."
ssh "$HOST" "cd '$DEST' && sha256sum -c sha256sums.txt --quiet"
echo "OK: $DATASET verified in $DEST"
