#!/usr/bin/env python3
"""Validate core-matched derived arrays and standard corner products."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import tomllib

import numpy as np


CORE_ARRAYS = ("E_j_core_52", "Gamma_0_core_avg", "M_j_core_msun")
CORNER_PRODUCTS = (
    "corner_prior.pdf",
    "corner.pdf",
    "corner_core.pdf",
    "corner_csm.pdf",
    "corner_energy.pdf",
    "corner_jet_mass.pdf",
)
POWERLAW_STRUCTJET_PRODUCTS = (
    "mass_swept_ejecta_time.pdf",
    "mass_swept_ejecta_radius.pdf",
    "mass_swept_ejecta_two_panel.pdf",
    "mass_swept_ejecta_crossings.csv",
    "gamma_jetbreak_two_panel.pdf",
    "gamma_jetbreak_crossings.csv",
)
RESOLUTION_LADDER_PRODUCTS = (
    "resolution_summary.csv",
    "modeled_observation_fluxes.csv",
    "resolution_light_curve_overlay.pdf",
    "resolution_light_curve_overlay.png",
    "resolution_convergence.pdf",
    "resolution_convergence.png",
    "resolution_convergence_signed.pdf",
    "resolution_convergence_signed.png",
    ".resolution_plot_version",
    "resolution_run_metadata.json",
)
RESOLUTION_LADDER_VERSION = "coupled-grid-relative-to-production-v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument(
        "--require-resolution-ladder",
        action="store_true",
        help="Require the standard fixed-solution numerical-resolution products.",
    )
    return parser.parse_args()


def require_pdf_png_pairs(results: Path) -> None:
    """Require every root-level PDF product to have a same-stem PNG companion."""
    missing = []
    for pdf_path in sorted(results.glob("*.pdf")):
        if "trash" in pdf_path.parts:
            continue
        png_path = pdf_path.with_suffix(".png")
        if not png_path.is_file() or png_path.stat().st_size == 0:
            missing.append(png_path.name)
    if missing:
        raise SystemExit(f"Missing or empty PNG companions for PDF products: {missing}")


def require_resolution_ladder(results: Path) -> None:
    """Require the standard numerical ladder and a production-grid reference."""
    ladder = results / "resolution_ladder"
    missing = [
        name
        for name in RESOLUTION_LADDER_PRODUCTS
        if not (ladder / name).is_file() or (ladder / name).stat().st_size == 0
    ]
    if missing:
        raise SystemExit(
            f"Missing or empty numerical-resolution ladder products in {ladder}: {missing}"
        )

    with (ladder / "resolution_summary.csv").open(newline="") as handle:
        summary = list(csv.DictReader(handle))
    if not summary or "resolution_id" not in summary[0]:
        raise SystemExit(f"Invalid numerical-resolution summary: {ladder / 'resolution_summary.csv'}")
    resolution_ids = {row.get("resolution_id", "") for row in summary}
    if not ({"production", "campaign_moderate"} & resolution_ids):
        raise SystemExit(
            "Numerical-resolution summary lacks a production-grid reference: "
            f"{ladder / 'resolution_summary.csv'}"
        )
    try:
        metadata = json.loads((ladder / "resolution_run_metadata.json").read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Unreadable numerical-resolution metadata: {ladder}") from exc
    if metadata.get("resolution_ladder_version") != RESOLUTION_LADDER_VERSION:
        raise SystemExit(
            "Numerical-resolution ladder is not the current coupled-grid protocol: "
            f"{ladder / 'resolution_run_metadata.json'}"
        )


def main() -> int:
    results = args.results.expanduser().resolve()
    posterior_path = results / "jet_energy_posterior.npz"
    if not posterior_path.is_file():
        raise SystemExit(f"Missing core posterior product: {posterior_path}")

    sample_count = None
    with np.load(posterior_path) as posterior:
        for name in CORE_ARRAYS:
            if name not in posterior:
                raise SystemExit(f"Missing {name} in {posterior_path}")
            values = np.asarray(posterior[name], dtype=float)
            if values.ndim != 1 or values.size == 0:
                raise SystemExit(f"Invalid shape for {name}: {values.shape}")
            if sample_count is None:
                sample_count = values.size
            elif values.size != sample_count:
                raise SystemExit(
                    f"Core posterior length mismatch: {name} has {values.size}, "
                    f"expected {sample_count}"
                )
            if not np.all(np.isfinite(values)):
                raise SystemExit(f"Non-finite values found in {name}")
            if not np.all(values > 0.0):
                raise SystemExit(f"Non-positive values found in {name}")

    missing = [
        name
        for name in CORNER_PRODUCTS
        if not (results / name).is_file() or (results / name).stat().st_size == 0
    ]
    if missing:
        raise SystemExit(f"Missing or empty core-aware corner products: {missing}")

    require_pdf_png_pairs(results)
    if args.require_resolution_ladder:
        require_resolution_ladder(results)

    model_path = results / "model.toml"
    if model_path.is_file():
        with model_path.open("rb") as handle:
            model_name = str(tomllib.load(handle).get("name", ""))
        if model_name == "PowerlawJetVegasDylanSpectrumModel":
            missing_structjet = [
                name
                for name in POWERLAW_STRUCTJET_PRODUCTS
                if not (results / name).is_file()
                or (results / name).stat().st_size == 0
            ]
            if missing_structjet:
                raise SystemExit(
                    "Missing or empty structured-jet mass/Gamma products: "
                    f"{missing_structjet}"
                )

    print(
        f"core_postfit_products_ok results={results} "
        f"samples={sample_count} arrays={','.join(CORE_ARRAYS)} "
        f"resolution_ladder={'required' if args.require_resolution_ladder else 'not-required'}"
    )
    return 0


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(main())
