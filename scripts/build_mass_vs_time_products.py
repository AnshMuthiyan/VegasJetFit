#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib
import json
import math
import re
import shutil
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


SEC_PER_DAY = 86400.0
C2_CGS = (2.99792458e10) ** 2
MP_CGS = 1.67262192e-24
REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from jetfit.models.jet_energy import resolve_e_iso52

# Supported model wrappers for mass-vs-time reconstruction.
MODEL_CLASS_MAP: dict[str, str] = {
    "powerlawVegasModel": "jetfit.models.powerlawVegas:powerlawVegasModel",
    "powerlawVegasDylanSpectrumModel": "jetfit.models.powerlawVegasDylanSpectrum:powerlawVegasDylanSpectrumModel",
    "VegasAfterglowModel": "jetfit.models.vegasafterglow:VegasAfterglowModel",
    "PowerlawJetVegasDylanSpectrumModel": "jetfit.models.powerlawJetVegasDylanSpectrum:PowerlawJetVegasDylanSpectrumModel",
    "PowerlawJetVegasAfterglowModel": "jetfit.models.powerlawJetVegasAfterglow:PowerlawJetVegasAfterglowModel",
    "BubbleVegasDylanSpectrumModel": "jetfit.models.bubbleVegasDylanSpectrum:BubbleVegasDylanSpectrumModel",
    "EmpiricalBubbleVegasModel": "jetfit.models.empiricalBubbleVegas:EmpiricalBubbleVegasModel",
    "EmpiricalBubbleVegasDylanSpectrumModel": (
        "jetfit.models.empiricalBubbleVegasDylanSpectrum:EmpiricalBubbleVegasDylanSpectrumModel"
    ),
}

TIME_COLUMN_CANDIDATES = ("time_days", "time", "t_days", "t", "days")
EVENT_RE = re.compile(r"^([0-9]{6}[A-Z]?)")


@dataclass
class RunSelection:
    event: str
    run_dir: Path
    run_name: str
    model_name: str
    nmap: float
    params: dict[str, Any]
    obs_csv: Path
    model_toml: Path


def _json_read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def extract_event_id(run_name: str) -> str | None:
    m = EVENT_RE.match(run_name)
    if not m:
        return None
    return m.group(1)


def load_best_params(run_dir: Path) -> tuple[dict[str, Any], float]:
    min_path = run_dir / "minimized" / "minimized.json"
    best_path = run_dir / "best_fit.json"

    if min_path.exists():
        payload = _json_read(min_path)
        params = payload.get("params", payload)
        nmap = payload.get("nmap", payload.get("nmap_val", math.inf))
        if isinstance(payload.get("inference"), dict):
            nmap = payload["inference"].get("nmap_val", nmap)
        return params, float(nmap) if np.isfinite(nmap) else math.inf

    if best_path.exists():
        payload = _json_read(best_path)
        nmap = payload.get("nmap", payload.get("nmap_val", math.inf))
        if isinstance(payload.get("inference"), dict):
            nmap = payload["inference"].get("nmap_val", nmap)
        return payload, float(nmap) if np.isfinite(nmap) else math.inf

    raise FileNotFoundError(f"No minimized/minimized.json or best_fit.json in {run_dir}")


def parse_model_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        return tomllib.load(f)


