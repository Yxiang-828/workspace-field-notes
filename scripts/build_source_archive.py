#!/usr/bin/env python3
"""Make a portable source snapshot when the full workspace exceeds free disk space.

This intentionally omits dependency/build/cache trees, Git internals, and files
over the size cap. The ZIP records every omission in MANIFEST.json. It is not a
substitute for a full backup.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


SKIP_DIRS = {
    ".git", ".next", ".pytest_cache", ".playwright-cli", ".venv",
    "__pycache__", "_cache", "_out", "_scratch", "build", "dist",
    "node_modules", "target", "tmp", "venv",
}


def inventory(root: Path, limit: int) -> tuple[list[tuple[Path, str, int]], list[dict], dict]:
    included: list[tuple[Path, str, int]] = []
    omitted: list[dict] = []
    stats = {"included_files": 0, "included_bytes": 0,
             "omitted_files": 0, "omitted_bytes": 0}
    for base, dirs, files in os.walk(root, followlinks=False):
        here = Path(base)
        kept_dirs = []
        for name in dirs:
            path = here / name
            rel = path.relative_to(root).as_posix()
            if name.lower() in SKIP_DIRS or path.is_symlink():
                omitted.append({"path": rel + "/", "reason": "build/cache/git or link"})
            else:
                kept_dirs.append(name)
        dirs[:] = kept_dirs
        for name in files:
            path = here / name
            rel = path.relative_to(root).as_posix()
            try:
                if path.is_symlink():
                    omitted.append({"path": rel, "reason": "link"})
                    continue
                size = path.stat().st_size
            except OSError as exc:
                omitted.append({"path": rel, "reason": type(exc).__name__})
                continue
            if size > limit:
                omitted.append({"path": rel, "reason": "size cap", "bytes": size})
                stats["omitted_files"] += 1
                stats["omitted_bytes"] += size
            else:
                included.append((path, rel, size))
                stats["included_files"] += 1
                stats["included_bytes"] += size
    return included, omitted, stats


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--max-file-mb", type=int, default=32)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    root = args.root.resolve(strict=True)
    output = args.output.resolve()
    if output.is_relative_to(root):
        p.error("output must be outside the source workspace")
    included, omitted, stats = inventory(root, args.max_file_mb * 1024 * 1024)
    print(json.dumps(stats, indent=2))
    if args.dry_run:
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    failures: list[dict] = []
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=4, allowZip64=True) as archive:
        for i, (path, rel, _) in enumerate(included, 1):
            try:
                archive.write(path, "claude-workspace/" + rel)
            except (OSError, PermissionError) as exc:
                failures.append({"path": rel, "reason": type(exc).__name__})
            if i % 20000 == 0:
                print(f"Archived {i}/{len(included)} files", flush=True)
        manifest = {
            "source": str(root),
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "kind": "source snapshot; not a full backup",
            "max_file_bytes": args.max_file_mb * 1024 * 1024,
            "skipped_directories": sorted(SKIP_DIRS),
            "stats": stats,
            "omitted": omitted + failures,
        }
        archive.writestr("MANIFEST.json", json.dumps(manifest, indent=2))
    print(f"Wrote {output} ({output.stat().st_size} bytes), read failures: {len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
