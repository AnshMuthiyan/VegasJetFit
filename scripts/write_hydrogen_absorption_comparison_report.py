#!/usr/bin/env python3
"""Analyze matched gas-absorption fits and build a meeting-ready PDF."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jetfit.ampy import Ampy
from jetfit.core import utils
from jetfit.core.hydrogen_absorption import hydrogen_transmission
from jetfit.mcmc.mcmc import (
    calibration_offsets,
    chi_squared,
    log_likelihood_fn,
    log_posterior_fn,
    slop,
)
from scripts.minimize import initial_from_best_fit


EVENTS = ("160131A", "220101A")
VARIANTS = ("none", "igm", "igm_host")
LABELS = {
    "none": "Gas off",
    "igm": "Inoue14 IGM",
    "igm_host": r"Inoue14 IGM + host H I",
}
COLORS = {"none": "#555555", "igm": "#2878B5", "igm_host": "#B05A32"}


def tag(event: str, variant: str) -> str:
    return f"{event}_hydrogen_{variant}_bandpass_verified_5temp_25x100_v1"


def tex(value: object) -> str:
    replacements = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%",
        "_": r"\_", "#": r"\#", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in str(value))


def number(value: object, digits: int = 3) -> str:
    if value is None:
        return "not recorded"
    value = float(value)
    return f"{value:.{digits}f}" if math.isfinite(value) else "not finite"


def wall_clock_seconds(result: Path) -> float | None:
    candidates = (result / "run.log", ROOT / "logs" / f"{result.name}.log")
    for path in candidates:
        if not path.is_file():
            continue
        matches = re.findall(
            r"^real\s+([0-9]+(?:\.[0-9]+)?)\s*$",
            path.read_text(errors="replace"),
            flags=re.MULTILINE,
        )
        if matches:
            return float(matches[-1])
    return None


def residual_row(label, band, mask, statistic, fractional):
    selected = fractional[mask]
    return {
        "variant": label,
        "band": band,
        "n": int(mask.sum()),
        "minus2_log_likelihood": float(statistic),
        "median_fractional_residual": float(np.median(selected)),
        "median_abs_fractional_residual": float(np.median(np.abs(selected))),
        "rms_fractional_residual": float(np.sqrt(np.mean(selected**2))),
    }


def evaluate(event: str, variant: str) -> tuple[dict, list[dict], dict]:
    config = ROOT / "run_configs" / "hydrogen_absorption" / event / variant
    result = ROOT / "jetfit" / "results" / tag(event, variant)
    best = json.loads((result / "best_fit.json").read_text())
    ampy = Ampy(
        config / "obs.csv",
        config / "model.toml",
        bandpass_integration="verified",
        bandpass_nodes=16,
    )
    theta = initial_from_best_fit(ampy, best)
    params = ampy.mcmc.params.samples_to_dict(theta)
    obs = ampy.mcmc.models.obs
    modeled = ampy.mcmc.models.model(params)
    modeled = calibration_offsets(modeled, params.get("offsets"), obs.offsets)
    fitted_slop = slop(params.get("slop"), obs)
    values = np.asarray(obs.as_arrays.values, dtype=float)
    errors = np.asarray(obs.as_arrays.errors, dtype=float)
    bands = np.asarray(obs.as_arrays.bands, dtype=str)
    flux = np.asarray(obs.flux_loc, dtype=bool)
    spectral_index = np.asarray(obs.sindex_loc, dtype=bool)
    fractional = (modeled - values) / values

    loglike = log_likelihood_fn(theta, ampy.mcmc.params, ampy.mcmc.models)
    logpost = log_posterior_fn(theta, ampy.mcmc.params, ampy.mcmc.models)
    with np.load(result / "chain.npz", allow_pickle=False) as archive:
        chain = np.asarray(archive["chain"], dtype=float)
    if chain.ndim != 3 or chain.shape[-1] != theta.size:
        raise ValueError(f"Unexpected {event}/{variant} chain shape {chain.shape}.")
    flat = chain.reshape(-1, chain.shape[-1])
    posterior = {}
    for index, parameter in enumerate(ampy.mcmc.params.fitting):
        q16, median, q84 = np.percentile(flat[:, index], (16.0, 50.0, 84.0))
        posterior[parameter.name] = {
            "q16": float(q16), "median": float(median), "q84": float(q84),
            "scale": str(getattr(parameter.scale, "value", parameter.scale)),
        }

    rows = []
    for band in sorted(set(bands[flux]), key=str.lower):
        mask = flux & (bands == band)
        band_slop = fitted_slop if np.isscalar(fitted_slop) else np.asarray(fitted_slop)[mask]
        rows.append(residual_row(
            variant, band, mask,
            utils.chi_squared(modeled[mask], values[mask], errors[mask], band_slop),
            fractional,
        ))
    if spectral_index.any():
        rows.append(residual_row(
            variant, "spectral_index", spectral_index,
            utils.chi_squared(
                modeled[spectral_index], values[spectral_index], errors[spectral_index]
            ),
            fractional,
        ))
    total = chi_squared(modeled, obs, fitted_slop)
    rows.append(residual_row(
        variant, "ALL", np.ones(obs.length, dtype=bool), total, fractional
    ))
    if not np.isclose(total, -2.0 * loglike, rtol=0.0, atol=1.0e-7):
        raise RuntimeError(f"Likelihood decomposition failed for {event}/{variant}.")

    runtime = wall_clock_seconds(result)
    ndata = int(obs.length)
    nparams = int(theta.size)
    summary = {
        "event": event,
        "variant": variant,
        "label": LABELS[variant],
        "observations": ndata,
        "fitted_parameters": nparams,
        "minus2_log_likelihood": float(-2.0 * loglike),
        "minus2_log_posterior": float(-2.0 * logpost),
        "aic": float(-2.0 * loglike + 2.0 * nparams),
        "bic": float(-2.0 * loglike + nparams * math.log(ndata)),
        "wall_clock_seconds": runtime,
        "wall_clock_hours": runtime / 3600.0 if runtime is not None else None,
        "best_absorption": best.get("absorption", {}),
        "gas_models": {
            "igm": ampy.mcmc.params.igm_absorption_model,
            "host_hi": ampy.mcmc.params.host_hi_absorption_model,
        },
    }
    return summary, rows, posterior


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def save_figure(fig, output: Path, stem: str) -> None:
    fig.savefig(output / f"{stem}.png", dpi=220, bbox_inches="tight")
    fig.savefig(output / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_fit_differences(event: str, residuals: list[dict], output: Path) -> None:
    by_variant = {
        variant: {row["band"]: row for row in residuals if row["variant"] == variant}
        for variant in VARIANTS
    }
    bands = sorted(
        set(by_variant["none"]) & set(by_variant["igm"]) & set(by_variant["igm_host"]),
        key=lambda band: abs(
            by_variant["igm_host"][band]["minus2_log_likelihood"]
            - by_variant["none"][band]["minus2_log_likelihood"]
        ),
    )
    y = np.arange(len(bands))
    fig, ax = plt.subplots(figsize=(8.0, max(4.8, 0.32 * len(bands))))
    for offset, variant in ((-0.16, "igm"), (0.16, "igm_host")):
        delta = [
            by_variant[variant][band]["minus2_log_likelihood"]
            - by_variant["none"][band]["minus2_log_likelihood"]
            for band in bands
        ]
        ax.barh(y + offset, delta, height=0.30, label=LABELS[variant], color=COLORS[variant])
    ax.set_yticks(y, bands)
    ax.axvline(0.0, color="black", linewidth=0.8)
    ax.set_xlabel(r"Absorption model minus gas-off $(-2\ln\mathcal{L})$")
    ax.set_ylabel("Observed band")
    ax.set_title(f"GRB {event}: fit-statistic change by band")
    ax.grid(axis="x", alpha=0.25)
    ax.legend(frameon=False, loc="best")
    fig.tight_layout()
    save_figure(fig, output, f"{event}_hydrogen_absorption_band_fit_difference")


def posterior_shift_rows(posteriors: dict[str, dict]) -> list[dict]:
    common = sorted(set.intersection(*(set(posteriors[v]) for v in VARIANTS)))
    rows = []
    for name in common:
        baseline = posteriors["none"][name]
        base_sigma = 0.5 * (baseline["q84"] - baseline["q16"])
        row = {"parameter": name, "scale": baseline["scale"]}
        for variant in ("igm", "igm_host"):
            item = posteriors[variant][name]
            sigma = 0.5 * (item["q84"] - item["q16"])
            pooled = math.hypot(base_sigma, sigma)
            delta = item["median"] - baseline["median"]
            row[f"{variant}_minus_none"] = delta
            row[f"{variant}_standardized_shift"] = (
                delta / pooled if pooled > 0.0 else float("nan")
            )
            row[f"{variant}_median"] = item["median"]
        row["none_median"] = baseline["median"]
        rows.append(row)
    return rows


def plot_parameter_shifts(event: str, rows: list[dict], output: Path) -> None:
    rows = [row for row in rows if math.isfinite(row["igm_host_standardized_shift"])]
    rows.sort(key=lambda row: abs(row["igm_host_standardized_shift"]))
    y = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(8.0, max(5.0, 0.30 * len(rows))))
    ax.barh(
        y - 0.16, [row["igm_standardized_shift"] for row in rows],
        height=0.30, label=LABELS["igm"], color=COLORS["igm"],
    )
    ax.barh(
        y + 0.16, [row["igm_host_standardized_shift"] for row in rows],
        height=0.30, label=LABELS["igm_host"], color=COLORS["igm_host"],
    )
    ax.set_yticks(y, [row["parameter"] for row in rows])
    ax.axvline(0.0, color="black", linewidth=0.8)
    ax.axvline(-1.0, color="0.5", linewidth=0.8, linestyle="--")
    ax.axvline(1.0, color="0.5", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Posterior median shift (pooled 68% half-widths)")
    ax.set_title(f"GRB {event}: physical and nuisance-parameter response")
    ax.grid(axis="x", alpha=0.25)
    ax.legend(frameon=False, loc="best")
    fig.tight_layout()
    save_figure(fig, output, f"{event}_hydrogen_absorption_parameter_shifts")


def plot_transmission(
    event: str, provenance: dict, summaries: dict[str, dict], output: Path
) -> None:
    z = float(provenance["source_redshift"])
    wavelength = np.geomspace(900.0, 25000.0, 2400)
    nhi = summaries["igm_host"].get("best_absorption", {}).get("nhi_host")
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.plot(wavelength, np.ones_like(wavelength), color=COLORS["none"], label=LABELS["none"])
    ax.plot(
        wavelength,
        hydrogen_transmission(wavelength, z, igm_model="inoue2014"),
        color=COLORS["igm"], label=LABELS["igm"],
    )
    if nhi is not None:
        ax.plot(
            wavelength,
            hydrogen_transmission(
                wavelength, z, igm_model="inoue2014",
                host_model="trotter2011", nhi_host_cm2=float(nhi),
            ),
            color=COLORS["igm_host"], label=LABELS["igm_host"],
        )
    ax.axvline(1215.67 * (1.0 + z), color="0.35", linestyle="--", linewidth=1.0, label=r"Host Ly$\alpha$")
    ax.axvline(911.8 * (1.0 + z), color="0.55", linestyle=":", linewidth=1.0, label="Host Lyman limit")
    ax.set_xscale("log")
    ax.set_ylim(-0.03, 1.05)
    ax.set_xlabel(r"Observed wavelength [$\AA$]")
    ax.set_ylabel("Transmission")
    ax.set_title(f"GRB {event}: adopted neutral-hydrogen transmission")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False, ncol=2, fontsize=8, loc="lower right")
    fig.tight_layout()
    save_figure(fig, output, f"{event}_hydrogen_absorption_transmission")


def table(headers: tuple[str, ...], rows: list[tuple[str, ...]], columns: str) -> str:
    lines = [
        r"\begingroup\small\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.03}",
        rf"\noindent\begin{{tabularx}}{{\textwidth}}{{{columns}}}",
        r"\toprule", " & ".join(headers) + " \\\\", r"\midrule",
    ]
    lines.extend(" & ".join(row) + " \\\\" for row in rows)
    lines.extend((r"\bottomrule", r"\end{tabularx}", r"\endgroup"))
    return "\n".join(lines)


def build_tex(output: Path, payload: dict) -> str:
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        r"\documentclass[10pt,letterpaper]{article}",
        r"\usepackage[margin=0.68in]{geometry}", r"\usepackage{graphicx}",
        r"\usepackage{booktabs}", r"\usepackage{tabularx}",
        r"\usepackage{array}", r"\usepackage{float}", r"\usepackage{fancyhdr}",
        r"\usepackage[colorlinks=true,linkcolor=blue,urlcolor=blue,citecolor=blue]{hyperref}",
        r"\setlength{\headheight}{24pt}", r"\pagestyle{fancy}", r"\fancyhf{}",
        r"\lhead{GRB neutral-hydrogen absorption comparison}",
        r"\rhead{\scriptsize Inoue14 IGM and Trotter11 host H I}", r"\cfoot{\thepage}",
        r"\begin{document}",
        r"\title{Redshift-Dependent Lyman Absorption in VegasJetFit}", r"\author{}",
        rf"\date{{Generated {tex(generated)}}}", r"\maketitle",
        r"\begin{abstract}",
        (
            "This controlled diagnostic replaces the historical use of free per-band offsets "
            "as surrogates for Lyman suppression. For GRBs 160131A and 220101A, three fits "
            "share the same authoritative data, emission model, source-frame CCM dust law, "
            "Vegas grid, and correlated posterior-cloud draws: gas off; the deterministic "
            "mean Inoue et al. (2014) intergalactic attenuation; and that IGM model plus a "
            "log-uniform fitted host neutral-hydrogen column using the Trotter (2011) damped-"
            "Ly-alpha profile. Verified UVOT/HST response curves are integrated in the likelihood."
        ),
        r"\end{abstract}",
        r"\section{Scientific Audit}",
        (
            "Dylan's dissertation explicitly states that its fits did not model Lyman-forest "
            "attenuation for these bursts; instead, uvm2/uvw1 offsets for GRB 160131A and r/R "
            "offsets for GRB 220101A absorbed the suppression. The implementation tested here "
            "therefore adds missing physics rather than duplicating an active code path. The "
            "Inoue curve is a mean line of sight, not a realization of stochastic forest variance. "
            "The fitted host column is a separate gas parameter and is not the metal-sensitive "
            "equivalent X-ray column."
        ),
    ]
    material_filters = payload.get("material_filter_audit", [])
    if material_filters:
        lines.extend((
            r"\subsection{Filters Requiring the Correction}",
            (
                "This screening table lists event/filter combinations in the "
                "authoritative 15-burst manifest with more than one-percent mean "
                "IGM suppression. A verified response uses response-weighted mean "
                "transmission; an instrument-ambiguous historical label uses its "
                "central wavelength and is explicitly marked as an approximation."
            ),
            table(
                ("GRB", "Filter", "$z$", r"$\langle T_{\rm IGM}\rangle$", "Likelihood treatment"),
                [
                    (
                        tex(row["event"]), tex(row["filter"]),
                        number(row["redshift"], 3),
                        number(row["igm_transmission_used_for_likelihood_audit"], 3),
                        tex(str(row["treatment"]).replace("_", " ")),
                    )
                    for row in material_filters
                ],
                r"llrr>{\raggedright\arraybackslash}X",
            ),
        ))
    lines.append(r"\section{Run Summary}")
    summary_rows = []
    for event in EVENTS:
        for variant in VARIANTS:
            item = payload["events"][event]["summaries"][variant]
            summary_rows.append((
                event, tex(LABELS[variant]), str(item["fitted_parameters"]),
                number(item["minus2_log_likelihood"], 2), number(item["aic"], 2),
                number(item["wall_clock_hours"], 2),
            ))
    lines.append(table(
        ("GRB", "Gas model", "Free", r"$-2\ln\mathcal{L}$", "AIC", "Wall [h]"),
        summary_rows, r">{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}Xrrrr",
    ))
    lines.append(
        "All runs use five temperatures, 100 walkers, 25 burn-in steps, 100 retained "
        "production steps, eight workers, and 10-step checkpoints. These are controlled "
        "diagnostic continuations, not replacements for the authoritative long chains."
    )
    for event in EVENTS:
        lines.extend((
            r"\clearpage", rf"\section{{GRB {event}}}",
            r"\begin{figure}[H]\centering",
            rf"\includegraphics[width=0.96\textwidth,height=0.37\textheight,keepaspectratio]{{{event}_hydrogen_absorption_transmission.pdf}}",
            r"\caption{Observer-frame transmission in the three controlled variants. The mean IGM curve includes 39 Lyman-series transitions and Lyman-continuum opacity. The host curve uses the retained best-fit neutral-hydrogen column. Dashed and dotted lines locate the host-redshifted Ly-alpha line and Lyman limit.}", r"\end{figure}",
            r"\begin{figure}[H]\centering",
            rf"\includegraphics[width=0.96\textwidth,height=0.43\textheight,keepaspectratio]{{{event}_hydrogen_absorption_band_fit_difference.pdf}}",
            r"\caption{Per-band fit-statistic changes relative to the gas-off model. Negative values improve the likelihood. Separating IGM-only from IGM-plus-host-H-I identifies whether the deterministic foreground correction or the fitted host damping wing supplies the improvement.}", r"\end{figure}",
            r"\clearpage",
            r"\begin{figure}[H]\centering",
            rf"\includegraphics[width=0.96\textwidth,height=0.82\textheight,keepaspectratio]{{{event}_hydrogen_absorption_parameter_shifts.pdf}}",
            r"\caption{Changes in common fitted coordinates relative to the gas-off posterior, expressed in pooled 68-percent half-widths. Offsets are retained deliberately: movement of the historically affected offsets toward zero is a direct diagnostic that physical absorption is replacing calibration compensation.}", r"\end{figure}",
        ))
    lines.extend((
        r"\clearpage", r"\section{Interpretation and Next Decision}",
        (
            "A lower fit statistic is necessary but not sufficient to adopt a model. We should "
            "also require stable common-parameter posteriors, sensible movement of the affected "
            "filter offsets, and a host column that closes away from its broad prior limits. "
            "If host N_HI remains prior-dominated, the deterministic Inoue-only model is the "
            "better production choice unless spectroscopy supplies an external host-column prior."
        ),
        r"\section{References}",
        r"\begin{itemize}",
        r"\item Inoue, Shimizu, Iwata, and Tanaka (2014), MNRAS 442, 1805, \href{https://doi.org/10.1093/mnras/stu936}{doi:10.1093/mnras/stu936}.",
        r"\item Trotter (2011), UNC-Chapel Hill PhD thesis, Sections 3.4--3.5, \href{https://doi.org/10.17615/2gjp-g156}{doi:10.17615/2gjp-g156}.",
        r"\item Totani et al. (2006), PASJ 58, 485, \href{https://doi.org/10.1093/pasj/58.2.485}{doi:10.1093/pasj/58.2.485}.",
        r"\end{itemize}", r"\end{document}",
    ))
    return "\n\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--compile", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    payload = {"generated_utc": datetime.now(UTC).isoformat(), "events": {}}
    filter_audit = output / "filter_absorption_inventory.csv"
    if filter_audit.is_file():
        with filter_audit.open(newline="") as handle:
            payload["material_filter_audit"] = [
                row for row in csv.DictReader(handle)
                if row.get("igm_material_in_likelihood_audit", "").lower()
                == "true"
            ]

    for event in EVENTS:
        summaries, residuals, posteriors = {}, [], {}
        for variant in VARIANTS:
            summary, variant_rows, posterior = evaluate(event, variant)
            summaries[variant] = summary
            residuals.extend(variant_rows)
            posteriors[variant] = posterior
        shifts = posterior_shift_rows(posteriors)
        write_csv(output / f"{event}_band_residuals.csv", residuals)
        write_csv(output / f"{event}_posterior_shifts.csv", shifts)
        plot_fit_differences(event, residuals, output)
        plot_parameter_shifts(event, shifts, output)
        provenance = json.loads((
            ROOT / "run_configs" / "hydrogen_absorption" / event / "provenance.json"
        ).read_text())
        plot_transmission(event, provenance, summaries, output)
        payload["events"][event] = {
            "summaries": summaries,
            "provenance": provenance,
        }

    summary_path = output / "hydrogen_absorption_comparison.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n")
    tex_path = output / "GRB_hydrogen_absorption_comparison.tex"
    tex_path.write_text(build_tex(output, payload))
    if args.compile:
        latexmk = shutil.which("latexmk")
        if latexmk is None:
            raise SystemExit("latexmk is required to compile the report.")
        subprocess.run(
            [latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=output, check=True,
        )
        subprocess.run([latexmk, "-c", tex_path.name], cwd=output, check=True)
    print(f"summary={summary_path}")
    print(f"tex={tex_path}")
    if args.compile:
        print(f"pdf={tex_path.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