def _model_entries_by_name(model_toml: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for entry in model_toml.get("model", []):
        name = entry.get("name")
        if isinstance(name, str):
            out[name] = entry
    return out


def _is_fixed(entry: dict[str, Any] | None) -> bool:
    return bool(entry and "value" in entry)


def _fixed_value(entry: dict[str, Any] | None) -> float | None:
    if not entry or "value" not in entry:
        return None
    try:
        return float(entry["value"])
    except Exception:
        return None


def is_candidate_for_scope(model_toml: dict[str, Any], run_name: str, fit_scope: str) -> tuple[bool, str]:
    model_name = model_toml.get("name")
    if model_name not in MODEL_CLASS_MAP:
        return False, f"unsupported model wrapper: {model_name}"

    if fit_scope == "all_supported":
        # Keep production-like runs and skip obvious smoke/preflight artifacts.
        lowered = run_name.lower()
        if "preflight" in lowered or "speedtest" in lowered or "smoke" in lowered:
            return False, "excluded preflight/smoke/speedtest run"
        return True, "ok"

    if fit_scope != "wide_onaxis_tophat":
        return False, f"unknown fit scope: {fit_scope}"

    # wide_onaxis_tophat scope: exclude structured-jet/bubble families.
    lowered = run_name.lower()
    if "powerlawjet" in lowered or "structured" in lowered or "bubble" in lowered:
        return False, "excluded structured/bubble run"

    entries = _model_entries_by_name(model_toml)
    theta_c = _fixed_value(entries.get("theta_c"))
    theta_v = _fixed_value(entries.get("theta_v"))
    lf0_entry = entries.get("lf0")

    if theta_c is None or not np.isclose(theta_c, 1.0, atol=1e-12):
        return False, f"theta_c not fixed at 1.0 (got {theta_c})"
    if theta_v is None or not np.isclose(theta_v, 0.0, atol=1e-12):
        return False, f"theta_v not fixed at 0.0 (got {theta_v})"
    if _is_fixed(lf0_entry):
        return False, "lf0 fixed (likely gamma0 grid, not wide fit)"

    return True, "ok"


def detect_time_column(fieldnames: list[str]) -> str:
    lowered = {name.lower(): name for name in fieldnames}
    for candidate in TIME_COLUMN_CANDIDATES:
        if candidate in lowered:
            return lowered[candidate]
    return fieldnames[0]


def _fieldname_casefold(fieldnames: list[str], target: str) -> str | None:
    target_lower = target.lower()
    for name in fieldnames:
        if name.lower() == target_lower:
            return name
    return None


def _time_value_to_days(value: float, units: str | None) -> float:
    if units is None or not units.strip():
        return value

    normalized = units.strip().lower()
    if normalized in {"d", "day", "days"}:
        return value
    if normalized in {"s", "sec", "secs", "second", "seconds"}:
        return value / SEC_PER_DAY
    if normalized in {"ks", "kilosecond", "kiloseconds"}:
        return value * 1000.0 / SEC_PER_DAY
    if normalized in {"hr", "hrs", "hour", "hours", "h"}:
        return value / 24.0

    # Unknown units are treated as days to preserve the old behavior, but the
    # unit is recorded in metadata by the caller for traceability.
    return value


def read_obs_time_range(obs_csv: Path) -> tuple[float, float]:
    with obs_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"No header columns in {obs_csv}")
        fieldnames = list(reader.fieldnames)
        time_col = detect_time_column(fieldnames)
        units_col = _fieldname_casefold(fieldnames, "TimeUnits")
        include_col = _fieldname_casefold(fieldnames, "Include")
        vals: list[float] = []
        for row in reader:
            if include_col is not None:
                try:
                    include = float(row.get(include_col, "1"))
                except Exception:
                    include = 1.0
                if include <= 0:
                    continue

            try:
                t_raw = float(row.get(time_col, "nan"))
            except Exception:
                continue
            t = _time_value_to_days(t_raw, row.get(units_col) if units_col is not None else None)
            if np.isfinite(t) and t > 0:
                vals.append(t)
    if not vals:
        raise ValueError(f"No positive time values in {obs_csv}")
    return float(min(vals)), float(max(vals))


def load_model_class(model_name: str):
    target = MODEL_CLASS_MAP[model_name]
    mod_name, class_name = target.split(":")
    mod = importlib.import_module(mod_name)
    return getattr(mod, class_name)


