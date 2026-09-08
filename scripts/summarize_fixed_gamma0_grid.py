#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import tomllib

# Keep the deceleration-time calculation dependency-free.
_SOL_CGS = 2.99792458e10


def deceleration_time_seconds(E_erg: float, n0_cgs: float, k: float, gamma0: float) -> float:
    r_decel = ((3.0 - k) * E_erg / (n0_cgs * 0.0188907 * gamma0**2.0)) ** (1.0 / (3.0 - k))
    return r_decel / gamma0**2.0 / (4.0 - k) / _SOL_CGS


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _pick_best_walker(payload: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_nmap: float | None = None
    for row in payload:
        if not isinstance(row, dict):
            continue
        nmap = _safe_float(row.get("nmap"))
        if nmap is None:
            continue
        if best is None or best_nmap is None or nmap < best_nmap:
            best = row
            best_nmap = nmap
    return best


def load_solution(run_dir: Path) -> tuple[dict[str, Any] | None, float | None, str, bool | None, str]:
    min_json = run_dir / "minimized" / "minimized.json"
    min_walkers = run_dir / "minimized" / "minimized_walkers.json"
    best_fit = run_dir / "best_fit.json"

    if min_json.exists():
        payload = _load_json(min_json)
        if isinstance(payload, dict):
            params = payload.get("params")
            nmap = _safe_float(payload.get("nmap"))
            success = payload.get("success")
            if not isinstance(success, bool):
                success = None
            message = str(payload.get("message", ""))
            if isinstance(params, dict):
                return params, nmap, "minimized.json", success, message

    if min_walkers.exists():
        payload = _load_json(min_walkers)
        if isinstance(payload, list):
            best = _pick_best_walker(payload)
            if isinstance(best, dict):
                params = best.get("params")
                nmap = _safe_float(best.get("nmap"))
                success = best.get("success")
                if not isinstance(success, bool):
                    success = None
                message = str(best.get("message", ""))
                if isinstance(params, dict):
                    return params, nmap, "minimized_walkers.json", success, message

    if best_fit.exists():
        payload = _load_json(best_fit)
        if isinstance(payload, dict):
            nmap = _safe_float(payload.get("nmap"))
            return payload, nmap, "best_fit.json", None, ""

    return None, None, "missing", None, ""


def load_t1_days(obs_csv: Path) -> float | None:
    if not obs_csv.exists():
        return None
    with obs_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return None
        candidates = ["time_days", "time", "t_days", "t", "days"]
        time_col = None
        lowered = {name.lower(): name for name in reader.fieldnames}
        for c in candidates:
            if c in lowered:
                time_col = lowered[c]
                break
        if time_col is None:
            time_col = reader.fieldnames[0]

        vals: list[float] = []
        for row in reader:
            val = _safe_float(row.get(time_col))
            if val is not None and val > 0.0:
                vals.append(val)
        return min(vals) if vals else None


def compute_tdec_days(model: dict[str, Any]) -> float | None:
    e52 = _safe_float(model.get("E52"))
    gamma0 = _safe_float(model.get("lf0"))
    n017 = _safe_float(model.get("n017"))
    k = _safe_float(model.get("k"))
    z = _safe_float(model.get("z"))
    if None in {e52, gamma0, n017, k, z}:
        return None

    # Dylan PL density convention: n(r)=n017*(r/1e17 cm)^(-k)
    n0 = n017 * (1.0e17 ** k)
    try:
        tdec_src_s = float(deceleration_time_seconds(e52 * 1.0e52, n0, k, gamma0))
    except Exception:
        return None
    return tdec_src_s * (1.0 + z) / 86400.0


def _iter_prior_entries(cfg: dict[str, Any]):
    for section in ("model", "extinction", "offsets", "host", "slop"):
        entries = cfg.get(section, [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            prior = entry.get("prior")
            if not isinstance(name, str) or not isinstance(prior, dict):
                continue
            yield section, entry


def detect_hit_bounds(params: dict[str, Any], cfg_path: Path, tol_frac: float = 1e-3) -> tuple[bool, list[str]]:
    if not cfg_path.exists():
        return False, []
    cfg = tomllib.loads(cfg_path.read_text())
    hits: list[str] = []

    for section, entry in _iter_prior_entries(cfg):
        name = entry["name"]
        prior = entry["prior"]
        lower = _safe_float(prior.get("lower"))
        upper = _safe_float(prior.get("upper"))
        if lower is None or upper is None or upper <= lower:
            continue
        section_values = params.get(section, {})
        if not isinstance(section_values, dict):
            continue
        value = _safe_float(section_values.get(name))
        if value is None:
            continue

        scale = str(entry.get("scale", "linear")).lower()
        if section == "model" and scale == "log":
            low_cmp = 10.0**lower
            up_cmp = 10.0**upper
        else:
            low_cmp = lower
            up_cmp = upper

        span = max(abs(up_cmp - low_cmp), 1e-30)
        tol = tol_frac * span
        if abs(value - low_cmp) <= tol or abs(value - up_cmp) <= tol:
            hits.append(f"{section}.{name}")

    return len(hits) > 0, hits


def summarize(
    *,
    event: str,
    gammas: list[int],
    run_tag: str,
    results_root: Path,
    config_dir: Path,
    obs_csv: Path,
    out_csv: Path,
) -> None:
    rows: list[dict[str, Any]] = []
    t1_days = load_t1_days(obs_csv)

    for gamma in gammas:
        run_name = f"{event}_g{gamma}_{run_tag}"
        run_dir = results_root / run_name
        params, nmap, src, success, message = load_solution(run_dir)

        row: dict[str, Any] = {
            "event": event,
            "gamma0_fixed": gamma,
            "run_dir": run_name,
            "solution_source": src,
            "best_nmap": nmap,
            "delta_nmap": None,
            "E52": None,
            "n017": None,
            "k": None,
            "eps_e": None,
            "eps_B": None,
            "p": None,
            "theta_c": None,
            "ebv_source_frame": None,
            "slop": None,
            "success": success,
            "hit_bounds": None,
            "hit_bounds_names": "",
            "t_dec_obs_days": None,
            "t1_obs_days": t1_days,
            "t1_over_tdec": None,
            "message": message,
        }

        if isinstance(params, dict):
            model = params.get("model", {})
            extinction = params.get("extinction", {})
            slop = params.get("slop", {})
            if isinstance(model, dict):
                row["E52"] = _safe_float(model.get("E52"))
                row["n017"] = _safe_float(model.get("n017"))
                row["k"] = _safe_float(model.get("k"))
                row["eps_e"] = _safe_float(model.get("eps_e"))
                row["eps_B"] = _safe_float(model.get("eps_b"))
                row["p"] = _safe_float(model.get("p"))
                row["theta_c"] = _safe_float(model.get("theta_c"))

            if isinstance(extinction, dict):
                row["ebv_source_frame"] = _safe_float(extinction.get("ebv_source_frame"))

            if isinstance(slop, dict):
                row["slop"] = _safe_float(slop.get("slop"))

            tdec_days = compute_tdec_days(model if isinstance(model, dict) else {})
            row["t_dec_obs_days"] = tdec_days
            if tdec_days and t1_days:
                row["t1_over_tdec"] = t1_days / tdec_days

            cfg_path = config_dir / f"{event}_g{gamma}.toml"
            hit, names = detect_hit_bounds(params, cfg_path)
            row["hit_bounds"] = hit
            row["hit_bounds_names"] = ";".join(names)

        rows.append(row)

    finite = [r["best_nmap"] for r in rows if _safe_float(r["best_nmap"]) is not None]
    best = min(finite) if finite else None
    if best is not None:
        for r in rows:
            nmap = _safe_float(r["best_nmap"])
            if nmap is not None:
                r["delta_nmap"] = nmap - best

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "event",
        "gamma0_fixed",
        "run_dir",
        "solution_source",
        "best_nmap",
        "delta_nmap",
        "E52",
        "n017",
        "k",
        "eps_e",
        "eps_B",
        "p",
        "theta_c",
        "ebv_source_frame",
        "slop",
        "success",
        "hit_bounds",
        "hit_bounds_names",
        "t_dec_obs_days",
        "t1_obs_days",
        "t1_over_tdec",
        "message",
    ]
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(out_csv)


def main() -> None:
    p = argparse.ArgumentParser(description="Summarize fixed-Gamma0 fit grid results into one CSV.")
    p.add_argument("--event", default="221009A")
    p.add_argument("--run-tag", required=True)
    p.add_argument(
        "--gammas",
        nargs="+",
        type=int,
        default=[50, 100, 150, 200, 250, 300, 400, 600, 800, 1000],
    )
    p.add_argument("--results-root", default="/Users/jkeohane/GRBs/VegasJetFit/jetfit/results")
    p.add_argument("--config-dir", required=True)
    p.add_argument("--obs-csv", default="/Users/jkeohane/GRBs/VegasJetFit/jetfit/resources/grbs/221009A/221009Aclean.csv")
    p.add_argument("--out-csv", required=True)
    args = p.parse_args()

    summarize(
        event=args.event,
        gammas=args.gammas,
        run_tag=args.run_tag,
        results_root=Path(args.results_root).expanduser().resolve(),
        config_dir=Path(args.config_dir).expanduser().resolve(),
        obs_csv=Path(args.obs_csv).expanduser().resolve(),
        out_csv=Path(args.out_csv).expanduser().resolve(),
    )


if __name__ == "__main__":
    main()
