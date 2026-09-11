"""Shared helpers for the data-management scripts.

Stdlib only: these run on cluster login nodes where the repo venv may
not exist. Invoke with the system ``python3``.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any

ROLES = ("workstation", "lab", "helma", "alex")
CLUSTERS = ("helma", "alex")
IGNORED_DIRS = ("data", "checkpoints", "outputs")


class ConfigError(RuntimeError):
    """Raised when the repo or its config-global.json is unusable."""


def entries(section: Any) -> dict[str, Any]:
    """Return a config section without its ``_``-prefixed keys.

    Underscore keys are comments and shipped examples; they must never
    be treated as real datasets, checkpoints or methods.
    """
    if not isinstance(section, dict):
        return {}
    return {
        k: v
        for k, v in section.items()
        if isinstance(k, str) and not k.startswith("_")
    }


def repo_root(start: Path | None = None) -> Path:
    """Walk up from *start* to the directory holding config-global.json."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "config-global.json").is_file():
            return candidate
    raise ConfigError(
        "no config-global.json found in this directory or any parent; "
        "run from inside a repo laid out by general-codebase-structure"
    )


def load_config(root: Path) -> dict[str, Any]:
    path = root / "config-global.json"
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a JSON object")
    return data


def nas_root(cfg: dict[str, Any]) -> Path:
    raw = cfg.get("nas_root", "~/nas_drive")
    if not isinstance(raw, str):
        raise ConfigError("nas_root must be a string")
    return Path(raw).expanduser()


def detect_machine(cfg: dict[str, Any]) -> str:
    """Resolve which machine role we are running on.

    Order: explicit ``DM_MACHINE`` override, then the NVMe mount points
    that only exist on the NHR clusters, then the hostname table in
    config-global.json, then "is the NAS mounted". Anything left over is
    a hard error -- guessing here means writing terabytes to the wrong
    filesystem.
    """
    override = os.environ.get("DM_MACHINE")
    if override:
        if override not in ROLES:
            raise ConfigError(f"DM_MACHINE={override!r} is not one of {ROLES}")
        return override

    if Path("/hnvme").is_dir():
        return "helma"
    if Path("/anvme").is_dir():
        return "alex"

    host = socket.gethostname().split(".")[0]
    role = entries(cfg.get("machines")).get(host)
    if isinstance(role, str):
        if role not in ROLES:
            raise ConfigError(
                f"machines.{host} = {role!r} is not one of {ROLES}"
            )
        return role

    if nas_root(cfg).is_dir():
        return "workstation"

    raise ConfigError(
        f"cannot place host {host!r}: no /hnvme or /anvme, no entry under "
        f'"machines" in config-global.json, and {nas_root(cfg)} is not '
        "mounted. Add the hostname to the machines table or set "
        "DM_MACHINE."
    )


def workspace_dir(name: str) -> Path:
    """Resolve a workspace with ``ws_find``; never allocate one."""
    if shutil.which("ws_find") is None:
        raise ConfigError(
            "ws_find is not on PATH -- run this on a Helma, Alex or Fritz "
            "frontend"
        )
    proc = subprocess.run(
        ["ws_find", name],
        capture_output=True,
        text=True,
        check=False,
    )
    path = proc.stdout.strip()
    if proc.returncode != 0 or not path:
        raise ConfigError(
            f"workspace {name!r} does not exist. Allocate it yourself:\n"
            f"    ws_allocate {name} 90 -r 7 -m <your-email>"
        )
    return Path(path)


def pack_dir(cfg: dict[str, Any], dataset: str) -> Path:
    """Where packed shards for *dataset* live on the NAS."""
    sub = cfg.get("pack_root", "_packed")
    if not isinstance(sub, str):
        raise ConfigError("pack_root must be a string")
    return nas_root(cfg) / sub / dataset


def dataset_source(cfg: dict[str, Any], dataset: str) -> Path:
    spec = entries(cfg.get("datasets")).get(dataset)
    if not isinstance(spec, dict) or "nas" not in spec:
        raise ConfigError(
            f"dataset {dataset!r} is not declared in config-global.json"
        )
    return nas_root(cfg) / str(spec["nas"])


def shard_count(cfg: dict[str, Any], dataset: str) -> int:
    spec = entries(cfg.get("datasets")).get(dataset, {})
    raw = spec.get("shards", 24) if isinstance(spec, dict) else 24
    count = int(raw)
    if count < 1:
        raise ConfigError(f"dataset {dataset!r}: shards must be >= 1")
    return count


def relative_files(root: Path, skip: set[str] | None = None) -> list[str]:
    """Sorted POSIX-relative paths of every regular file under *root*."""
    skipped = skip or set()
    out: list[str] = []
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] in skipped:
            continue
        out.append(rel.as_posix())
    out.sort()
    return out
