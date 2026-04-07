#!/usr/bin/env python3
"""Batch replot corner PDFs using current diagnose.plot_corner logic.

This is intended to backfill existing results after corner-plot layout updates
(e.g., including lf0 / Gamma0).
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import numpy as np

from jetfit.mcmc.parameters import Parameters
from scripts.plot import diagnose


EVENT_RE = re.compile(r"^([0-9]{6}[A-Z]?)")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--root",
        action="append",
        type=Path,
        required=True,
        help="Root directory to scan for result folders (repeatable).",
    )
    p.add_argument(
        "--vegas-dir",
        type=Path,
        default=Path("/Users/jkeohane/GRBs/VegasJetFit"),
        help="VegasJetFit repo directory.",
    )
    p.add_argument(
        "--drive-owner",
        default="jkeohane",
        help="When scanning Drive-like roots, only rewrite this owner subtree.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print planned updates.",
    )
    return p.parse_args()


def looks_like_drive_path(path: Path) -> bool:
    s = str(path)
    return "My Drive" in s or "VegasGRBruns" in s


def iter_result_dirs(root: Path, drive_owner: str) -> list[Path]:
    out: list[Path] = []
    if not root.exists():
        return out

    owner_segment = re.compile(rf"^{re.escape(drive_owner)}(?: \(\d+\))?$")
    drive_anchor = root.name

    for chain_file in root.rglob("chain.npz"):
        result_dir = chain_file.parent

        # Only touch completed runs.
        if not (result_dir / "best_fit.json").exists():
            continue

        # Keep collaborators' shared folders untouched by default.
        if looks_like_drive_path(root):
            parts = result_dir.parts
            anchor_positions = [i for i, p in enumerate(parts) if p == drive_anchor]
            if not any(
                owner_segment.match(parts[j])
                for i in anchor_positions
                for j in range(i + 2, len(parts))
            ):
                continue

        out.append(result_dir)

    return sorted(set(out))


def infer_event(result_dir: Path) -> str | None:
    m = EVENT_RE.match(result_dir.name)
    if m:
        return m.group(1)
    # Drive structure: .../<event>/<owner>/<run_label>
    for part in result_dir.parts[::-1]:
        m = EVENT_RE.match(part)
        if m:
            return m.group(1)
    return None


def resolve_model_toml(result_dir: Path, vegas_dir: Path) -> Path | None:
    direct = result_dir / "model.toml"
    if direct.exists():
        return direct

    event = infer_event(result_dir)
    if event is None:
        return None

    name = result_dir.name
    logs = vegas_dir / "logs"
    resources_model = vegas_dir / "jetfit" / "resources" / "grbs" / event / "parameters.toml"

    candidates: list[Path] = []
    if "smoothbroken" in name or "_sbpl_" in name:
        candidates.extend(
            [
                logs / f"{event}.parameters_sbpl_like.toml",
                resources_model,
            ]
        )
    elif "bubble" in name:
        candidates.extend(
            [
                logs / f"{event}.parameters_bubble_theta1.0.synced.toml",
                logs / f"{event}.parameters_bubble_theta1.0.speedtest.synced.toml",
                resources_model,
            ]
        )
    elif "AnshPriors" in name or "Ansh_Run" in name:
        candidates.extend(
            [
                vegas_dir / "Ansh_Run" / "parameters_powerlaw.toml",
                resources_model,
            ]
        )
    else:
        candidates.extend(
            [
                logs / f"{event}.parameters_tophat_theta1.0.toml",
                vegas_dir / "Ansh_Run" / "parameters_powerlaw.toml",
                resources_model,
            ]
        )

    for c in candidates:
        if c.exists():
            return c
    return None


def flatten_chain(chain: np.ndarray) -> np.ndarray:
    if chain.ndim == 2:
        return chain
    if chain.ndim == 3:
        return chain.reshape((-1, chain.shape[-1]))
    raise ValueError(f"Unexpected chain shape: {chain.shape}")


def main() -> int:
    args = parse_args()
    vegas_dir = args.vegas_dir.resolve()
    roots = [r.resolve() for r in args.root]

    targets: list[Path] = []
    for root in roots:
        targets.extend(iter_result_dirs(root, args.drive_owner))
    targets = sorted(set(targets))

    print(f"Found {len(targets)} completed result directories.")

    updated = 0
    skipped = 0
    failed = 0

    for result_dir in targets:
        model_toml = resolve_model_toml(result_dir, vegas_dir)
        if model_toml is None:
            print(f"SKIP (no model TOML): {result_dir}")
            skipped += 1
            continue

        chain_file = result_dir / "chain.npz"
        try:
            chain = np.load(chain_file)["chain"]
            flat = flatten_chain(chain)
            params = Parameters.from_toml(model_toml).fitting
        except Exception as exc:
            print(f"FAIL (load): {result_dir} :: {exc}")
            failed += 1
            continue

        event = infer_event(result_dir) or "UNKNOWN"
        os.environ["JETFIT_PLOT_RUN_LABEL"] = f"GRB {event} | {result_dir.name}"

        if args.dry_run:
            print(f"DRYRUN: {result_dir}  model={model_toml}")
            updated += 1
            continue

        try:
            diagnose.plot_corner(flat, params, out_dir=result_dir)
            print(f"OK: {result_dir}")
            updated += 1
        except Exception as exc:
            print(f"FAIL (plot): {result_dir} :: {exc}")
            failed += 1

    print(
        f"Done. updated={updated} skipped={skipped} failed={failed} total={len(targets)}"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
