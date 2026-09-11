"""Shard a NAS dataset into a fixed number of .tar.zst archives.

The NAS stays the single unpacked source of truth; the cluster only ever
sees these shards. Re-running repacks *only* the shards whose contents
changed, because every file is assigned to a shard by a hash of its
relative path -- adding files never reshuffles the others.

    python3 scripts/dm_pack.py <dataset> [--all] [--allow-deletions]

Must run where the NAS is mounted (the workstation).
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dm_common import (  # noqa: E402
    ConfigError,
    dataset_source,
    load_config,
    pack_dir,
    relative_files,
    repo_root,
    shard_count,
)

MANIFEST = "manifest.tsv"
CHECKSUMS = "sha256sums.txt"
Entry = tuple[int, int, int]  # size, mtime_ns, shard


def shard_of(relpath: str, shards: int) -> int:
    """Stable shard index for a path. Independent of every other file."""
    digest = hashlib.blake2b(relpath.encode("utf-8"), digest_size=8)
    return int.from_bytes(digest.digest(), "big") % shards


def read_manifest(path: Path) -> dict[str, Entry]:
    if not path.is_file():
        return {}
    out: dict[str, Entry] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        rel, size, mtime, shard = line.rsplit("\t", 3)
        out[rel] = (int(size), int(mtime), int(shard))
    return out


def write_manifest(path: Path, manifest: dict[str, Entry]) -> None:
    lines = ["#relpath\tsize\tmtime_ns\tshard"]
    lines += [
        f"{rel}\t{size}\t{mtime}\t{shard}"
        for rel, (size, mtime, shard) in sorted(manifest.items())
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def scan(source: Path, shards: int) -> dict[str, Entry]:
    manifest: dict[str, Entry] = {}
    for rel in relative_files(source):
        stat = (source / rel).stat()
        manifest[rel] = (stat.st_size, stat.st_mtime_ns, shard_of(rel, shards))
    return manifest


def compressor() -> tuple[bool, str]:
    """Prefer multithreaded zstd; fall back to an uncompressed tar.

    Probed once per run, not once per shard.
    """
    if shutil.which("zstd") is not None:
        return True, ".tar.zst"
    print("  ! zstd not found -- writing uncompressed .tar", file=sys.stderr)
    return False, ".tar"


def build_shard(
    source: Path,
    out: Path,
    members: list[str],
    use_zstd: bool,
) -> None:
    """Pack *members* into *out*, piping through zstd when available.

    tar's own -I/--use-compress-program is GNU-only and silently means
    --include on bsdtar, so the compressor is a separate process.
    """
    cmd = [
        "tar",
        "-C",
        str(source),
        "--null",
        "-T",
        "-",
        "--no-recursion",
        "-cf",
        "-",
    ]
    payload = "\0".join(members).encode("utf-8") + b"\0"
    with out.open("wb") as sink:
        if not use_zstd:
            subprocess.run(cmd, input=payload, stdout=sink, check=True)
            return
        tar = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )
        zstd = subprocess.Popen(
            ["zstd", "-T0", "-3", "-q"], stdin=tar.stdout, stdout=sink
        )
        if tar.stdout is not None:
            tar.stdout.close()
        tar.communicate(payload)
        zstd.wait()
    if tar.returncode or zstd.returncode:
        out.unlink(missing_ok=True)
        raise ConfigError(
            f"packing {out.name} failed "
            f"(tar={tar.returncode}, zstd={zstd.returncode})"
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset")
    parser.add_argument(
        "--all",
        action="store_true",
        help="repack every shard, not just the changed ones",
    )
    parser.add_argument(
        "--allow-deletions",
        action="store_true",
        help="proceed even though files vanished from the NAS",
    )
    args = parser.parse_args()

    root = repo_root()
    cfg = load_config(root)
    source = dataset_source(cfg, args.dataset)
    if not source.is_dir():
        raise ConfigError(f"dataset source {source} is not a directory")
    shards = shard_count(cfg, args.dataset)
    out_dir = pack_dir(cfg, args.dataset)
    if out_dir.resolve() == source.resolve() or source.resolve() in (
        out_dir.resolve().parents
    ):
        raise ConfigError(
            f"pack_root resolves to {out_dir}, which is inside the dataset "
            f"{source}. The packer would archive its own archives. Point "
            "pack_root somewhere outside the dataset tree."
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    old = read_manifest(out_dir / MANIFEST)
    new = scan(source, shards)
    print(f"{args.dataset}: {len(new)} files -> {shards} shards")

    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(
        rel for rel in set(new) & set(old) if new[rel][:2] != old[rel][:2]
    )
    print(
        f"  added {len(added)}  modified {len(changed)}  "
        f"removed {len(removed)}"
    )

    if removed and not args.allow_deletions:
        for rel in removed[:10]:
            print(f"  - {rel}", file=sys.stderr)
        raise ConfigError(
            f"{len(removed)} file(s) disappeared from the NAS. The NAS is "
            "meant to be static, so this usually means a half-mounted "
            "share. Re-run with --allow-deletions if it is intentional."
        )

    use_zstd, suffix = compressor()
    if args.all or not old:
        dirty = set(range(shards))
    else:
        dirty = {new[r][2] for r in added + changed}
        dirty |= {old[r][2] for r in removed}

    if not dirty:
        print("  nothing to do -- shards are up to date")
        return 0

    by_shard: dict[int, list[str]] = {i: [] for i in range(shards)}
    for rel, (_, _, shard) in new.items():
        by_shard[shard].append(rel)

    for index in sorted(dirty):
        members = sorted(by_shard[index])
        target = out_dir / f"{args.dataset}_{index:03d}{suffix}"
        if not members:
            target.unlink(missing_ok=True)
            continue
        print(f"  packing {target.name} ({len(members)} files)")
        build_shard(source, target, members, use_zstd)

    write_manifest(out_dir / MANIFEST, new)

    sums = sorted(
        p for p in out_dir.iterdir() if p.name.endswith((".tar", ".tar.zst"))
    )
    (out_dir / CHECKSUMS).write_text(
        "".join(f"{sha256(p)}  {p.name}\n" for p in sums),
        encoding="utf-8",
    )
    print(f"  wrote {MANIFEST} and {CHECKSUMS} in {out_dir}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
