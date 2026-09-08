#!/usr/bin/env python3
"""Build a portable LaTeX/PDF meeting summary from a published GRB campaign.

The script intentionally reads the files that travel with a published campaign:
event ``model.toml`` files, minimized results, MCMC settings, and campaign-level
figures.  It can therefore be run both by a completion watcher and retroactively
on an older campaign directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


BASE_EVENT_RE = re.compile(r"^\d{6}[A-Z]?$", re.IGNORECASE)
EVENT_RE = re.compile(r"^(\d{6}[A-Z]?)(?:_[A-Z0-9][A-Z0-9_-]*)?$", re.IGNORECASE)
SUMMARY_TEX = "campaign_meeting_summary.tex"
SUMMARY_PDF = "campaign_meeting_summary.pdf"
MOVE_MANIFEST = "campaign_plot_organization.csv"
RESOLUTION_PLOT_VERSION = "signed-primary-convergence-and-16core-runtime-v16"
POSTFIT_PRODUCT_STYLE_VERSION = "publication-ready-v3-prior-bound-and-zoomed-corners"
RESOLUTION_LADDER_VERSION = "coupled-grid-relative-to-production-v2"
DENSITY_SHELL_METHOD_VERSION = "spherical-shell-dynamical-radius-v2"

# This order follows the thesis-style diagnostic sequence first, then the
# products added for the current VegasAfterglow analysis.
EVENT_FIGURES = (
    ("Standard light curve", ("light_curve.pdf",)),
    ("Posterior light-curve envelope", ("light_curve_spread_out_shaded_posterior.pdf",)),
    ("All retained walker light curves", ("light_curve_spread_out_100_walkers.pdf",)),
    ("Spectral evolution and break frequencies", ("spectral_evolution_two_panel.pdf",)),
    ("Spectra at selected epochs", ("spectrum_timeseries.pdf",)),
    ("Spectral-break evolution", ("frequencies.pdf",)),
    ("Core physical / microphysical posterior", ("corner_core.pdf",)),
    ("CSM / spectral / geometry posterior", ("corner_csm.pdf",)),
    ("Full physical-parameter posterior (fit prior bounds)", ("corner_prior.pdf",)),
    ("Full physical-parameter posterior (zoomed)", ("corner.pdf",)),
    ("Non-physical nuisance-parameter posterior", ("corner_np.pdf",)),
    ("Density profile", ("n_profile.pdf", "n0_profile.pdf", "k_profile.pdf")),
    ("Observed-shell mass posterior", ("density_shell_mass_histogram.pdf",)),
    ("Observed-shell mean number-density posterior", ("density_shell_density_histogram.pdf",)),
    ("Observed-shell mass-number-density corner", ("density_shell_mass_corner.pdf",)),
    ("Observed-shell mass-number-density scatter", ("density_shell_mass_scatter.pdf",)),
    ("Lorentz-factor and jet-break diagnostic", ("gamma_jetbreak_two_panel.pdf",)),
    ("Swept-up mass diagnostic", ("mass_swept_ejecta_two_panel.pdf",)),
)

PARAMETER_LABELS = {
    "E_j_core_52": (r"$E_{j,\mathrm{core},52}$", r"Core kinetic energy [$10^{52}$ erg]"),
    "Gamma_0_core_avg": (r"$\Gamma_{0,\mathrm{core}}$", "Core-averaged initial Lorentz factor"),
    "n017": (r"$n_{0,17}$", r"Density normalization at $10^{17}$ cm [$\mathrm{cm}^{-3}$]"),
    "eps_e": (r"$\epsilon_e$", "Electron energy fraction"),
    "eps_b": (r"$\epsilon_B$", "Magnetic energy fraction"),
    "p": (r"$p$", "Electron power-law index"),
    "k": (r"$k$", "CSM density-profile slope"),
    "theta_c": (r"$\theta_c$", "Jet core half-opening angle [rad]"),
    "theta_v": (r"$\theta_v$", "Viewing angle [rad]"),
    "s": (r"$s$", "Structured-jet angular-shape parameter"),
    "ebv_source_frame": (r"$E(B-V)_{\rm sf}$", "Source-frame color excess [mag]"),
    "ebv_milky_way": (r"$E(B-V)_{\rm MW}$", "Milky-Way foreground color excess [mag]"),
    "rv_milky_way": (r"$R_{V,\rm MW}$", "Milky-Way extinction-law parameter"),
    "slop": (r"$\sigma_{\rm slop}$", "Additional fractional/model scatter"),
    "z": (r"$z$", "Cosmological redshift"),
    "dl28": (r"$d_L/10^{28}\,\mathrm{cm}$", "Luminosity distance"),
    "hmf": (r"$h$", "Hubble parameter normalization"),
    "k_e": (r"$k_e$", "Jet angular energy-profile index"),
    "k_g": (r"$k_g$", "Jet angular Lorentz-factor-profile index"),
    "vegas_resolution_phi": (r"$N_\phi$", "Azimuthal angular samples per degree"),
    "vegas_resolution_theta": (r"$N_\theta$", "Polar angular samples per degree"),
    "vegas_resolution_t": (r"$N_t$", r"Time samples per $\log_{10}$ decade"),
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent


def tex(value: object) -> str:
    """Escape text fields while leaving a compact scientific notation readable."""
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "_": r"\_",
        "#": r"\#", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def tex_math_or_text(value: str) -> str:
    """Allow curated math symbols while safely escaping all other table text."""
    return value if value.startswith(("$", "\\")) else tex(value)


def tex_breakable_text(value: object) -> str:
    """Escape prose while allowing long run identifiers to wrap at underscores."""
    return tex(value).replace(r"\_", r"\_\allowbreak{}")


def tex_path(path: Path) -> str:
    # All document inputs are campaign-relative. detokenize keeps underscores
    # and the dated campaign name harmless to LaTeX.
    return r"\detokenize{" + path.as_posix() + "}"


def read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def event_dirs(campaign: Path) -> list[Path]:
    return sorted(
        (path for path in campaign.iterdir() if path.is_dir() and EVENT_RE.fullmatch(path.name)),
        key=lambda path: path.name,
    )


def canonical_event_name(event: Path | str) -> str:
    """Return the GRB identifier from a canonical or controlled-branch name."""
    name = event.name if isinstance(event, Path) else str(event)
    match = EVENT_RE.fullmatch(name)
    if match is None:
        raise ValueError(f"Not a GRB event directory name: {name}")
    return match.group(1)


def fitted_and_fixed(model: dict[str, Any]) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    fitted: list[tuple[str, str, str]] = []
    fixed: list[tuple[str, str, str]] = []
    for section in ("model", "extinction", "host", "offsets", "slop"):
        for entry in model.get(section, []):
            if not isinstance(entry, dict) or "name" not in entry:
                continue
            name = str(entry["name"])
            scale = str(entry.get("scale", "linear"))
            prior = entry.get("prior")
            if isinstance(prior, dict):
                if prior.get("type") == "uniform":
                    domain = f"{number(prior.get('lower', ''))} to {number(prior.get('upper', ''))}"
                elif prior.get("type") == "gaussian":
                    domain = f"Gaussian: mu={number(prior.get('mu', ''))}, sigma={number(prior.get('sigma', ''))}"
                else:
                    domain = str(prior.get("type", "prior"))
                fitted.append((name, scale, domain))
            elif "value" in entry:
                fixed.append((name, scale, number(entry["value"])))
    return fitted, fixed


def fitted_scales(model: dict[str, Any]) -> list[tuple[str, str]]:
    """Return fitted coordinates in the exact chain-column order."""
    rows: list[tuple[str, str]] = []
    for section in ("model", "extinction", "host", "offsets", "slop"):
        for entry in model.get(section, []):
            if isinstance(entry, dict) and "name" in entry and isinstance(entry.get("prior"), dict):
                rows.append((str(entry["name"]), str(entry.get("scale", "linear"))))
    return rows


def flatten_parameters(payload: dict[str, Any]) -> list[tuple[str, object]]:
    params = payload.get("params", {})
    rows: list[tuple[str, object]] = []
    if not isinstance(params, dict):
        return rows
    for section in ("model", "extinction", "host", "offsets", "slop"):
        values = params.get(section, {})
        if isinstance(values, dict):
            rows.extend((str(name), value) for name, value in values.items())
    return rows


def number(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.3g}"
    return str(value)


def formatted_parameter_values(
    minimized: object,
    median: float,
    plus: float,
    minus: float,
) -> tuple[str, str, str, str]:
    """Format a parameter row with a shared precision and, when useful, exponent."""
    values = np.asarray([float(minimized), median, plus, minus], dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size != 4:
        return tuple(number(value) for value in values)  # type: ignore[return-value]
    scale_value = max(abs(median), abs(float(minimized)), abs(plus), abs(minus), 1.0e-300)
    exponent = int(math.floor(math.log10(scale_value)))
    # Scientific notation is reserved for values that would otherwise be hard
    # to scan. All four cells use the same exponent when it is selected.
    if exponent >= 4 or exponent <= -3:
        scaled = values / (10.0 ** exponent)
        return tuple(rf"${value:.2g}\!\times\!10^{{{exponent}}}$" for value in scaled)  # type: ignore[return-value]
    uncertainty = max(abs(plus), abs(minus), 1.0e-12)
    decimals = max(0, min(6, 1 - int(math.floor(math.log10(uncertainty)))))
    return tuple(f"{value:.{decimals}f}" for value in values)  # type: ignore[return-value]


def compact_table(
    headers: Iterable[str],
    rows: list[tuple[str, ...]],
    widths: str = "lll",
    *,
    math_columns: set[int] | None = None,
    footer: tuple[str, ...] | None = None,
    footer_math_columns: set[int] | None = None,
) -> str:
    if not rows:
        return r"\emph{Not available in this published event directory.}"
    math_columns = math_columns or set()
    head = " & ".join(tex(item) for item in headers) + r" \\\hline"
    body = "\n".join(
        " & ".join(
            str(cell)
            if isinstance(cell, LatexCell)
            else tex_math_or_text(cell)
            if index in math_columns
            else tex(cell)
            for index, cell in enumerate(row)
        )
        + r" \\\\"
        for row in rows
    )
    if footer is not None:
        footer_math_columns = footer_math_columns or set()
        footer_text = " & ".join(
            str(cell)
            if isinstance(cell, LatexCell)
            else tex_math_or_text(cell)
            if index in footer_math_columns
            else tex(cell)
            for index, cell in enumerate(footer)
        ) + r" \\\\"
        body += "\n" + r"\hline" + "\n" + footer_text
    return "\n".join((
        r"\begingroup",
        r"\footnotesize",
        r"\renewcommand{\arraystretch}{0.80}",
        r"\setlength{\tabcolsep}{2.5pt}",
        r"\setlength{\LTpre}{0pt}",
        r"\setlength{\LTpost}{0pt}",
        rf"\begin{{longtable}}{{@{{}}{widths}@{{}}}}",
        head,
        r"\endfirsthead",
        head,
        r"\endhead",
        body,
        r"\end{longtable}",
        r"\normalsize",
        r"\endgroup",
    ))


def first_existing(event: Path, choices: tuple[str, ...]) -> Path | None:
    for choice in choices:
        candidate = event / choice
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def event_figure_caption(label: str) -> str:
    """Return paper-ready captions for the standard event-level figures."""
    captions = {
        "Standard light curve": (
            "Observed multi-band afterglow measurements with the minimized forward-model light curve."
        ),
        "Posterior light-curve envelope": (
            "Observed multi-band light curves with the envelope of retained posterior models, "
            "showing the range of solutions supported by the MCMC."
        ),
        "All retained walker light curves": (
            "Observed multi-band light curves overlaid with one model curve for each of the 100 retained "
            "terminal cold-chain walkers, showing the discrete posterior realizations behind the envelope."
        ),
        "Core physical / microphysical posterior": (
            "Posterior constraints on core energy, initial Lorentz factor, and microphysical parameters."
        ),
        "CSM / spectral / geometry posterior": (
            "Posterior constraints on the circumstellar density profile, electron index, and jet geometry."
        ),
        "Full physical-parameter posterior (fit prior bounds)": (
            "Joint posterior distribution in the native fitted physical coordinates, with every axis set "
            "to its explicit prior bounds. Posterior density reaching an edge therefore signals contact "
            "with a hard fit boundary."
        ),
        "Full physical-parameter posterior (zoomed)": (
            "Joint posterior distribution for the physical parameters, shown on compact posterior-focused "
            "axes to make correlations and credible-region structure readable away from the full prior volume."
        ),
        "Non-physical nuisance-parameter posterior": (
            "Posterior distribution for extinction, calibration offsets, and additional-scatter nuisance parameters."
        ),
        "Density profile": (
            "Circumstellar density profiles evaluated from all retained terminal cold-chain walkers."
        ),
        "Spectral evolution and break frequencies": (
            "Top: synchrotron spectra at selected observer times, with thin translucent curves for all finite "
            "terminal cold-chain walkers and a thick minimized reference curve. Bottom: posterior evolution of "
            "the self-absorption (green), injection (blue), and cooling (orange) break frequencies and spectral index."
        ),
        "Spectra at selected epochs": (
            "Standalone spectral-evolution diagnostic. Thin translucent curves show all finite terminal cold-chain "
            "walkers at each epoch; the thick curve is the minimized reference solution."
        ),
        "Spectral-break evolution": (
            "Standalone posterior diagnostic for the self-absorption, injection, and cooling break frequencies and "
            "the modeled spectral index."
        ),
        "Lorentz-factor and jet-break diagnostic": (
            "Blast-wave Lorentz-factor evolution and the associated jet-break diagnostic."
        ),
        "Swept-up mass diagnostic": (
            "Swept-up mass versus observer time and radius, compared with the dynamic ejecta-mass reference scales."
        ),
        "Observed-shell mass posterior": (
            "Terminal-walker posterior for the spherical hydrogen mass integrated through the radial interval sampled by the observations."
        ),
        "Observed-shell mean number-density posterior": (
            "Terminal-walker posterior for the spherical-shell mass divided by proton mass and the corresponding shell volume, expressed in hydrogen atoms per cubic centimetre."
        ),
        "Observed-shell mass-number-density corner": (
            "Joint terminal-walker posterior of observed-shell mass, mean hydrogen number density, density normalization, and density-profile slope; the star is the minimized solution."
        ),
        "Observed-shell mass-number-density scatter": (
            "Observed-shell mass versus mean hydrogen number density for all terminal walkers, colored by the local density-profile slope."
        ),
    }
    return captions.get(label, label + ".")


def comparison_figure_caption(path: Path) -> str:
    """Convert campaign plot filenames into interpretable scientific captions."""
    stem = path.stem.lower()
    if "090424_early_xray_shape_comparison" in stem:
        return (
            "GRB 090424 early-X-ray data and the three minimized model predictions on the common "
            "91--247 s interval. The lower panel exposes the time-dependent model/data ratio; the "
            "listed log-log slopes show that SSC+KN improves but does not reproduce the observed decline."
        )
    if "090424_fit_overlays_by_dataset" in stem:
        return (
            "All GRB 090424 measurement groups evaluated with each minimized fit on one common data table. "
            "The canonical synchrotron fit was not refitted to the excluded early X-rays; its curve is an "
            "out-of-sample prediction there."
        )
    if "090424_fit_quality_by_dataset" in stem:
        return (
            "Common-data fit diagnostics by measurement group. The upper panel uses the quoted measurement "
            "errors without the fitted slop term; the lower panel shows the median model/data ratio and its "
            "16th--84th percentile range."
        )
    if "campaign_resolution_convergence" in stem:
        return "Campaign-wide numerical-resolution sensitivity at the production grid for the published GRBs."
    if "convergence_vs_viewing_angle" in stem:
        return "Numerical-resolution sensitivity versus fitted viewing angle across the published GRBs."
    if "density" in stem and ("_vs_k" in stem or "_vs_csm" in stem):
        return "Joint posterior samples of density normalization and circumstellar density-profile slope."
    if "mass_vs_core_energy" in stem or "mass_vs_jet_core_energy" in stem:
        return "Minimized core jet mass versus core kinetic energy across the published GRBs."
    if "mass_per_solid_angle" in stem:
        return "Minimized core mass per solid angle versus core solid angle across the published GRBs."
    if "mass_vs_solid_angle" in stem:
        return "Minimized core jet mass versus core solid angle across the published GRBs."
    if "density_shell_mass_density_comparison_histograms" in stem:
        return (
            "Matched terminal-walker distributions of the spherical observed-shell mass and "
            "the corresponding shell-volume-averaged hydrogen number density across the published GRBs."
        )
    if "csm_mean_density_vs_n017" in stem:
        return (
            "Posterior 16th--84th percentile comparisons of the density normalization at "
            "10$^{17}$ cm and the hydrogen-density average through each event's data-range profile. "
            "The square axes use identical physical units and per-decade scale."
        )
    if "jet_mass_vs_csm_shell_mass" in stem:
        return (
            "Posterior comparison of the two-sided total jet ejecta mass and the spherical "
            "CSM mass integrated through the data-range profile. Both axes are in solar masses "
            "with equal per-decade scale."
        )
    if "csm_shell_mass_density_vs_k" in stem:
        return (
            "Data-range CSM mass (top) and profile-averaged hydrogen density (bottom) versus the fitted "
            "CSM slope. Both panels share the same $k$ axis; bars show marginal 16th--84th percentiles."
        )
    if "theta_c_vs_profile_mean_density" in stem:
        return (
            "Core-angle and data-range profile-average-density posteriors. The green band marks the "
            "proposed $10^{-6}$--$10^{10}$ cm$^{-3}$ density range for discussion only; it is not a prior "
            "applied to these fits."
        )
    if "theta_c_vs_profile_radius" in stem:
        return (
            "Core angle versus the geometric-mean radius of each data-range density profile. Pale horizontal "
            "segments show the posterior-median inner-to-outer radius interval; point bars are 16th--84th percentiles."
        )
    if "histogram" in stem:
        quantity = stem.replace("_histogram", "").replace("histogram_", "").replace("_", " ")
        return f"Distribution of {quantity} across the published GRBs."
    return "Campaign-level comparison derived from the published GRB results."


def metadata_value(path: Path, key: str) -> str:
    if not path.is_file():
        return ""
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return ""


def wall_clock_hours(event: Path) -> str:
    seconds = wall_clock_seconds(event)
    return "not recorded" if seconds is None else f"{seconds / 3600.0:.1f} h"


def wall_clock_seconds(event: Path) -> float | None:
    path = event / "run.log"
    if not path.is_file():
        return None
    match = re.search(r"^real\s+([0-9.]+)\s*$", path.read_text(errors="replace"), re.MULTILINE)
    if match is None:
        return None
    return float(match.group(1))


def campaign_identity(campaign: Path) -> tuple[str, str]:
    """Return the human-facing VegasGRBruns path and its campaign folder name."""
    share_root = (WORKSPACE_ROOT / "Share_Folder").resolve()
    try:
        relative = campaign.relative_to(share_root).as_posix()
    except ValueError:
        relative = campaign.as_posix()
    return relative, campaign.name


def campaign_date(campaign: Path) -> str:
    match = re.match(r"(\d{2})_(\d{2})_(\d{2})", campaign.name)
    return "campaign date not encoded" if match is None else "20" + "-".join(match.groups())


class LatexCell(str):
    """A deliberately pre-escaped LaTeX table cell."""


def tex_campaign_path(value: str) -> LatexCell:
    """Keep a long campaign path readable without altering its identifier."""
    parts = value.rstrip("/").split("/")
    if len(parts) <= 1:
        return LatexCell(rf"\nolinkurl{{{value}}}")
    prefix = "/".join(parts[:-1]) + "/"
    return LatexCell(rf"\nolinkurl{{{prefix}}}\newline\nolinkurl{{{parts[-1]}}}")


def tex_campaign_identifier(value: str) -> LatexCell:
    """Preserve double underscores while allowing a narrow table cell to wrap."""
    escaped = tex(value).replace(r"\_\_", r"\_\allowbreak\_")
    return LatexCell(rf"{{\small\texttt{{{escaped}}}}}")


def tex_campaign_cover_identifier(value: str) -> LatexCell:
    """Set a long literal folder name in short fixed-width cover-page lines."""
    pieces = value.split("__")
    lines = ["__".join(pieces[index:index + 2]) for index in range(0, len(pieces), 2)]
    body = r"\\".join(tex(line) for line in lines)
    return LatexCell(rf"\begin{{minipage}}{{\textwidth}}\raggedright\small\ttfamily {body}\end{{minipage}}")


def campaign_manifest(campaign: Path) -> dict[str, dict[str, str]]:
    """Locate the report whose recorded publication directory is this campaign."""
    try:
        relative = campaign.resolve().relative_to(WORKSPACE_ROOT).as_posix()
    except ValueError:
        return {}
    for report in PROJECT_ROOT.joinpath("reports").glob("*/CAMPAIGN_METHOD_REPORT.md"):
        if relative not in report.read_text(errors="replace"):
            continue
        manifest = report.parent / "dispatch_manifest.csv"
        if manifest.is_file():
            with manifest.open(newline="") as handle:
                return {row["event"]: row for row in csv.DictReader(handle) if row.get("event")}
    return {}


def event_run_record(event: Path, manifest: dict[str, dict[str, str]]) -> tuple[str, str]:
    host = metadata_value(event / "sync_manifest.txt", "source_host")
    if not host:
        host = manifest.get(canonical_event_name(event), {}).get("host", "not recorded")
    return host, wall_clock_hours(event)


def physical_intervals(event: Path, model: dict[str, Any]) -> dict[str, tuple[float, float, float]]:
    """Return 16th/50th/84th posterior percentiles in physical coordinates."""
    chain_path = event / "chain.npz"
    if not chain_path.is_file():
        return {}
    try:
        with np.load(chain_path) as data:
            chain = np.asarray(data["chain"], dtype=float)
    except (KeyError, OSError, ValueError):
        return {}
    if chain.ndim == 4:
        chain = chain[:, 0]
    if chain.ndim != 3:
        return {}
    flat = chain.reshape(-1, chain.shape[-1])
    entries = fitted_scales(model)
    if flat.shape[1] != len(entries):
        return {}
    intervals: dict[str, tuple[float, float, float]] = {}
    for index, (name, scale) in enumerate(entries):
        values = flat[:, index]
        values = values[np.isfinite(values)]
        if values.size == 0:
            continue
        q16, q50, q84 = np.quantile(values, (0.16, 0.5, 0.84))
        if scale == "log":
            q16, q50, q84 = 10.0**q16, 10.0**q50, 10.0**q84
        elif scale == "ln":
            q16, q50, q84 = np.exp(q16), np.exp(q50), np.exp(q84)
        intervals[name] = (float(q16), float(q50), float(q84))
    return intervals


def parameter_rows(event: Path, model: dict[str, Any]) -> list[tuple[str, str, str, str, str, str]]:
    minimized_path = event / "minimized" / "minimized.json"
    if not minimized_path.is_file():
        return []
    try:
        minimized = dict(flatten_parameters(json.loads(minimized_path.read_text())))
    except (json.JSONDecodeError, OSError):
        return []
    intervals = physical_intervals(event, model)
    rows: list[tuple[str, str, str, str, str, str]] = []
    # minimized.json contains fixed values for provenance as well as fitted
    # coordinates.  Keep this table faithful to the MCMC parameter vector.
    for name, _ in fitted_scales(model):
        if name not in minimized:
            continue
        value = minimized[name]
        symbol, meaning = PARAMETER_LABELS.get(name, (name, name.replace("_", " ")))
        interval = intervals.get(name)
        if interval is None:
            median = plus = minus = "not available"
            minimized_text = number(value)
        else:
            q16, q50, q84 = interval
            minimized_text, median, plus, minus = formatted_parameter_values(
                value, q50, q84 - q50, q50 - q16
            )
        rows.append((symbol, LatexCell(meaning), minimized_text, median, plus, minus))
    return rows


def load_campaign_metadata(campaign: Path) -> dict[str, str]:
    """Read durable campaign setup notes written at campaign creation time."""
    path = campaign / "campaign_metadata.json"
    candidates = [path]
    if not path.is_file():
        share_path, _ = campaign_identity(campaign)
        for candidate in PROJECT_ROOT.glob("reports/*/campaign_metadata.json"):
            try:
                payload = json.loads(candidate.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict) and str(payload.get("share_campaign", "")) == share_path:
                candidates.append(candidate)
                break
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            payload = json.loads(candidate.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            metadata = {str(key): str(value) for key, value in payload.items() if value not in (None, "")}
            # The meeting-book refresh is also the publication path; make the
            # setup record travel with the shared campaign from then onward.
            if candidate != path:
                path.write_text(json.dumps(metadata, indent=2) + "\n")
            return metadata
    return {}


def load_event_decision_record(event: Path) -> dict[str, Any]:
    """Read the pre-dispatch decision snapshot that travels with a run."""
    path = event / "decision_record.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_campaign_tracking_notes(campaign: Path) -> dict[str, dict[str, Any]]:
    """Read the campaign-local snapshot of live tracking-sheet notes."""
    path = campaign / "tracking_sheet_notes.json"
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    events = payload.get("events", {})
    return events if isinstance(events, dict) else {}


def record_text(value: object) -> str:
    """Collapse spreadsheet-style line breaks for compact report paragraphs."""
    return " ".join(str(value).split())


def event_needs_refresh(event: Path) -> bool:
    """Only refresh a completed event if a meeting-book product is missing/stale."""
    if not (event / "core_postfit_products.validated").is_file():
        return False
    # Campaign-level physical histograms/scatters use this derived posterior,
    # even when an older event directory already happens to contain its PDFs.
    if not (event / "jet_energy_posterior.npz").is_file():
        return True
    if not (event / "density_shell_mass_walkers.csv").is_file():
        return True
    try:
        density_summary = json.loads((event / "density_shell_mass_summary.json").read_text())
    except (OSError, json.JSONDecodeError):
        return True
    if density_summary.get("method_version") != DENSITY_SHELL_METHOD_VERSION:
        return True
    style_version = event / ".postfit_product_style_version"
    if not style_version.is_file() or style_version.read_text().strip() != POSTFIT_PRODUCT_STYLE_VERSION:
        return True
    source_paths = [event / "chain.npz", event / "model.toml", event / "best_fit.json", event / "minimized" / "minimized.json"]
    source_mtime = max((path.stat().st_mtime for path in source_paths if path.is_file()), default=0.0)
    for _, choices in EVENT_FIGURES:
        figure = first_existing(event, choices)
        if figure is None or figure.stat().st_mtime < source_mtime:
            return True
    return False


def resolution_needs_refresh(event: Path) -> tuple[bool, bool]:
    """Return (rerun_fixed_model, replot) for the event resolution ladder."""
    ladder = event / "resolution_ladder"
    summary = ladder / "resolution_summary.csv"
    fluxes = ladder / "modeled_observation_fluxes.csv"
    metadata = ladder / "resolution_run_metadata.json"
    plot_paths = tuple(
        ladder / name
        for name in (
            "resolution_convergence.pdf",
            "resolution_convergence.png",
            "resolution_convergence_signed.pdf",
            "resolution_convergence_signed.png",
            "resolution_light_curve_overlay.pdf",
            "resolution_light_curve_overlay.png",
        )
    )
    rerun = not (summary.is_file() and fluxes.is_file() and metadata.is_file())
    if not rerun:
        try:
            recorded_version = str(json.loads(metadata.read_text()).get("resolution_ladder_version", ""))
        except (OSError, json.JSONDecodeError):
            recorded_version = ""
        rerun = recorded_version != RESOLUTION_LADDER_VERSION
    if rerun:
        return True, True
    version = ladder / ".resolution_plot_version"
    latest_data = max(summary.stat().st_mtime, fluxes.stat().st_mtime)
    replot = (
        any(not path.is_file() or path.stat().st_mtime < latest_data for path in plot_paths)
        or not version.is_file()
        or version.read_text().strip() != RESOLUTION_PLOT_VERSION
    )
    return False, replot


def refresh_resolution_products(event: Path) -> None:
    """Generate a fixed-solution convergence ladder for published results."""
    rerun, replot = resolution_needs_refresh(event)
    ladder = event / "resolution_ladder"
    if rerun:
        print(f"REFRESH resolution_ladder event={event.name}")
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "run_vegas_resolution_ladder.py"),
             "--event", canonical_event_name(event), "--results", str(event), "--out", str(ladder)],
            cwd=PROJECT_ROOT,
            check=True,
        )
    if rerun or replot:
        print(f"REFRESH resolution_plots event={event.name}")
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "plot_vegas_resolution_ladder.py"),
             "--event-dir", str(ladder)],
            cwd=PROJECT_ROOT,
            check=True,
        )
        (ladder / ".resolution_plot_version").write_text(RESOLUTION_PLOT_VERSION + "\n")


def refresh_event_products(campaign: Path) -> None:
    script = PROJECT_ROOT / "scripts" / "generate_postfit_products.py"
    for event in event_dirs(campaign):
        if event_needs_refresh(event):
            print(f"REFRESH event_products event={event.name}")
            subprocess.run(
                [sys.executable, str(script), "--results", str(event), "--event", canonical_event_name(event), "--parallel-products", "--product-workers", "4"],
                cwd=PROJECT_ROOT,
                check=True,
            )
        if (event / "core_postfit_products.validated").is_file():
            refresh_resolution_products(event)


def refresh_campaign_comparisons(campaign: Path) -> None:
    """Generate aggregate histograms/scatters from whatever published runs exist."""
    completed = [
        event
        for event in event_dirs(campaign)
        if (event / "core_postfit_products.validated").is_file()
        and (event / "minimized" / "minimized.json").is_file()
    ]
    if not completed:
        return
    # Alternate-data/physics branches deliberately retain a descriptive suffix.
    # Their one-event meeting books should not invoke cross-event scripts whose
    # campaign discovery is intentionally restricted to canonical GRB folders.
    if any(not BASE_EVENT_RE.fullmatch(event.name) for event in completed):
        return
    histograms = list((campaign / "histograms").glob("*.pdf"))
    comparisons = list((campaign / "comparison_plots").glob("*.pdf"))
    source_times = [
        (event / "minimized" / "minimized.json").stat().st_mtime
        for event in completed
    ]
    source_times.extend(
        (event / "density_shell_mass_walkers.csv").stat().st_mtime
        for event in completed
        if (event / "density_shell_mass_walkers.csv").is_file()
    )
    latest_source = max(source_times)
    latest_product = max((path.stat().st_mtime for path in histograms + comparisons), default=0.0)
    convergence_products = (
        campaign / "comparison_plots" / "campaign_resolution_convergence.pdf",
        campaign / "comparison_plots" / "convergence_vs_viewing_angle.pdf",
    )
    density_comparison = campaign / "histograms" / "density_shell_mass_density_comparison_histograms.pdf"
    csm_physical_comparisons = (
        campaign / "comparison_plots" / "csm_mean_density_vs_n017.pdf",
        campaign / "comparison_plots" / "jet_mass_vs_csm_shell_mass.pdf",
        campaign / "comparison_plots" / "csm_shell_mass_density_vs_k.pdf",
        campaign / "comparison_plots" / "theta_c_vs_profile_mean_density.pdf",
        campaign / "comparison_plots" / "theta_c_vs_profile_radius.pdf",
    )
    if histograms and comparisons and density_comparison.is_file() and all(path.is_file() for path in convergence_products + csm_physical_comparisons) and latest_product >= latest_source:
        return
    print(f"REFRESH campaign_comparisons events={len(completed)}")
    subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "plot_campaign_physical_parameter_histograms.py"), "--campaign", str(campaign)], cwd=PROJECT_ROOT, check=True)
    subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "plot_campaign_density_shell_histograms.py"), "--campaign", str(campaign)], cwd=PROJECT_ROOT, check=True)
    subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "plot_campaign_csm_physical_scatters.py"), "--campaign", str(campaign)], cwd=PROJECT_ROOT, check=True)
    subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "plot_minimized_core_mass_vs_solid_angle.py"), "--campaign", str(campaign)], cwd=PROJECT_ROOT, check=True)
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "plot_vegas_resolution_ladder.py"),
         "--campaign", str(campaign), "--out-root", str(campaign / "comparison_plots")],
        cwd=PROJECT_ROOT,
        check=True,
    )


def move_campaign_plots(campaign: Path, dry_run: bool) -> list[tuple[str, str, str]]:
    """Tidy loose aggregate figures without ever changing GRB event folders."""
    histograms = campaign / "histograms"
    comparisons = campaign / "comparison_plots"
    moves: list[tuple[str, str, str]] = []
    for path in sorted(campaign.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".png", ".csv"}:
            continue
        if path.name in {SUMMARY_PDF, MOVE_MANIFEST, "dispatch_manifest.csv"}:
            continue
        stem = path.stem.lower()
        if path.suffix.lower() == ".csv":
            is_plot_data = (
                "histogram" in stem
                or any(token in stem for token in ("scatter", "comparison", "_vs_", "convergence", "resolution", "rerun_priority"))
                or any((directory / f"{path.stem}{suffix}").is_file()
                       for directory in (campaign, histograms, comparisons)
                       for suffix in (".pdf", ".png"))
            )
            if not is_plot_data:
                continue
        if "histogram" in stem:
            target_dir, category = histograms, "histogram"
        elif any(token in stem for token in ("scatter", "comparison", "_vs_", "convergence", "resolution", "rerun_priority")):
            target_dir, category = comparisons, "comparison_plot"
        else:
            # A loose graphic at a campaign root is necessarily aggregate; it
            # belongs with comparisons, rather than among event-level files.
            target_dir, category = comparisons, "campaign_plot"
        destination = target_dir / path.name
        if destination.exists():
            if destination.read_bytes() == path.read_bytes():
                if not dry_run:
                    path.unlink()
                moves.append((path.name, destination.relative_to(campaign).as_posix(), "duplicate_removed"))
                continue
            # Aggregate scripts intentionally regenerate same-named plots at the
            # campaign root.  Refresh the organized copy in place; other files
            # still retain the collision guard above by name and destination.
            if not dry_run:
                shutil.copy2(path, destination)
                path.unlink()
            moves.append((path.name, destination.relative_to(campaign).as_posix(), "refreshed_replaced"))
            continue
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
            path.replace(destination)
        moves.append((path.name, destination.relative_to(campaign).as_posix(), category))
    if not dry_run and moves:
        with (campaign / MOVE_MANIFEST).open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(("source_name", "organized_path", "category"))
            writer.writerows(moves)
    return moves


def load_settings(events: list[Path]) -> dict[str, object]:
    samplers: list[dict[str, object]] = []
    for event in events:
        path = event / "mcmc_settings.toml"
        if path.is_file():
            sampler = read_toml(path).get("sampler", {})
            if isinstance(sampler, dict):
                samplers.append(sampler)
    if not samplers:
        return {}
    settings: dict[str, object] = {}
    for key in ("name", "num_walkers", "ntemps", "burn_length", "run_length"):
        values = [sampler[key] for sampler in samplers if key in sampler]
        if not values:
            continue
        signatures = {json.dumps(value, sort_keys=True, default=str) for value in values}
        settings[key] = values[0] if len(signatures) == 1 and len(values) == len(samplers) else "varies by event"
    return settings


def inferred_campaign_notes(events: list[Path]) -> tuple[str, str]:
    """Recover portable setup facts that live in every published event model."""
    initial = "Saved event-specific initial positions; see each result directory for provenance."
    if events and all((event / "initial_positions.npz").is_file() for event in events):
        initial = "Event-specific initial-position ensembles are retained with every published result."
    for event in events:
        model_path = event / "model.toml"
        if not model_path.is_file():
            continue
        model = read_toml(model_path)
        fixed = {name: value for name, _, value in fitted_and_fixed(model)[1]}
        keys = ("vegas_resolution_phi", "vegas_resolution_theta", "vegas_resolution_t")
        if all(key in fixed for key in keys):
            return initial, "VegasAfterglow (phi, theta, time) = (" + ", ".join(fixed[key] for key in keys) + ")."
    return initial, "Recorded in the campaign configuration."


def common_priors(events: list[Path]) -> list[tuple[str, str, str, str]]:
    signatures: dict[str, set[tuple[str, str, str]]] = {}
    seen = 0
    for event in events:
        path = event / "model.toml"
        if not path.is_file():
            continue
        seen += 1
        fitted, _ = fitted_and_fixed(read_toml(path))
        for name, scale, bounds in fitted:
            signatures.setdefault(name, set()).add((scale, bounds, event.name))
    rows: list[tuple[str, str, str, str]] = []
    for name, entries in sorted(signatures.items()):
        values = {(scale, bounds) for scale, bounds, _ in entries}
        if len(values) == 1 and len(entries) == seen:
            scale, bounds = values.pop()
            symbol, _ = PARAMETER_LABELS.get(name, (name, name.replace("_", " ")))
            rows.append((symbol, scale, bounds, "common"))
    return rows


def document(campaign: Path, title: str, purpose: str, metadata: dict[str, str]) -> str:
    # The watcher publishes a marker only after minimization, ordinary
    # post-processing, and the numerical ladder all validate.  Restrict the
    # meeting book to those completed events so a partially copied directory
    # can never be mistaken for a reviewed result.
    events = [
        event
        for event in event_dirs(campaign)
        if (event / "core_postfit_products.validated").is_file()
    ]
    manifest = campaign_manifest(campaign)
    metadata = {**load_campaign_metadata(campaign), **metadata}
    campaign_tracking_notes = load_campaign_tracking_notes(campaign)
    purpose = metadata.get("purpose", purpose)
    settings = load_settings(events)
    inferred_initialization, inferred_resolution = inferred_campaign_notes(events)
    complete = sum((event / "core_postfit_products.validated").is_file() for event in events)
    setup_rows = [
        ("Campaign identifier", tex_campaign_identifier(campaign.name)),
        ("Purpose", purpose),
        ("Published GRB directories", str(len(events))),
        ("Validated post-fit products", f"{complete}/{len(events)}"),
        ("Sampler", str(settings.get("name", metadata.get("sampler", "not recorded")))),
        ("Walkers", str(settings.get("num_walkers", metadata.get("walkers", "not recorded")))),
        ("Temperatures", str(settings.get("ntemps", metadata.get("temperatures", "not recorded")))),
        ("Burn-in iterations", str(settings.get("burn_length", metadata.get("burn", "not recorded")))),
        ("Production iterations", str(settings.get("run_length", metadata.get("production", "not recorded")))),
        ("Workers per host", str(settings.get("workers", metadata.get("workers", "not recorded")))),
        ("Seed source campaign", tex_campaign_path(metadata.get("seed_source_campaign", "Not recorded at campaign setup."))),
        ("Seeding method", metadata.get("seeding_method", metadata.get("initialization", inferred_initialization))),
        ("Initialization", metadata.get("initialization", inferred_initialization)),
        ("Numerical resolution", metadata.get("resolution", inferred_resolution)),
    ]
    common = common_priors(events)
    generated_date = datetime.now(UTC).strftime("%Y-%m-%d")
    share_path, folder_name = campaign_identity(campaign)
    share_path = metadata.get("published_share_path", share_path)
    folder_name = metadata.get("published_folder_name", folder_name)
    header_title = rf"\shortstack[l]{{\tiny\texttt{{\detokenize{{{folder_name}}}}}\\[-1pt]\scriptsize {tex(campaign_date(campaign))} to {generated_date}}}"
    abstract = metadata.get(
        "abstract",
        f"{purpose} This meeting book preserves the campaign identity, configuration, "
        "posterior diagnostics, and cross-event comparisons so the fitted results can be "
        "reviewed and discussed reproducibly.",
    )
    result = [r"\documentclass[10pt,letterpaper]{article}", r"\usepackage[margin=0.62in]{geometry}", r"\usepackage{graphicx}", r"\usepackage{booktabs}", r"\usepackage{longtable}", r"\usepackage{array}", r"\usepackage{fancyhdr}", r"\usepackage[colorlinks=true,linkcolor=blue,urlcolor=blue,citecolor=blue]{hyperref}", r"\setlength{\headheight}{27pt}", r"\pagestyle{fancy}", r"\fancyhf{}", rf"\lhead{{{header_title}}}", r"\rhead{\nouppercase{\rightmark}}", r"\cfoot{\thepage}", r"\begin{document}", rf"\title{{{tex(title)}}}", rf"\date{{Generated {generated_date} UTC}}", r"\maketitle", rf"\noindent\textbf{{VegasGRBruns share folder:}} \nolinkurl{{{share_path.rsplit('/', 1)[0] + '/'}}}\\", r"\noindent\textbf{Campaign folder:}\\", rf"\noindent {tex_campaign_cover_identifier(folder_name)}", r"\begin{abstract}", tex(abstract), r"\end{abstract}", r"\noindent\textbf{GRBs in this campaign:} "]
    result.append(r"\quad\allowbreak{} ".join(rf"\hyperref[grb:{event.name}]{{GRB {tex(event.name)}}}" for event in events))
    result.extend((r"\clearpage", r"\section{Campaign Set-up and Purpose}", compact_table(("Item", "Value"), setup_rows, "p{0.27\\textwidth}p{0.66\\textwidth}"), r"\subsection{Common Fitted-Prior Bounds}", compact_table(("Parameter", "Scale", "Bounds / prior", "Coverage"), common, "p{0.25\\textwidth}p{0.12\\textwidth}p{0.40\\textwidth}p{0.15\\textwidth}", math_columns={0}), r"\noindent Event-specific calibration offsets and special priors are listed with the corresponding GRB rather than mixed into this campaign-wide table.", r"\subsection{Reproducibility Notes}", r"This document is generated directly from validated, published campaign files. Before writing this book, the generator checks every completed event product, requires its fixed-solution numerical-resolution ladder, and refreshes only missing or stale results. Therefore the meeting book can be rebuilt after each completed GRB rather than waiting for the slowest campaign member. The campaign-level plot organization is recorded in \texttt{campaign\_plot\_organization.csv}; event products remain in their original GRB directories.", r"\clearpage", r"\section{Gamma-ray Bursts}", r"\subsection{Run Index}"))
    index_rows = []
    for event in events:
        host, runtime = event_run_record(event, manifest)
        index_rows.append((rf"\hyperref[grb:{event.name}]{{GRB {tex(event.name)}}}", host, runtime))
    total_seconds = sum(seconds for event in events if (seconds := wall_clock_seconds(event)) is not None)
    total_runtime = f"{total_seconds / 3600.0:.1f} h" if total_seconds else "not recorded"
    result.append(compact_table(("GRB", "Compute host", "MCMC wall clock"), index_rows, "p{0.24\\textwidth}p{0.40\\textwidth}p{0.25\\textwidth}", math_columns={0}, footer=(r"\textbf{Total wall-clock time}", "", rf"\textbf{{{total_runtime}}}"), footer_math_columns={0, 2}))
    result.append(r"\clearpage")
    for event in events:
        result.extend((rf"\subsection{{GRB {tex(event.name)}}}", rf"\label{{grb:{event.name}}}", rf"\markright{{GRB {tex(event.name)}}}"))
        decision_record = load_event_decision_record(event)
        tracking_entry = campaign_tracking_notes.get(
            event.name, campaign_tracking_notes.get(canonical_event_name(event), {})
        )
        tracking_notes = tracking_entry.get("notes", {}) if isinstance(tracking_entry, dict) else {}
        if decision_record or tracking_notes:
            summary = record_text(decision_record.get("decision_summary", ""))
            record_rows = []
            tracking_row = decision_record.get("tracking_row") or tracking_entry.get("tracking_row")
            if tracking_row:
                record_rows.append(("Tracking-sheet row", str(tracking_row)))
            if decision_record.get("staged_utc"):
                record_rows.append(("Decision snapshot staged", record_text(decision_record["staged_utc"])))
            if summary:
                record_rows.append(("Decision summary", summary))
            result.append(r"\subsubsection{Decision Record and Tracking-Sheet Notes}")
            if record_rows:
                result.append(compact_table(("Item", "Record"), record_rows, "p{0.26\\textwidth}p{0.67\\textwidth}"))
            for label, key in (
                ("Pre-dispatch decision", "pre_dispatch_decision"),
                ("Resolution-ladder basis", "refinement_basis"),
                ("Selected refinement", "selected_refinement"),
                ("Post-fit protocol", "postfit_protocol"),
            ):
                value = record_text(decision_record.get(key, ""))
                if value:
                    result.extend((rf"\paragraph{{{tex(label)}.}}", tex_breakable_text(value)))
            record_tracking_notes = decision_record.get("tracking_sheet_notes", {})
            if isinstance(record_tracking_notes, dict):
                for source, note in record_tracking_notes.items():
                    value = record_text(note)
                    if value:
                        result.extend((rf"\paragraph{{Tracking sheet: {tex(source)}.}}", tex_breakable_text(value)))
            if isinstance(tracking_notes, dict):
                for source, note in tracking_notes.items():
                    value = record_text(note)
                    if value:
                        result.extend((rf"\paragraph{{Tracking sheet: {tex(source)}.}}", tex_breakable_text(value)))
            result.append(r"\clearpage")
        included: set[Path] = set()
        for caption, choices in EVENT_FIGURES:
            figure = first_existing(event, choices)
            if figure is None or figure in included:
                continue
            included.add(figure)
            relative = figure.relative_to(campaign)
            result.extend((r"\begin{center}", rf"\includegraphics[width=0.96\textwidth,height=0.82\textheight,keepaspectratio]{{{tex_path(relative)}}}", rf"\par\small\textit{{GRB {tex(event.name)}: {tex(event_figure_caption(caption))}}}", r"\end{center}", r"\clearpage"))
            if caption == "All retained walker light curves":
                resolution_overlay = event / "resolution_ladder" / "resolution_light_curve_overlay.pdf"
                if resolution_overlay.is_file():
                    relative = resolution_overlay.relative_to(campaign)
                    result.extend((r"\begin{center}", rf"\includegraphics[width=0.96\textwidth,height=0.82\textheight,keepaspectratio]{{{tex_path(relative)}}}", rf"\par\small\textit{{GRB {tex(event.name)}: fixed-minimized-solution light curves evaluated over coupled numerical-resolution grids. Lighter curves are coarser, darker curves are finer, and the thick dashed curve is the production grid used for the MCMC.}}", r"\end{center}", r"\clearpage"))
                convergence = event / "resolution_ladder" / "resolution_convergence_signed.pdf"
                if not convergence.is_file():
                    convergence = event / "resolution_ladder" / "resolution_convergence.pdf"
                if convergence.is_file():
                    relative = convergence.relative_to(campaign)
                    result.extend((r"\begin{center}", rf"\includegraphics[width=0.96\textwidth,height=0.82\textheight,keepaspectratio]{{{tex_path(relative)}}}", rf"\par\small\textit{{GRB {tex(event.name)}: signed flux and fit-statistic shifts relative to the production grid, estimated repeat-MCMC runtime, and one-control sensitivity at fixed minimized parameters. The production point is the zero-reference.}}", r"\end{center}", r"\clearpage"))
        model_path = event / "model.toml"
        minimized_path = event / "minimized" / "minimized.json"
        fixed_rows: list[tuple[str, str, str]] = []
        minimized_rows: list[tuple[str, str, str, str, str, str]] = []
        if model_path.is_file():
            model = read_toml(model_path)
            _, fixed_rows = fitted_and_fixed(model)
            minimized_rows = parameter_rows(event, model)
        fixed_display = []
        for name, scale, value in fixed_rows:
            symbol, meaning = PARAMETER_LABELS.get(name, (name, name.replace("_", " ")))
            fixed_display.append((symbol, LatexCell(meaning), scale, value))
        result.extend((r"\subsubsection{Fitted Parameters}", compact_table(("Symbol", "Physical quantity", "Minimized", "Posterior median", "+68%", "-68%"), minimized_rows, "p{0.12\\textwidth}p{0.30\\textwidth}p{0.14\\textwidth}p{0.14\\textwidth}p{0.12\\textwidth}p{0.12\\textwidth}", math_columns={0, 2, 3, 4, 5}), r"\noindent The uncertainty columns are the physical-coordinate posterior 16th--84th percentile half-widths about the posterior median; the minimized column remains the best-fit optimization result.", r"\subsubsection{Fixed Parameters}", compact_table(("Symbol", "Physical quantity", "Scale", "Fixed value"), fixed_display, "p{0.17\\textwidth}p{0.45\\textwidth}p{0.15\\textwidth}p{0.15\\textwidth}", math_columns={0})))
        result.append(r"\clearpage")
    result.append(r"\section{Comparison of Results}")
    comparison_files = []
    for directory in (campaign / "comparison_plots", campaign / "histograms"):
        if directory.is_dir():
            comparison_files.extend(directory.glob("*.pdf"))
    def comparison_priority(path: Path) -> tuple[int, str]:
        stem = path.stem.lower()
        keys = (
            ("campaign_resolution_convergence", 0),
            ("convergence_vs_viewing_angle", 1),
            ("mass_vs_core_energy", 10), ("jet_core_energy", 11),
            ("mass_vs_solid_angle", 20), ("jet_mass", 21),
            ("density_shell_mass_density", 25),
            ("csm_mean_density_vs_n017", 26),
            ("jet_mass_vs_csm_shell_mass", 27),
            ("csm_shell_mass_density_vs_k", 28),
            ("theta_c_vs_profile_mean_density", 29),
            ("theta_c_vs_profile_radius", 30),
            ("density_normalization_vs_k", 31), ("n017", 32), ("k_", 33),
        )
        return next(((priority, stem) for token, priority in keys if token in stem), (90, stem))
    comparison_files = [path for path in comparison_files if "ampy_comparison" not in path.stem.lower()]
    ordered_comparisons = sorted(comparison_files, key=comparison_priority)
    convergence = [
        path for path in ordered_comparisons
        if any(token in path.stem.lower() for token in ("campaign_resolution_convergence", "convergence_vs_viewing_angle"))
    ]
    remaining = [path for path in ordered_comparisons if path not in convergence]

    def append_comparison_page(
        figures: list[Path], *, tall: bool = False, full_page: bool = False
    ) -> None:
        height = "0.68\\textheight" if full_page else "0.40\\textheight" if tall else "0.36\\textheight"
        result.append(r"\begin{center}")
        for index, figure in enumerate(figures):
            relative = figure.relative_to(campaign)
            result.extend((
                rf"\includegraphics[width=0.94\textwidth,height={height},keepaspectratio]{{{tex_path(relative)}}}",
                rf"\par\small\textit{{{tex(comparison_figure_caption(figure))}}}",
            ))
            if index + 1 < len(figures):
                result.append(r"\vspace{0.45cm}")
        result.extend((r"\end{center}", r"\clearpage"))

    if convergence:
        append_comparison_page(convergence[:2], tall=True)
    density_shell_comparison = [
        path for path in remaining
        if "density_shell_mass_density_comparison_histograms" in path.stem.lower()
    ]
    remaining = [path for path in remaining if path not in density_shell_comparison]
    # This PDF already contains the matched mass and mean-density histograms.
    # Keep it alone so Section 3 presents that comparison as one legible unit.
    for path in density_shell_comparison:
        append_comparison_page([path])
    # These three physical cross-event diagnostics have dense 15-event error
    # bars and legends.  Give each one a full page so their scales remain
    # useful during a meeting and in the archived PDF.
    csm_physical_stems = {
        "csm_mean_density_vs_n017",
        "jet_mass_vs_csm_shell_mass",
        "csm_shell_mass_density_vs_k",
        "theta_c_vs_profile_mean_density",
        "theta_c_vs_profile_radius",
    }
    csm_physical = [path for path in remaining if path.stem.lower() in csm_physical_stems]
    remaining = [path for path in remaining if path not in csm_physical]
    for path in csm_physical:
        append_comparison_page([path], full_page=True)
    branch_diagnostics = [
        path for path in remaining
        if path.stem.lower() in {
            "090424_early_xray_shape_comparison",
            "090424_fit_overlays_by_dataset",
            "090424_fit_quality_by_dataset",
        }
    ]
    remaining = [path for path in remaining if path not in branch_diagnostics]
    for path in branch_diagnostics:
        append_comparison_page([path], full_page=True)
    for index in range(0, len(remaining), 2):
        append_comparison_page(remaining[index:index + 2])
    result.append(r"\end{document}")
    return "\n".join(result) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, help="One published Share_Folder campaign directory")
    parser.add_argument("--all-under", type=Path, help="Retroactively process complete campaigns two levels under this production-runs root")
    parser.add_argument("--complete-only", action="store_true", help="With --all-under, require every discovered event directory to have its validation marker")
    parser.add_argument("--title", help="Document title; defaults to a readable campaign name")
    parser.add_argument("--purpose", default="Campaign meeting summary generated from published results.")
    parser.add_argument("--metadata-json", type=Path, help="Optional small JSON file with initialization/resolution notes")
    parser.add_argument("--dry-run", action="store_true", help="Report plot organization without moving or compiling")
    parser.add_argument("--no-refresh-products", action="store_true", help="Skip the completed-product and campaign-comparison refresh pass")
    parser.add_argument("--no-organize-plots", action="store_true", help="Leave root-level aggregate plots in place")
    parser.add_argument("--no-compile", action="store_true", help="Write LaTeX but do not invoke tectonic")
    args = parser.parse_args()
    if bool(args.campaign) == bool(args.all_under):
        parser.error("supply exactly one of --campaign or --all-under")
    if args.all_under:
        root = args.all_under.expanduser().resolve()
        targets = []
        for candidate in sorted(root.glob("*/*")):
            if not candidate.is_dir() or "trash" in candidate.parts:
                continue
            events = event_dirs(candidate)
            if not events:
                continue
            if args.complete_only:
                events_complete = all((event / "core_postfit_products.validated").is_file() for event in events)
                campaign_complete = (candidate / "campaign_products.validated").is_file() or len(events) == 1
                if not events_complete or not campaign_complete:
                    continue
            targets.append(candidate)
        if not targets:
            raise SystemExit(f"No matching campaign directories below {root}")
        for target in targets:
            command = [sys.executable, str(Path(__file__).resolve()), "--campaign", str(target), "--purpose", args.purpose]
            if args.dry_run:
                command.append("--dry-run")
            if args.no_organize_plots:
                command.append("--no-organize-plots")
            if args.no_refresh_products:
                command.append("--no-refresh-products")
            if args.no_compile:
                command.append("--no-compile")
            subprocess.run(command, check=True)
        print(f"PROCESSED {len(targets)} campaigns under {root}")
        return
    campaign = args.campaign.expanduser().resolve()
    if not campaign.is_dir() or "trash" in campaign.parts:
        raise SystemExit(f"Campaign must be an existing non-trash directory: {campaign}")
    events = event_dirs(campaign)
    if not events:
        raise SystemExit(f"No GRB event directories found in {campaign}")
    metadata: dict[str, str] = {}
    if args.metadata_json:
        metadata = {str(key): str(value) for key, value in json.loads(args.metadata_json.read_text()).items()}
    if not args.no_refresh_products and not args.dry_run:
        refresh_event_products(campaign)
        refresh_campaign_comparisons(campaign)
    moves = [] if args.no_organize_plots else move_campaign_plots(campaign, args.dry_run)
    title = args.title or "GRB Campaign: " + campaign.name.replace("_", " ")
    source = document(campaign, title, args.purpose, metadata)
    tex_path_out = campaign / SUMMARY_TEX
    if args.dry_run:
        print(f"DRY RUN events={len(events)} proposed_plot_moves={len(moves)} tex={tex_path_out}")
        return
    tex_path_out.write_text(source)
    print(f"WROTE {tex_path_out}")
    print(f"ORGANIZED {len(moves)} campaign-level figures")
    if args.no_compile:
        return
    engine = shutil.which("tectonic")
    if engine is None:
        raise SystemExit("tectonic is required to compile the meeting PDF; install it with `brew install tectonic`.")
    completed = subprocess.run([engine, "--outdir", ".", tex_path_out.name], cwd=campaign, text=True)
    if completed.returncode:
        raise SystemExit(completed.returncode)
    pdf = campaign / SUMMARY_PDF
    if not pdf.is_file() or pdf.stat().st_size == 0:
        raise SystemExit(f"Expected PDF was not written: {pdf}")
    print(f"WROTE {pdf}")


if __name__ == "__main__":
    main()