def compute_tdec_crossing_days(t_days: np.ndarray, swept_mass_iso_g: np.ndarray, decel_mass_target_g: float) -> float:
    if not np.isfinite(decel_mass_target_g) or decel_mass_target_g <= 0:
        return math.nan
    if swept_mass_iso_g.size < 2:
        return math.nan

    hit = np.where(swept_mass_iso_g >= decel_mass_target_g)[0]
    if hit.size == 0:
        return math.nan
    idx = int(hit[0])
    if idx == 0:
        return float(t_days[0])

    t0 = float(t_days[idx - 1])
    t1 = float(t_days[idx])
    m0 = float(swept_mass_iso_g[idx - 1])
    m1 = float(swept_mass_iso_g[idx])
    if not (np.isfinite(t0) and np.isfinite(t1) and np.isfinite(m0) and np.isfinite(m1)):
        return float(t1)
    if t0 <= 0 or t1 <= 0 or m0 <= 0 or m1 <= 0 or m1 == m0:
        return float(t1)

    frac = (math.log(decel_mass_target_g) - math.log(m0)) / (math.log(m1) - math.log(m0))
    frac = float(np.clip(frac, 0.0, 1.0))
    return float(math.exp(math.log(t0) + frac * (math.log(t1) - math.log(t0))))


def compute_crossing_days_against_curve(
    t_days: np.ndarray,
    swept_mass_iso_g: np.ndarray,
    target_mass_g: np.ndarray,
) -> float:
    """Return first log-interpolated crossing where swept mass exceeds target curve."""
    if t_days.size < 2:
        return math.nan
    if not (t_days.size == swept_mass_iso_g.size == target_mass_g.size):
        return math.nan

    mask = (
        np.isfinite(t_days)
        & np.isfinite(swept_mass_iso_g)
        & np.isfinite(target_mass_g)
        & (t_days > 0)
        & (swept_mass_iso_g > 0)
        & (target_mass_g > 0)
    )
    t = t_days[mask]
    msw = swept_mass_iso_g[mask]
    mt = target_mass_g[mask]
    if t.size < 2:
        return math.nan

    delta = msw - mt
    hits = np.where(delta >= 0.0)[0]
    if hits.size == 0:
        return math.nan
    idx = int(hits[0])
    if idx == 0:
        return float(t[0])

    t0, t1 = float(t[idx - 1]), float(t[idx])
    m0, m1 = float(msw[idx - 1]), float(msw[idx])
    q0, q1 = float(mt[idx - 1]), float(mt[idx])
    d0, d1 = m0 - q0, m1 - q1
    if not (np.isfinite(d0) and np.isfinite(d1)) or d1 == d0:
        return float(t1)

    frac = -d0 / (d1 - d0)
    frac = float(np.clip(frac, 0.0, 1.0))
    if t0 <= 0 or t1 <= 0:
        return float(t1)
    return float(math.exp(math.log(t0) + frac * (math.log(t1) - math.log(t0))))


