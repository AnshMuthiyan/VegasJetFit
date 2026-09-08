#!/usr/bin/env python3
"""Flatten redundant `fit` leaves in the human-facing Google Drive Fits tree.

Older organization passes used:

    Fits/<jet>/<csm>/<spectrum>/<campaign>/<GRB>/fit

The current convention is simpler:

    Fits/<jet>/<csm>/<spectrum>/<campaign>/<GRB>

This script moves the contents of each redundant `fit` directory up one level
and updates `run_registry.csv` paths accordingly.  It refuses to overwrite
conflicting parent files.
"""

from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path


def _flatten_fit_dir(fit_dir: Path, dry_run: bool = False) -> bool:
    parent = fit_dir.parent
    conflicts = []
    for child in fit_dir.iterdir():
        dest = parent / child.name
        if dest.exists() and child.name != ".DS_Store":
            conflicts.append(child.name)
    if conflicts:
        raise FileExistsError(f"Cannot flatten {fit_dir}; parent conflicts: {conflicts}")

    if dry_run:
        return True

    ds_store = fit_dir / ".DS_Store"
    if ds_store.exists() and (parent / ".DS_Store").exists():
        ds_store.unlink()

    for child in list(fit_dir.iterdir()):
        shutil.move(str(child), str(parent / child.name))
    fit_dir.rmdir()
    return True


def _update_registry(fits_root: Path, dry_run: bool = False) -> int:
    changed = 0
    for registry_path in fits_root.rglob("run_registry.csv"):
        rows = list(csv.DictReader(registry_path.open()))
        if not rows:
            continue
        for row in rows:
            new_path = row.get("new_path", "")
            if new_path.endswith("/fit"):
                row["new_path"] = str(Path(new_path).parent)
                changed += 1
        if changed and not dry_run:
            with registry_path.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
    return changed


def simplify(fits_root: Path, dry_run: bool = False) -> tuple[int, int]:
    fit_dirs = sorted(path for path in fits_root.rglob("fit") if path.is_dir())
    flattened = 0
    for fit_dir in fit_dirs:
        if _flatten_fit_dir(fit_dir, dry_run=dry_run):
            flattened += 1
    registry_rows = _update_registry(fits_root, dry_run=dry_run)
    return flattened, registry_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fits_root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    flattened, registry_rows = simplify(args.fits_root.expanduser().resolve(), args.dry_run)
    action = "Would flatten" if args.dry_run else "Flattened"
    print(f"{action} {flattened} redundant fit directories; registry rows updated: {registry_rows}")


if __name__ == "__main__":
    main()
