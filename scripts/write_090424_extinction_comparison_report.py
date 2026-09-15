#!/usr/bin/env python3
"""Write and compile the meeting-style 090424 extinction comparison report."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_STEM = "GRB_090424_CCM_vs_Trotter_extinction_comparison"


def tex(value: object) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in str(value))


def number(value: object, digits: int = 3) -> str:
    if value is None:
        return "not recorded"
    value = float(value)
    if not math.isfinite(value):
        return "not finite"
    return f"{value:.{digits}f}"


def signed(value: float, digits: int = 2) -> str:
    return f"{value:+.{digits}f}"


def tabular(headers: tuple[str, ...], rows: list[tuple[str, ...]], columns: str) -> str:
    lines = [
        r"\begingroup\small\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.05}",
        rf"\noindent\begin{{tabularx}}{{\textwidth}}{{{columns}}}",
        r"\toprule",
        " & ".join(headers) + r" \\",
        r"\midrule",
    ]
    lines.extend(" & ".join(row) + r" \\" for row in rows)
    lines.extend((r"\bottomrule", r"\end{tabularx}", r"\endgroup"))
    return "\n".join(lines)


def runtime_text(models: dict) -> tuple[str, list[tuple[str, ...]]]:
    ccm = models["CCM"].get("wall_clock_seconds")
    trotter = models["Trotter"].get("wall_clock_seconds")
    rows = [
        (
            "CCM",
            "Pauley404-02",
            number(models["CCM"].get("wall_clock_hours"), 2),
            number(ccm, 1),
        ),
        (
            "Trotter",
            "Pauley404-01",
            number(models["Trotter"].get("wall_clock_hours"), 2),
            number(trotter, 1),
        ),
    ]
    if ccm is None or trotter is None:
        return "A complete wall-clock record was not available for both fits.", rows
    faster = "CCM" if ccm < trotter else "Trotter"
    slower = "Trotter" if faster == "CCM" else "CCM"
    fast = min(ccm, trotter)
    slow = max(ccm, trotter)
    difference = slow - fast
    percent = 100.0 * difference / fast
    ratio = slow / fast
    sentence = (
        f"{faster} finished {difference / 3600.0:.2f} hours faster than {slower}. "
        f"The slower-to-faster wall-clock ratio was {ratio:.3f}, a {percent:.1f}% "
        "difference under simultaneous runs on identical M1 Max hosts."
    )
    return sentence, rows


def fit_interpretation(payload: dict) -> str:
    delta = payload["trotter_minus_ccm"]
    ll = float(delta["minus2_log_likelihood"])
    aic = float(delta["aic"])
    bic = float(delta["bic"])
    direction = "improves" if ll < 0.0 else "worsens"
    return (
        f"At the retained best points, Trotter {direction} minus twice the log "
        f"likelihood by {abs(ll):.2f} relative to CCM. The corresponding Trotter "
        f"minus CCM differences are {aic:+.2f} in AIC and {bic:+.2f} in BIC. "
        "Lower values are preferred, but AIC and BIC are approximate complexity "
        "diagnostics rather than Bayesian evidence."
    )


def band_rows(path: Path) -> list[tuple[str, ...]]:
    records = list(csv.DictReader(path.open()))
    by_model = {
        model: {row["band"]: row for row in records if row["model"] == model}
        for model in ("CCM", "Trotter")
    }
    rows = []
    for band in set(by_model["CCM"]) & set(by_model["Trotter"]):
        if band == "ALL":
            continue
        ccm = float(by_model["CCM"][band]["minus2_log_likelihood"])
        trotter = float(by_model["Trotter"][band]["minus2_log_likelihood"])
        rows.append((band, ccm, trotter, trotter - ccm))
    rows.sort(key=lambda row: abs(row[3]), reverse=True)
    return [
        (tex(band), number(ccm, 2), number(trotter, 2), signed(delta, 2))
        for band, ccm, trotter, delta in rows[:10]
    ]


def posterior_rows(path: Path) -> list[tuple[str, ...]]:
    records = list(csv.DictReader(path.open()))
    records.sort(key=lambda row: abs(float(row["standardized_shift"])), reverse=True)
    return [
        (
            tex(row["parameter"]),
            tex(row["scale"]),
            number(row["ccm_median"], 3),
            number(row["trotter_median"], 3),
            signed(float(row["standardized_shift"]), 2),
        )
        for row in records[:12]
    ]


def extinction_rows(models: dict) -> list[tuple[str, ...]]:
    rows = []
    for model in ("CCM", "Trotter"):
        for name, value in models[model].get("best_extinction", {}).items():
            if name == "ebv_milky_way" or str(name).startswith("delta_"):
                continue
            if isinstance(value, (int, float)):
                rows.append((model, tex(name), number(value, 4)))
    return rows


def build_document(output_dir: Path, payload: dict) -> str:
    models = payload["models"]
    runtime_summary, runtimes = runtime_text(models)
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    result_paths = {
        "CCM": ROOT / "jetfit/results/090424_ccm_bandpass_verified_5temp_100x800_v1",
        "Trotter": ROOT / "jetfit/results/090424_trotter_bandpass_verified_5temp_100x800_v1",
    }
    fit_rows = []
    for model in ("CCM", "Trotter"):
        summary = models[model]
        fit_rows.append(
            (
                model,
                str(summary["fitted_parameters"]),
                number(summary["minus2_log_likelihood"], 2),
                number(summary["aic"], 2),
                number(summary["bic"], 2),
            )
        )
    delta = payload["trotter_minus_ccm"]
    fit_rows.append(
        (
            r"\textbf{Trotter $-$ CCM}",
            "",
            signed(float(delta["minus2_log_likelihood"]), 2),
            signed(float(delta["aic"]), 2),
            signed(float(delta["bic"]), 2),
        )
    )

    lines = [
        r"\documentclass[10pt,letterpaper]{article}",
        r"\usepackage[margin=0.68in]{geometry}",
        r"\usepackage{graphicx}",
        r"\usepackage{booktabs}",
        r"\usepackage{tabularx}",
        r"\usepackage{array}",
        r"\usepackage{fancyhdr}",
        r"\usepackage{float}",
        r"\usepackage{xcolor}",
        r"\usepackage[colorlinks=true,linkcolor=blue,urlcolor=blue,citecolor=blue]{hyperref}",
        r"\setlength{\headheight}{24pt}",
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        r"\lhead{GRB 090424: CCM versus Trotter extinction}",
        r"\rhead{\scriptsize\texttt{5temp\_100x800, verified bandpasses}}",
        r"\cfoot{\thepage}",
        r"\begin{document}",
        r"\title{GRB 090424: Source-Frame Extinction Model Comparison}",
        r"\author{}",
        rf"\date{{Generated {tex(generated)}}}",
        r"\maketitle",
        r"\noindent\textbf{Code branch and commit:} \texttt{codex/trotter-extinction-production @ 63092ae}\\",
        r"\noindent\textbf{Comparison folder:}\\",
        rf"\noindent\scriptsize\path{{{output_dir}}}\normalsize",
        r"\begin{abstract}",
        (
            "This controlled experiment tests whether the Trotter/Reichart flexible "
            "source-frame dust prescription materially improves the GRB 090424 fit "
            "relative to the one-parameter Cardelli, Clayton, and Mathis (1989; CCM) "
            "source-frame model. Source-frame extinction here means attenuation by dust "
            "in the GRB host galaxy, evaluated at the host-rest-frame wavelength. It is "
            "distinct from the independently applied Milky Way foreground dust at "
            "redshift zero. Both fits use the same 607 observations, include all reviewed "
            "UV/OIR data, exclude the early X-ray flare, use the same afterglow model and "
            "Vegas grid, and integrate supported photometry through verified response "
            "curves."
        ),
        r"\end{abstract}",
        r"\section{Executive Comparison}",
        tex(fit_interpretation(payload)),
        "\n\n" + tex(runtime_summary),
        tabular(
            ("Model", "Free parameters", r"$-2\ln\mathcal{L}$", "AIC", "BIC"),
            fit_rows,
            r">{\raggedright\arraybackslash}Xrrrr",
        ),
        r"\section{Run Design and Wall-Clock Time}",
        (
            "The fits ran concurrently on identical 10-core Apple M1 Max Pauley "
            "workstations. Each used five temperatures, 100 walkers, 100 burn-in "
            "steps, 800 retained production steps, eight workers, and checkpoints "
            "every 50 steps. The different fitted dimensionality is intrinsic to the "
            "models: CCM has 23 fitted coordinates and Trotter has 33."
        ),
        tabular(
            ("Model", "Host", "Wall clock [h]", "Wall clock [s]"),
            runtimes,
            r">{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}Xrr",
        ),
        r"\section{Extinction Parameters at the Retained Best Point}",
        tabular(
            ("Model", "Parameter", "Value"),
            extinction_rows(models),
            r">{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}Xr",
        ),
        r"\clearpage",
        r"\section{Fit Quality by Observed Band}",
        r"Negative values in the final column favor Trotter; positive values favor CCM.",
        tabular(
            ("Band", r"CCM $-2\ln\mathcal{L}$", r"Trotter $-2\ln\mathcal{L}$", "Difference"),
            band_rows(output_dir / "090424_ccm_vs_trotter_verified_bandpass_residuals.csv"),
            r">{\raggedright\arraybackslash}Xrrr",
        ),
        r"\begin{figure}[H]",
        r"\centering",
        r"\includegraphics[width=0.94\textwidth,height=0.54\textheight,keepaspectratio]{090424_ccm_vs_trotter_band_fit_difference.pdf}",
        r"\caption{Per-band change in the fit statistic at the retained best point. Bars show Trotter minus CCM, so negative values identify wavelength bands for which the flexible Trotter extinction curve improves the likelihood. This decomposition localizes any global improvement and guards against interpreting compensation in unrelated bands as a dust-law success.}",
        r"\end{figure}",
        r"\clearpage",
        r"\section{Response of the Shared Posterior}",
        r"The table lists the largest shifts among parameters fitted in both models. The shift is the difference in posterior medians divided by the quadrature sum of the two 68\% half-widths.",
        tabular(
            ("Parameter", "Scale", "CCM median", "Trotter median", "Standardized shift"),
            posterior_rows(output_dir / "090424_ccm_vs_trotter_posterior_comparison.csv"),
            r">{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}Xrrr",
        ),
        r"\begin{figure}[H]",
        r"\centering",
        r"\includegraphics[width=0.94\textwidth,height=0.53\textheight,keepaspectratio]{090424_ccm_vs_trotter_common_parameter_shifts.pdf}",
        r"\caption{Shift in each common fitted parameter when the source-frame extinction prescription changes from CCM to Trotter. Dashed lines mark one pooled 68\% half-width. Large coherent shifts would indicate that dust-law flexibility is changing the inferred afterglow physics rather than only improving the ultraviolet residual structure.}",
        r"\end{figure}",
        r"\clearpage",
        r"\section{Provenance and Interpretation Limits}",
        r"\begin{itemize}",
        r"\item The observation files are byte-identical with SHA-256 {\scriptsize\texttt{cfa49b3a54e40cb96b7f614b4630880f9a7fe086b99b50781a96c965433d1ab5}}.",
        r"\item Supported UVOT and HST filters use verified photon-counting bandpass integration with 16 intrinsic-spectrum nodes and the full response grid for extinction.",
        r"\item Trotter replaces CCM's source-frame color excess with $A_V$, $c_2$, $c_4$, and correlated empirical dust-prior coordinates. The models therefore do not have equal complexity.",
        r"\item AIC and BIC are useful checks, but final model acceptance should also consider posterior stability, wavelength-local residuals, physical extinction curves, and convergence diagnostics.",
        r"\end{itemize}",
        r"\noindent\textbf{CCM result:}\\",
        rf"\scriptsize\path{{{result_paths['CCM']}}}\normalsize\\[4pt]",
        r"\noindent\textbf{Trotter result:}\\",
        rf"\scriptsize\path{{{result_paths['Trotter']}}}\normalsize",
        r"\end{document}",
    ]
    return "\n\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "reports/2026_09_14_090424_extinction_long_comparison",
    )
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    payload_path = output_dir / "090424_verified_bandpass_model_comparison.json"
    payload = json.loads(payload_path.read_text())

    tex_path = output_dir / f"{REPORT_STEM}.tex"
    tex_path.write_text(build_document(output_dir, payload))
    latexmk = shutil.which("latexmk")
    if latexmk is None:
        raise SystemExit("latexmk is required to compile the comparison PDF.")
    subprocess.run(
        [latexmk, "-pdf", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
        cwd=output_dir,
        check=True,
    )
    subprocess.run([latexmk, "-c", tex_path.name], cwd=output_dir, check=True)
    print(f"Wrote {tex_path}")
    print(f"Wrote {output_dir / (REPORT_STEM + '.pdf')}")


if __name__ == "__main__":
    main()