def build_plot_for_run(sel: RunSelection, out_dir: Path) -> dict[str, Any]:
    model_cls = load_model_class(sel.model_name)
    model = model_cls(**sel.params["model"])

    obs_tmin_days, obs_tmax_days = read_obs_time_range(sel.obs_csv)

    # Time span chosen to clearly show pre-data and post-data regimes.
    t_lo_days = max(min(obs_tmin_days, obs_tmax_days) / 30.0, 1e-8)
    t_hi_days = max(obs_tmax_days, obs_tmin_days) * 30.0
    if not np.isfinite(t_hi_days) or t_hi_days <= t_lo_days:
        t_hi_days = max(t_lo_days * 100.0, 1.0)

    details = model.vegas_model.details(float(t_lo_days * SEC_PER_DAY), float(t_hi_days * SEC_PER_DAY))

    t_obs_days = np.asarray(details.fwd.t_obs[0, 0, :], dtype=float) / SEC_PER_DAY
    swept_np = np.asarray(details.fwd.N_p[0, 0, :], dtype=float)
    gamma_dyn = np.asarray(details.fwd.Gamma[0, 0, :], dtype=float)
    swept_mass_iso_g = 4.0 * np.pi * MP_CGS * swept_np

    mask = (
        np.isfinite(t_obs_days)
        & np.isfinite(swept_mass_iso_g)
        & np.isfinite(gamma_dyn)
        & (t_obs_days > 0)
        & (swept_mass_iso_g > 0)
        & (gamma_dyn > 0)
    )
    t_obs_days = t_obs_days[mask]
    swept_mass_iso_g = swept_mass_iso_g[mask]
    gamma_dyn = gamma_dyn[mask]
    order = np.argsort(t_obs_days)
    t_obs_days = t_obs_days[order]
    swept_mass_iso_g = swept_mass_iso_g[order]
    gamma_dyn = gamma_dyn[order]

    model_params = sel.params["model"]
    e52 = resolve_e_iso52(
        E52=model_params.get("E52"),
        E_j_52=model_params.get("E_j_52"),
        jet_type="powerlaw" if "PowerlawJet" in sel.model_name else "tophat",
        theta_c=float(model_params["theta_c"]),
        k_e=model_params.get("k_e"),
    )
    gamma0 = float(model_params["lf0"])
    e_iso_erg = e52 * 1.0e52
    ejecta_mass_iso_g = e_iso_erg / (gamma0 * C2_CGS)
    decel_mass_target_g = ejecta_mass_iso_g / gamma0
    decel_mass_dyn_g = ejecta_mass_iso_g / gamma_dyn
    decel_mass_10x_dyn_g = 10.0 * ejecta_mass_iso_g / gamma_dyn
    t_dec_days = compute_crossing_days_against_curve(t_obs_days, swept_mass_iso_g, decel_mass_dyn_g)
    t_dec_10x_days = compute_crossing_days_against_curve(t_obs_days, swept_mass_iso_g, decel_mass_10x_dyn_g)
    t_ejecta_days = compute_tdec_crossing_days(t_obs_days, swept_mass_iso_g, ejecta_mass_iso_g)

    event_dir = out_dir / sel.event
    event_dir.mkdir(parents=True, exist_ok=True)

    stem = f"{sel.run_name}_mass_vs_time"
    csv_path = event_dir / f"{stem}.csv"
    png_path = event_dir / f"{stem}.png"
    meta_path = event_dir / f"{stem}.meta.json"

    arr = np.column_stack(
        [
            t_obs_days,
            swept_mass_iso_g,
            np.full_like(t_obs_days, ejecta_mass_iso_g),
            np.full_like(t_obs_days, decel_mass_target_g),
            gamma_dyn,
            decel_mass_dyn_g,
            decel_mass_10x_dyn_g,
        ]
    )
    np.savetxt(
        csv_path,
        arr,
        delimiter=",",
        header=(
            "t_obs_days,m_swept_iso_g,m_ejecta_iso_g,m_decel_target_iso_g,"
            "gamma_dynamic,m_ejecta_over_gamma_dynamic_g,m_10xejecta_over_gamma_dynamic_g"
        ),
        comments="",
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(t_obs_days, swept_mass_iso_g, lw=2.0, color="tab:blue", label=r"Swept-up mass $m_{\mathrm{sw}}$ (iso-eq)")
    ax.axhline(
        ejecta_mass_iso_g,
        lw=1.8,
        ls="--",
        color="tab:orange",
        label=r"Ejecta mass $m_j$ (iso-eq)",
    )
    ax.plot(
        t_obs_days,
        decel_mass_dyn_g,
        lw=1.4,
        ls=":",
        color="tab:red",
        label=r"Relativistic threshold $m_j/\Gamma(t)$",
    )
    ax.plot(
        t_obs_days,
        decel_mass_10x_dyn_g,
        lw=1.4,
        ls=":",
        color="tab:purple",
        label=r"Relativistic threshold $10\,m_j/\Gamma(t)$",
    )
    if np.isfinite(t_dec_days):
        ax.axvline(t_dec_days, lw=1.6, ls="-.", color="tab:red", label=r"$t_{\mathrm{dec}}$")
        ax.scatter(
            [t_dec_days],
            [np.interp(t_dec_days, t_obs_days, decel_mass_dyn_g)],
            s=54,
            color="tab:red",
            edgecolor="black",
            linewidth=0.6,
            zorder=5,
        )
    if np.isfinite(t_dec_10x_days):
        ax.axvline(
            t_dec_10x_days,
            lw=1.6,
            ls="-.",
            color="tab:purple",
            label=r"$t_{10\times\mathrm{dec}}$",
        )
        ax.scatter(
            [t_dec_10x_days],
            [np.interp(t_dec_10x_days, t_obs_days, decel_mass_10x_dyn_g)],
            s=54,
            color="tab:purple",
            edgecolor="black",
            linewidth=0.6,
            zorder=5,
        )
    if np.isfinite(t_ejecta_days):
        ax.axvline(t_ejecta_days, lw=1.6, ls="-.", color="tab:orange", label=r"$m_{\mathrm{sw}}=m_j$")
        ax.scatter(
            [t_ejecta_days],
            [ejecta_mass_iso_g],
            s=54,
            color="tab:orange",
            edgecolor="black",
            linewidth=0.6,
            zorder=5,
        )
    ax.axvspan(obs_tmin_days, obs_tmax_days, color="grey", alpha=0.17, label="Data time range")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Observer Time [days]")
    ax.set_ylabel("Mass [g] (isotropic-equivalent)")
    ax.set_title(f"GRB {sel.event}: Ejecta and swept-up mass")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=9, loc="best")
    top = ax.secondary_xaxis("top", functions=(lambda d: d * SEC_PER_DAY, lambda s: s / SEC_PER_DAY))
    top.set_xlabel("Observer Time [s]")
    fig.tight_layout()
    fig.savefig(png_path, dpi=220)
    plt.close(fig)

    meta = {
        "event": sel.event,
        "run_name": sel.run_name,
        "run_dir": str(sel.run_dir),
        "model_name": sel.model_name,
        "nmap": sel.nmap,
        "obs_tmin_days": obs_tmin_days,
        "obs_tmax_days": obs_tmax_days,
        "t_dec_days": t_dec_days,
        "t_dec_10x_days": t_dec_10x_days,
        "t_ejecta_equal_days": t_ejecta_days,
        "ejecta_mass_iso_g": ejecta_mass_iso_g,
        "decel_mass_target_iso_g": decel_mass_target_g,
        "csv_path": str(csv_path),
        "png_path": str(png_path),
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    return meta


def collect_candidates(results_root: Path, include_patterns: list[str], fit_scope: str) -> list[RunSelection]:
    candidates: list[RunSelection] = []
    for run_dir in sorted(results_root.iterdir()):
        if not run_dir.is_dir():
            continue
        run_name = run_dir.name
        if include_patterns and not any(run_dir.match(p) or run_name == p for p in include_patterns):
            # Also support Unix-glob style on basename.
            matched = False
            for pat in include_patterns:
                if Path(run_name).match(pat):
                    matched = True
                    break
            if not matched:
                continue

        model_toml = run_dir / "model.toml"
        obs_csv = run_dir / "obs.csv"
        if not (model_toml.exists() and obs_csv.exists()):
            continue

        try:
            model_cfg = parse_model_toml(model_toml)
            ok, _reason = is_candidate_for_scope(model_cfg, run_name, fit_scope)
            if not ok:
                continue
            params, nmap = load_best_params(run_dir)
        except Exception:
            continue

        if not isinstance(params, dict) or "model" not in params:
            continue

        event = extract_event_id(run_name)
        if event is None:
            continue
        model_name = str(model_cfg.get("name"))
        candidates.append(
            RunSelection(
                event=event,
                run_dir=run_dir,
                run_name=run_name,
                model_name=model_name,
                nmap=nmap,
                params=params,
                obs_csv=obs_csv,
                model_toml=model_toml,
            )
        )
    return candidates


def pick_best_per_event(candidates: list[RunSelection]) -> list[RunSelection]:
    by_event: dict[str, list[RunSelection]] = {}
    for c in candidates:
        by_event.setdefault(c.event, []).append(c)

    chosen: list[RunSelection] = []
    for event, rows in by_event.items():
        rows_sorted = sorted(
            rows,
            key=lambda r: (not np.isfinite(r.nmap), r.nmap if np.isfinite(r.nmap) else math.inf, r.run_name),
        )
        chosen.append(rows_sorted[0])
    return sorted(chosen, key=lambda r: r.event)


def maybe_sync_outputs(meta_rows: list[dict[str, Any]], out_dir: Path, sync_dir: Path) -> None:
    sync_dir.mkdir(parents=True, exist_ok=True)
    for meta in meta_rows:
        for key in ("csv_path", "png_path"):
            src = Path(meta[key])
            rel = src.relative_to(out_dir)
            dst = sync_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        meta_src = Path(meta["csv_path"]).with_suffix(".meta.json")
        rel_meta = meta_src.relative_to(out_dir)
        meta_dst = sync_dir / rel_meta
        meta_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(meta_src, meta_dst)

    manifest_src = out_dir / "mass_vs_time_index.csv"
    if manifest_src.exists():
        shutil.copy2(manifest_src, sync_dir / manifest_src.name)
    failures_src = out_dir / "mass_vs_time_failures.json"
    if failures_src.exists():
        shutil.copy2(failures_src, sync_dir / failures_src.name)


def main() -> None:
    p = argparse.ArgumentParser(
        description="Generate ejecta/swept-mass-vs-time products for wide on-axis top-hat best-fit GRB runs."
    )
    p.add_argument(
        "--results-root",
        default="/Users/jkeohane/GRBs/VegasJetFit/jetfit/results",
        help="Root directory containing run result folders.",
    )
    p.add_argument(
        "--out-dir",
        default="/Users/jkeohane/GRBs/VegasJetFit/analysis/data_products/mass_vs_time",
        help="Output directory for products and manifest.",
    )
    p.add_argument(
        "--include-pattern",
        action="append",
        default=[],
        help="Glob pattern(s) for run folder names (repeatable).",
    )
    p.add_argument(
        "--all-candidates",
        action="store_true",
        help="If set, generate products for all matching candidate runs instead of best-by-event only.",
    )
    p.add_argument(
        "--fit-scope",
        choices=("wide_onaxis_tophat", "all_supported"),
        default="wide_onaxis_tophat",
        help=(
            "Candidate scope: 'wide_onaxis_tophat' (legacy default) or "
            "'all_supported' (includes structured/bubble/Ansh-style runs for supported model wrappers)."
        ),
    )
    p.add_argument(
        "--sync-dir",
        default=None,
        help="Optional destination directory to copy generated products (e.g., shared drive data products folder).",
    )
    args = p.parse_args()

    results_root = Path(args.results_root).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    patterns = args.include_pattern or ["*"]
    candidates = collect_candidates(results_root, patterns, args.fit_scope)
    if not candidates:
        raise SystemExit(f"No matching candidates found for fit scope: {args.fit_scope}")

    selected = candidates if args.all_candidates else pick_best_per_event(candidates)

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for sel in selected:
        try:
            rows.append(build_plot_for_run(sel, out_dir))
        except Exception as exc:
            failures.append(
                {
                    "event": sel.event,
                    "run_name": sel.run_name,
                    "run_dir": str(sel.run_dir),
                    "model_name": sel.model_name,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    if not rows:
        raise SystemExit("No mass-vs-time products were generated successfully.")

    index_path = out_dir / "mass_vs_time_index.csv"
    with index_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "event",
                "run_name",
                "run_dir",
                "model_name",
                "nmap",
                "obs_tmin_days",
                "obs_tmax_days",
                "t_dec_days",
                "t_dec_10x_days",
                "t_ejecta_equal_days",
                "ejecta_mass_iso_g",
                "decel_mass_target_iso_g",
                "csv_path",
                "png_path",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    if args.sync_dir:
        sync_dir = Path(args.sync_dir).expanduser().resolve()
        maybe_sync_outputs(rows, out_dir, sync_dir)

    print(f"Wrote {len(rows)} mass_vs_time product set(s) to {out_dir}")
    print(f"Manifest: {index_path}")
    if failures:
        failures_path = out_dir / "mass_vs_time_failures.json"
        failures_path.write_text(json.dumps(failures, indent=2))
        print(f"Skipped {len(failures)} run(s); see {failures_path}")


if __name__ == "__main__":
    main()
