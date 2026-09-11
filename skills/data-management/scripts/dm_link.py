"""Materialise data/, checkpoints/ and outputs/ for this machine.

The same committed config-global.json produces a different layout on
every machine, so that only DATA_ROOT changes between a smoke run and a
cluster run:

    workstation  data/<ds>   -> symlink into the NAS
    lab          data/<ds>   -> a real copy (cluster1 / cluster2)
    helma, alex  data/<ds>/  -> the .tar.zst shards, never unpacked here

    python3 scripts/dm_link.py [--check] [--smoke]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dm_common import (  # noqa: E402
    CLUSTERS,
    IGNORED_DIRS,
    ConfigError,
    dataset_source,
    detect_machine,
    entries,
    load_config,
    nas_root,
    relative_files,
    repo_root,
)

SMOKE = "_smoke"
problems: list[str] = []


def fail(message: str) -> None:
    problems.append(message)
    print(f"  FAIL {message}")


def ensure_symlink(link: Path, target: Path, check: bool) -> None:
    if link.is_symlink() and link.readlink() == target:
        print(f"  ok   {link.name} -> {target}")
        return
    if not target.exists():
        fail(f"{link.name}: target {target} does not exist")
        return
    if check:
        fail(f"{link.name}: not linked to {target}")
        return
    if link.is_symlink() or link.exists():
        if link.is_dir() and not link.is_symlink():
            fail(f"{link} is a real directory; refusing to replace it")
            return
        link.unlink()
    link.symlink_to(target)
    print(f"  link {link.name} -> {target}")


def ensure_copy(dest: Path, source: Path, check: bool) -> None:
    if dest.is_dir() and any(dest.iterdir()):
        print(f"  ok   {dest.name} (already populated)")
        return
    if not source.exists():
        fail(f"{dest.name}: source {source} not reachable from this host")
        return
    if check:
        fail(f"{dest.name}: empty, needs a copy from {source}")
        return
    print(f"  copy {source} -> {dest}")
    if shutil.which("rsync") is not None:
        subprocess.run(
            ["rsync", "-a", "--info=progress2", f"{source}/", f"{dest}/"],
            check=True,
        )
    else:
        shutil.copytree(source, dest, dirs_exist_ok=True)


def verify_shards(directory: Path, name: str) -> None:
    sums = directory / "sha256sums.txt"
    if not sums.is_file():
        fail(f"{name}: no sha256sums.txt -- push it with dm_push.sh")
        return
    shards = [
        p for p in directory.iterdir() if p.name.endswith((".tar", ".tar.zst"))
    ]
    if not shards:
        fail(f"{name}: no shards present in {directory}")
        return
    print(f"  ok   {name}: {len(shards)} shards, checksums file present")


def build_smoke(root: Path, cfg: dict[str, object], check: bool) -> None:
    smoke = entries(cfg.get("smoke"))
    mix = entries(smoke.get("mix"))
    if not mix:
        print("  --   no smoke.mix declared, skipping subset")
        return
    total = int(smoke.get("total", 200) or 200)
    base = root / "data" / SMOKE
    if check:
        if base.is_dir():
            print(f"  ok   data/{SMOKE} present")
        else:
            fail("data/_smoke missing")
        return
    base.mkdir(parents=True, exist_ok=True)
    for dataset, share in mix.items():
        source = root / "data" / dataset
        if not source.exists():
            fail(f"smoke: data/{dataset} not materialised yet")
            continue
        wanted = max(1, round(total * float(share)))
        files = relative_files(source.resolve())
        if not files:
            fail(f"smoke: data/{dataset} contains no files")
            continue
        step = max(1, len(files) // wanted)
        picked = files[::step][:wanted]
        dest = base / dataset
        if dest.is_dir():
            shutil.rmtree(dest)
        for rel in picked:
            link = dest / rel
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to((source / rel).resolve())
        print(f"  smoke {dataset}: {len(picked)} of {len(files)} files")


def ensure_gitignore(root: Path, check: bool) -> None:
    path = root / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    lines = {line.strip() for line in text.splitlines()}
    missing = [f"{d}/" for d in IGNORED_DIRS if f"{d}/" not in lines]
    if ".docs/" in lines:
        fail(".docs/ is gitignored -- it must be committed")
    if not missing:
        print("  ok   .gitignore covers data/, checkpoints/, outputs/")
        return
    if check:
        fail(f".gitignore is missing: {', '.join(missing)}")
        return
    head = text.rstrip("\n") + "\n\n" if text.strip() else ""
    block = "# data-management (machine-dependent, never committed)\n"
    path.write_text(
        head + block + "\n".join(missing) + "\n",
        encoding="utf-8",
    )
    print(f"  add  .gitignore entries: {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report problems, change nothing, exit non-zero if any",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="also (re)build the data/_smoke subset",
    )
    args = parser.parse_args()

    root = repo_root()
    cfg = load_config(root)
    role = detect_machine(cfg)
    print(f"repo {root}\nrole {role}\n")

    for name in IGNORED_DIRS:
        (root / name).mkdir(exist_ok=True)
    ensure_gitignore(root, args.check)

    print("datasets:")
    for dataset in entries(cfg.get("datasets")):
        link = root / "data" / dataset
        if role == "workstation":
            ensure_symlink(link, dataset_source(cfg, dataset), args.check)
        elif role == "lab":
            link.mkdir(exist_ok=True)
            ensure_copy(link, dataset_source(cfg, dataset), args.check)
        else:
            verify_shards(link, dataset)

    print("checkpoints:")
    for name, spec in entries(cfg.get("checkpoints")).items():
        nas_rel = str(spec["nas"])
        target = nas_root(cfg) / nas_rel
        # Default to the NAS basename so existing config paths keep
        # working; "as" overrides it when a stable local name is wanted.
        local = str(spec.get("as") or Path(nas_rel).name)
        dest = root / "checkpoints" / local
        if role in CLUSTERS:
            if dest.is_symlink():
                fail(
                    f"{name}: {local} is a symlink; "
                    f"on {role} it must be a copy"
                )
            elif not dest.exists():
                fail(f"{name}: {local} missing -- copy it in with dm_push.sh")
            else:
                print(f"  ok   {name} -> {local} (real file)")
        else:
            ensure_symlink(dest, target, args.check)

    if args.smoke or args.check:
        print("smoke subset:")
        if role in CLUSTERS:
            print("  --   skipped on a cluster (smoke tests run locally)")
        else:
            build_smoke(root, cfg, args.check)

    if problems:
        print(f"\n{len(problems)} problem(s)")
        return 1
    print("\nall good")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
