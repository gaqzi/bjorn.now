"""Lossless PNG optimization using oxipng."""

from pathlib import Path

import oxipng

OXIPNG_LEVEL = 4


def optimize_file(path: Path) -> tuple[int, int]:
    """Optimize a single PNG file in place. Returns (before, after) sizes in bytes."""
    before = path.stat().st_size
    oxipng.optimize(str(path), level=OXIPNG_LEVEL)
    after = path.stat().st_size
    return before, after


def optimize_files(paths: list[Path]) -> tuple[int, int, int]:
    """Optimize multiple PNG files. Returns (count, total_before, total_after)."""
    total_before = 0
    total_after = 0
    for path in paths:
        before, after = optimize_file(path)
        total_before += before
        total_after += after
    return len(paths), total_before, total_after


def collect_pngs(paths: list[Path]) -> list[Path]:
    """Collect PNG files from a mix of files and directories."""
    result = []
    for p in paths:
        if p.is_dir():
            result.extend(sorted(p.rglob("*.png")))
        elif p.is_file() and p.suffix.lower() == ".png":
            result.append(p)
    return result
