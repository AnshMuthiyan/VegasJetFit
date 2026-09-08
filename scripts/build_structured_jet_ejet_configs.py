#!/usr/bin/env python3
"""Build structured-jet TOMLs using core-matched physical parameters.

The generated configs sample the two-sided core energy ``E_j_core_52`` and the
solid-angle-averaged core Lorentz factor ``Gamma_0_core_avg``.  The
VegasAfterglow wrappers convert these to the on-axis ``E52`` and ``Gamma0``
required by the numerical engine using the fitted angular profiles.

This is a kinetic afterglow energy, not the prompt gamma-ray energy.  The
standard prior covers ``10^48 <= E_j,core,kin <= 10^54 erg``, equivalently
``-4 <= log10(E_j,core,kin,52) <= 2``.  The standard core-average Lorentz-factor
prior is ``50 <= <Gamma_0>_core <= 100000``.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Any

from build_thesis_reproduction_model_toml import _load_toml, _write_toml
from thesis_reproduction_data import normalize_event_name

FINAL_FINAL_RESOLUTIONS = {
    "vegas_resolution_phi": 0.15,
    "vegas_resolution_theta": 0.5,
    "vegas_resolution_t": 15.0,
}


def _entry_name(entry: dict[str, Any]) -> str | None:
    name = entry.get("name")
    return str(name) if name is not None else None


def _ensure_221009a_mw_rv_prior(config: dict[str, Any], event: str) -> None:
    """Fit Milky Way R_V for 221009A, where foreground extinction is large."""
    if normalize_event_name(event) != "221009A":
        return

    extinction = config.get("extinction", [])
    if not isinstance(extinction, list):
        raise ValueError("221009A config has no extinction entry list")

    rv_prior = {
        "name": "rv_milky_way",
        "scale": "log",
        "prior": {"type": "milkywayrv"},
    }

    cleaned = [entry for entry in extinction if _entry_name(entry) != "rv_milky_way"]
    ebv_idx = next(
        (idx for idx, entry in enumerate(cleaned) if _entry_name(entry) == "ebv_milky_way"),
        len(cleaned),
    )
    cleaned.insert(ebv_idx, rv_prior)
    config["extinction"] = cleaned


def _ensure_final_final_resolutions(config: dict[str, Any], resolutions: dict[str, float]) -> None:
    """Set explicit VegasAfterglow resolution controls for a campaign member."""
    entries = config.get("model")
    if not isinstance(entries, list):
        raise ValueError("config has no model entry list")

    # Replace rather than append so source-specific resolution settings cannot
    # silently make members of a single final-final campaign incomparable.
    config["model"] = [
        entry for entry in entries if _entry_name(entry) not in resolutions
    ] + [
        {"name": name, "scale": "linear", "value": value}
        for name, value in resolutions.items()
    ]


def _replace_core_physical_entries(
    entries: list[dict[str, Any]],
    *,
    lower: float,
    upper: float,
    log_gamma0_lower: float,
    log_gamma0_upper: float,
    initial_guess: float | None,
    initial_sigma: float | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    out: list[dict[str, Any]] = []
    audit: dict[str, Any] = {
        "old_name": "",
        "old_scale": "",
        "old_lower": "",
        "old_upper": "",
        "new_name": "E_j_core_52",
        "new_scale": "log",
        "new_lower": lower,
        "new_upper": upper,
        "new_initial_guess": initial_guess if initial_guess is not None else "",
        "new_initial_sigma": initial_sigma if initial_sigma is not None else "",
    }
    replaced = False

    for entry in entries:
        name = _entry_name(entry)
        if name in {"lf0", "Gamma_0_core_avg"}:
            continue
        if name not in {"E52", "E_j_52", "E_j_core_52"}:
            out.append(entry)
            continue

        prior = entry.get("prior", {}) if isinstance(entry.get("prior"), dict) else {}
        audit.update(
            {
                "old_name": name,
                "old_scale": entry.get("scale", ""),
                "old_lower": prior.get("lower", ""),
                "old_upper": prior.get("upper", ""),
            }
        )
        new_prior: dict[str, Any] = {
            "type": "uniform",
            "lower": float(lower),
            "upper": float(upper),
        }
        if initial_guess is not None:
            new_prior["initial_guess"] = float(initial_guess)
        if initial_sigma is not None:
            new_prior["initial_sigma"] = float(initial_sigma)
        if not replaced:
            out.append({"name": "E_j_core_52", "scale": "log", "prior": new_prior})
            replaced = True

    if not replaced:
        new_prior = {"type": "uniform", "lower": float(lower), "upper": float(upper)}
        if initial_guess is not None:
            new_prior["initial_guess"] = float(initial_guess)
        if initial_sigma is not None:
            new_prior["initial_sigma"] = float(initial_sigma)
        out.insert(0, {"name": "E_j_core_52", "scale": "log", "prior": new_prior})

    gamma_prior = {
        "type": "uniform",
        "lower": float(log_gamma0_lower),
        "upper": float(log_gamma0_upper),
    }
    out.insert(
        1,
        {
            "name": "Gamma_0_core_avg",
            "scale": "log",
            "prior": gamma_prior,
        },
    )

    return out, audit


def build_config(
    source: dict[str, Any],
    *,
    event: str,
    lower: float,
    upper: float,
    log_gamma0_lower: float,
    log_gamma0_upper: float,
    log_density_lower: float,
    log_density_upper: float,
    log_epse_lower: float,
    log_epse_upper: float,
    log_epsb_lower: float,
    log_epsb_upper: float,
    p_lower: float,
    p_upper: float,
    s_lower: float,
    s_upper: float,
    s_initial_guess: float,
    s_initial_sigma: float,
    theta_c_lower: float,
    theta_c_upper: float,
    theta_v_lower: float,
    theta_v_upper: float,
    ebv_upper: float,
    resolutions: dict[str, float],
    initial_guess: float | None,
    initial_sigma: float | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    config = dict(source)
    entries = source.get("model", [])
    if not isinstance(entries, list):
        raise ValueError("source config has no model entry list")
    new_entries, audit = _replace_core_physical_entries(
        entries,
        lower=lower,
        upper=upper,
        log_gamma0_lower=log_gamma0_lower,
        log_gamma0_upper=log_gamma0_upper,
        initial_guess=initial_guess,
        initial_sigma=initial_sigma,
    )
    for entry in new_entries:
        name = _entry_name(entry)
        if name == "s":
            entry["scale"] = "linear"
            entry.pop("value", None)
            entry["prior"] = {
                "type": "uniform",
                "lower": float(s_lower),
                "upper": float(s_upper),
                "initial_guess": float(s_initial_guess),
                "initial_sigma": float(s_initial_sigma),
            }
            continue
        prior = entry.get("prior")
        if not isinstance(prior, dict):
            continue
        if name in {"n017", "nt"}:
            prior["lower"] = float(log_density_lower)
            prior["upper"] = float(log_density_upper)
        elif name == "eps_e":
            prior["lower"] = float(log_epse_lower)
            prior["upper"] = float(log_epse_upper)
        elif name in {"eps_b", "eps_B"}:
            prior["lower"] = float(log_epsb_lower)
            prior["upper"] = float(log_epsb_upper)
        elif name == "p":
            prior["lower"] = float(p_lower)
            prior["upper"] = float(p_upper)
        elif name == "theta_c":
            prior["lower"] = float(theta_c_lower)
            prior["upper"] = float(theta_c_upper)
        elif name == "theta_v":
            prior["lower"] = float(theta_v_lower)
            prior["upper"] = float(theta_v_upper)
    config["model"] = new_entries
    _ensure_final_final_resolutions(config, resolutions)
    for entry in config.get("extinction", []):
        if _entry_name(entry) == "ebv_source_frame":
            prior = entry.get("prior")
            if not isinstance(prior, dict):
                raise ValueError("ebv_source_frame must be a fitted prior")
            prior["lower"] = 0.0
            prior["upper"] = float(ebv_upper)
    _ensure_221009a_mw_rv_prior(config, event)
    if normalize_event_name(event) == "221009A":
        rv_entry = next(
            (entry for entry in config.get("extinction", []) if _entry_name(entry) == "rv_milky_way"),
            None,
        )
        if not isinstance(rv_entry, dict) or rv_entry.get("prior", {}).get("type") != "milkywayrv":
            raise ValueError("221009A must use the dedicated milkywayrv prior for rv_milky_way.")
    return config, audit


def _float_or_none(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    out = float(value)
    return out if math.isfinite(out) else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-config-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--events", nargs="+", required=True)
    parser.add_argument(
        "--log-ejet-lower",
        type=float,
        default=-4.0,
        help="Lower log10(E_j_core_52) prior. Default -4 corresponds to 10^48 erg.",
    )
    parser.add_argument(
        "--log-ejet-upper",
        type=float,
        default=2.0,
        help="Upper log10(E_j_core_52) prior. Default 2 corresponds to 10^54 erg.",
    )
    parser.add_argument(
        "--log-gamma0-lower",
        type=float,
        default=math.log10(50.0),
        help="Lower log10(<Gamma_0>_core) prior. Default corresponds to 50.",
    )
    parser.add_argument(
        "--log-gamma0-upper",
        type=float,
        default=math.log10(100000.0),
        help="Upper log10(<Gamma_0>_core) prior. Default corresponds to 100000.",
    )
    parser.add_argument(
        "--log-epsb-lower",
        type=float,
        default=-10.0,
        help="Lower log10(epsilon_B) prior for eps_b/eps_B in generated configs.",
    )
    parser.add_argument(
        "--log-epsb-upper",
        type=float,
        default=0.0,
        help="Upper log10(epsilon_B) prior for eps_b/eps_B in generated configs.",
    )
    parser.add_argument(
        "--log-density-lower",
        type=float,
        default=-6.0,
        help="Lower log10 density-normalization prior.",
    )
    parser.add_argument("--log-density-upper", type=float, default=10.0)
    parser.add_argument("--log-epse-lower", type=float, default=-6.0)
    parser.add_argument("--log-epse-upper", type=float, default=0.0)
    parser.add_argument("--p-lower", type=float, default=2.0)
    parser.add_argument("--p-upper", type=float, default=3.5)
    parser.add_argument("--s-lower", type=float, default=0.1)
    parser.add_argument("--s-upper", type=float, default=10.0)
    parser.add_argument("--s-initial-guess", type=float, default=4.0)
    parser.add_argument("--s-initial-sigma", type=float, default=0.4)
    parser.add_argument("--theta-c-lower", type=float, default=-3.0)
    parser.add_argument("--theta-c-upper", type=float, default=0.0)
    parser.add_argument("--theta-v-lower", type=float, default=-4.0)
    parser.add_argument("--theta-v-upper", type=float, default=0.0)
    parser.add_argument("--vegas-resolution-phi", type=float, default=FINAL_FINAL_RESOLUTIONS["vegas_resolution_phi"])
    parser.add_argument("--vegas-resolution-theta", type=float, default=FINAL_FINAL_RESOLUTIONS["vegas_resolution_theta"])
    parser.add_argument("--vegas-resolution-t", type=float, default=FINAL_FINAL_RESOLUTIONS["vegas_resolution_t"])
    parser.add_argument(
        "--ebv-upper",
        type=float,
        default=1.0,
        help="Upper source-frame E(B-V) prior in magnitudes.",
    )
    parser.add_argument(
        "--note",
        default=(
            "E_j_core_52 is two-sided core kinetic afterglow energy; "
            "final-final defaults use the consolidated expanded prior policy."
        ),
        help="Human-readable note copied into the audit CSV.",
    )
    parser.add_argument("--initial-guess", help="Optional log10(E_j_core_52) initial guess for all events.")
    parser.add_argument("--initial-sigma", help="Optional log10(E_j_core_52) initial sigma for all events.")
    parser.add_argument("--audit-csv", type=Path)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    initial_guess = _float_or_none(args.initial_guess)
    initial_sigma = _float_or_none(args.initial_sigma)
    resolutions = {
        "vegas_resolution_phi": args.vegas_resolution_phi,
        "vegas_resolution_theta": args.vegas_resolution_theta,
        "vegas_resolution_t": args.vegas_resolution_t,
    }
    if any(value <= 0 for value in resolutions.values()):
        raise SystemExit("VegasAfterglow resolution controls must be positive.")
    rows: list[dict[str, Any]] = []

    for raw_event in args.events:
        event = normalize_event_name(raw_event)
        source_path = args.source_config_dir / f"{event}.toml"
        if not source_path.exists():
            raise SystemExit(f"Missing source config for {event}: {source_path}")

        config, audit = build_config(
            _load_toml(source_path),
            event=event,
            lower=args.log_ejet_lower,
            upper=args.log_ejet_upper,
            log_gamma0_lower=args.log_gamma0_lower,
            log_gamma0_upper=args.log_gamma0_upper,
            log_density_lower=args.log_density_lower,
            log_density_upper=args.log_density_upper,
            log_epse_lower=args.log_epse_lower,
            log_epse_upper=args.log_epse_upper,
            log_epsb_lower=args.log_epsb_lower,
            log_epsb_upper=args.log_epsb_upper,
            p_lower=args.p_lower,
            p_upper=args.p_upper,
            s_lower=args.s_lower,
            s_upper=args.s_upper,
            s_initial_guess=args.s_initial_guess,
            s_initial_sigma=args.s_initial_sigma,
            theta_c_lower=args.theta_c_lower,
            theta_c_upper=args.theta_c_upper,
            theta_v_lower=args.theta_v_lower,
            theta_v_upper=args.theta_v_upper,
            ebv_upper=args.ebv_upper,
            resolutions=resolutions,
            initial_guess=initial_guess,
            initial_sigma=initial_sigma,
        )
        output_path = args.output_dir / f"{event}.toml"
        _write_toml(output_path, config)
        print(f"WROTE {event}: {output_path}")

        audit["event"] = event
        audit["source_config"] = str(source_path)
        audit["output_config"] = str(output_path)
        audit["note"] = args.note
        rows.append(audit)

    if args.audit_csv is not None:
        args.audit_csv.parent.mkdir(parents=True, exist_ok=True)
        fields = [
            "event",
            "source_config",
            "output_config",
            "old_name",
            "old_scale",
            "old_lower",
            "old_upper",
            "new_name",
            "new_scale",
            "new_lower",
            "new_upper",
            "new_initial_guess",
            "new_initial_sigma",
            "note",
        ]
        with args.audit_csv.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"AUDIT {args.audit_csv}")


if __name__ == "__main__":
    main()
