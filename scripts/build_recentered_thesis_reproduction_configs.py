#!/usr/bin/env python3
"""Build next-round thesis reproduction configs recentered on prior run results."""

from __future__ import annotations

import argparse
import csv
import copy
import math
from pathlib import Path
from typing import Any

from build_thesis_reproduction_model_toml import (
    LOG_UPPER_BOUNDS,
    MIN_SIGMA_FALLBACKS,
    PL_PARAM_SPECS,
    POSITIVE_LINEAR_LOWER_BOUNDS,
    SBPL_PARAM_SPECS,
    _fixed_entry,
    _load_toml,
    _resolve_fixed_from_source,
    _source_section_map,
    _write_toml,
)
from thesis_reproduction_data import THESIS, normalize_event_name


SECTION_ORDER = ("model", "extinction", "offsets", "host", "slop")
RESULT_SECTION_ORDER = ("model", "extinction", "host", "offsets", "slop")


def flatten_minimized_params(payload: dict[str, Any]) -> dict[str, float]:
    flat: dict[str, float] = {}
    params = payload.get("params", {})
    if not isinstance(params, dict):
        return flat

    for section in RESULT_SECTION_ORDER:
        values = params.get(section, {})
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            if isinstance(value, (int, float)):
                flat[key] = float(value)

    return flat


def load_minimized_params(path: Path) -> dict[str, float]:
    payload = _load_toml(path) if path.suffix == ".toml" else None
    if payload is not None:
        raise ValueError(f"Unexpected TOML minimized payload: {path}")
    import json

    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict in minimized JSON: {path}")
    return flatten_minimized_params(data)


def load_summary_stats(path: Path) -> dict[str, dict[str, float]]:
    stats: dict[str, dict[str, float]] = {}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        first_field = reader.fieldnames[0] if reader.fieldnames else ""
        for row in reader:
            raw_name = row.get("") or row.get(first_field) or ""
            name = raw_name.strip()
            if not name:
                continue
            parsed: dict[str, float] = {}
            for key, value in row.items():
                if key in ("", first_field) or value in (None, ""):
                    continue
                try:
                    parsed[key] = float(value)
                except ValueError:
                    continue
            stats[name] = parsed
    return stats


def choose_mapping_value(mapping: dict[str, Any], *names: str) -> tuple[Any | None, str | None]:
    for name in names:
        if not name:
            continue
        if name in mapping:
            return mapping[name], name
    return None, None


def center_in_fit_space(
    *,
    linear_center: float | None,
    summary_stats: dict[str, float] | None,
    scale: str,
    param_name: str,
) -> float:
    if scale == "log":
        if linear_center is not None and linear_center > 0:
            return float(math.log10(linear_center))
        if summary_stats is not None and "mean" in summary_stats and math.isfinite(summary_stats["mean"]):
            return float(summary_stats["mean"])
        raise ValueError(f"Cannot derive log-space center for {param_name}")

    if linear_center is not None and math.isfinite(linear_center):
        return float(linear_center)
    if summary_stats is not None and "mean" in summary_stats and math.isfinite(summary_stats["mean"]):
        return float(summary_stats["mean"])
    raise ValueError(f"Cannot derive linear-space center for {param_name}")


def sigma_from_summary(
    *,
    summary_stats: dict[str, float] | None,
    source_entry: dict[str, Any] | None,
    param_name: str,
) -> float:
    if summary_stats is not None:
        sd = summary_stats.get("sd")
        if isinstance(sd, float) and math.isfinite(sd) and sd > 0:
            return float(sd)

    if source_entry is not None:
        prior = source_entry.get("prior")
        if isinstance(prior, dict):
            initial_sigma = prior.get("initial_sigma")
            if isinstance(initial_sigma, (int, float)) and math.isfinite(initial_sigma) and initial_sigma > 0:
                return float(initial_sigma)

    return float(MIN_SIGMA_FALLBACKS.get(param_name, 0.05))


def apply_physical_bounds(*, lower: float, upper: float, param_name: str) -> tuple[float, float]:
    lower_bound = POSITIVE_LINEAR_LOWER_BOUNDS.get(param_name)
    if lower_bound is not None:
        lower = max(lower, lower_bound)

    upper_bound = LOG_UPPER_BOUNDS.get(param_name)
    if upper_bound is not None:
        upper = min(upper, upper_bound)

    return lower, upper


def build_recentered_prior(
    *,
    center: float,
    sigma: float,
    sigma_multiple: float,
    param_name: str,
) -> dict[str, float | str]:
    width = max(float(sigma), 1e-3)
    lower = float(center) - sigma_multiple * width
    upper = float(center) + sigma_multiple * width
    lower, upper = apply_physical_bounds(lower=lower, upper=upper, param_name=param_name)

    if lower >= upper:
        lower = float(center) - width
        upper = float(center) + width
        lower, upper = apply_physical_bounds(lower=lower, upper=upper, param_name=param_name)
        if lower >= upper:
            upper = lower + max(width, 1e-3)

    return {
        "type": "uniform",
        "lower": float(lower),
        "upper": float(upper),
        "initial_guess": float(center),
        "initial_sigma": float(width),
    }


def recentered_entry(
    *,
    entry_name: str,
    scale: str,
    summary_names: tuple[str, ...],
    center_names: tuple[str, ...],
    source_entry: dict[str, Any] | None,
    minimized_flat: dict[str, float],
    summary_stats: dict[str, dict[str, float]],
    sigma_multiple: float,
    param_name: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    linear_center, center_key = choose_mapping_value(minimized_flat, *center_names)
    stats_row, stats_key = choose_mapping_value(summary_stats, *summary_names)
    if linear_center is None and stats_row is None:
        raise ValueError(f"Missing prior recentering data for {entry_name}")

    fit_center = center_in_fit_space(
        linear_center=linear_center if isinstance(linear_center, (int, float)) else None,
        summary_stats=stats_row if isinstance(stats_row, dict) else None,
        scale=scale,
        param_name=param_name,
    )
    sigma = sigma_from_summary(
        summary_stats=stats_row if isinstance(stats_row, dict) else None,
        source_entry=source_entry,
        param_name=param_name,
    )
    prior = build_recentered_prior(
        center=fit_center,
        sigma=sigma,
        sigma_multiple=sigma_multiple,
        param_name=param_name,
    )

    audit = {
        "entry_name": entry_name,
        "scale": scale,
        "center_source_key": center_key or "",
        "summary_source_key": stats_key or "",
        "center_fit": fit_center,
        "center_linear": linear_center if linear_center is not None else "",
        "sigma": sigma,
        "lower": prior["lower"],
        "upper": prior["upper"],
    }
    return {"name": entry_name, "scale": scale, "prior": prior}, audit


def copy_non_model_sections(
    source: dict[str, Any],
    *,
    minimized_flat: dict[str, float],
    summary_stats: dict[str, dict[str, float]],
    sigma_multiple: float,
    audit_rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}

    for section in ("offsets", "host"):
        entries = source.get(section, [])
        if isinstance(entries, list) and entries:
            out[section] = copy.deepcopy(entries)

    extinction_entries = source.get("extinction", [])
    if isinstance(extinction_entries, list) and extinction_entries:
        new_extinction: list[dict[str, Any]] = []
        for entry in extinction_entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if name == "ebv_source_frame":
                recentered, audit = recentered_entry(
                    entry_name="ebv_source_frame",
                    scale="linear",
                    summary_names=("ebv_source_frame",),
                    center_names=("ebv_source_frame",),
                    source_entry=entry,
                    minimized_flat=minimized_flat,
                    summary_stats=summary_stats,
                    sigma_multiple=sigma_multiple,
                    param_name="ebv_source_frame",
                )
                audit["section"] = "extinction"
                new_extinction.append(recentered)
                audit_rows.append(audit)
            else:
                new_extinction.append(copy.deepcopy(entry))
        if new_extinction:
            out["extinction"] = new_extinction

    slop_entries = source.get("slop", [])
    if isinstance(slop_entries, list) and slop_entries:
        new_slop: list[dict[str, Any]] = []
        for entry in slop_entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if name == "slop":
                recentered, audit = recentered_entry(
                    entry_name="slop",
                    scale="linear",
                    summary_names=("slop",),
                    center_names=("slop",),
                    source_entry=entry,
                    minimized_flat=minimized_flat,
                    summary_stats=summary_stats,
                    sigma_multiple=sigma_multiple,
                    param_name="slop",
                )
                audit["section"] = "slop"
                new_slop.append(recentered)
                audit_rows.append(audit)
            else:
                new_slop.append(copy.deepcopy(entry))
        if new_slop:
            out["slop"] = new_slop

    return out


def build_config_from_results(
    source: dict[str, Any],
    *,
    event: str,
    minimized_flat: dict[str, float],
    summary_stats: dict[str, dict[str, float]],
    sigma_multiple: float,
    theta_c: float,
    theta_v: float,
    pl_model_name: str,
    sbpl_model_name: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    thesis = THESIS[event]
    kind = thesis["model"]
    source_model = _source_section_map(source, "model")
    audit_rows: list[dict[str, Any]] = []

    if kind == "PL":
        config: dict[str, Any] = {"name": pl_model_name}
        specs = PL_PARAM_SPECS
    elif kind == "SBPL":
        config = {"name": sbpl_model_name}
        specs = SBPL_PARAM_SPECS
    else:
        raise ValueError(f"Unsupported thesis model kind for {event}: {kind}")

    model_entries: list[dict[str, Any]] = []
    for thesis_key, _, output_name, scale in specs:
        summary_names = (output_name, thesis_key)
        center_names = (output_name, thesis_key)
        source_lookup = output_name
        if output_name == "eps_B":
            summary_names = ("eps_B", "eps_b")
            center_names = ("eps_B", "eps_b")
            source_lookup = "eps_b"
        elif output_name == "k1":
            summary_names = ("k1", "kpre")
            center_names = ("k1", "kpre")
        elif output_name == "k2":
            summary_names = ("k2", "kpost")
            center_names = ("k2", "kpost")

        source_entry = source_model.get(source_lookup)
        recentered, audit = recentered_entry(
            entry_name=output_name,
            scale=scale,
            summary_names=summary_names,
            center_names=center_names,
            source_entry=source_entry,
            minimized_flat=minimized_flat,
            summary_stats=summary_stats,
            sigma_multiple=sigma_multiple,
            param_name=output_name,
        )
        audit["section"] = "model"
        model_entries.append(recentered)
        audit_rows.append(audit)

    if kind == "PL":
        model_entries.append(_fixed_entry("hmf", "linear", 0.7))
        model_entries.append(_fixed_entry("z", "linear", _resolve_fixed_from_source(source_model, "z")))
        model_entries.append(_fixed_entry("dl28", "linear", _resolve_fixed_from_source(source_model, "dl28")))
    else:
        model_entries.append(_fixed_entry("z", "linear", _resolve_fixed_from_source(source_model, "z")))
        model_entries.append(_fixed_entry("dl28", "linear", _resolve_fixed_from_source(source_model, "dl28")))

    model_entries.append(_fixed_entry("theta_c", "linear", theta_c))
    model_entries.append(_fixed_entry("theta_v", "linear", theta_v))
    config["model"] = model_entries
    config.update(
        copy_non_model_sections(
            source,
            minimized_flat=minimized_flat,
            summary_stats=summary_stats,
            sigma_multiple=sigma_multiple,
            audit_rows=audit_rows,
        )
    )

    return config, audit_rows


def results_name_for(event: str, run_tag: str, template: str) -> str:
    out = template.replace("{event}", event)
    out = out.replace("{run_tag}", run_tag)
    return out


def resolve_results_dir(
    *,
    event: str,
    results_name: str,
    results_root: Path,
    drive_root: Path | None,
    owner_subdir: str,
) -> Path:
    local_dir = results_root / results_name
    local_required = (
        local_dir / "model.toml",
        local_dir / "summary.csv",
        local_dir / "minimized" / "minimized.json",
    )
    if all(path.exists() for path in local_required):
        return local_dir

    if drive_root is not None:
        share_dir = drive_root / event / owner_subdir / results_name
        share_required = (
            share_dir / "model.toml",
            share_dir / "summary.csv",
            share_dir / "minimized" / "minimized.json",
        )
        if all(path.exists() for path in share_required):
            return share_dir

    return local_dir


def write_audit_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "event",
        "section",
        "entry_name",
        "scale",
        "center_source_key",
        "summary_source_key",
        "center_fit",
        "center_linear",
        "sigma",
        "lower",
        "upper",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-tag", required=True, help="Prior run tag providing minimized centers and summary widths.")
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "jetfit" / "results",
        help="Root results directory containing prior run outputs.",
    )
    parser.add_argument(
        "--drive-root",
        type=Path,
        help="Optional synced share root used as a fallback source of prior run outputs.",
    )
    parser.add_argument(
        "--owner-subdir",
        default="jkeohane",
        help="Owner subdirectory name under the synced share root.",
    )
    parser.add_argument(
        "--results-name-template",
        default="{event}_thesis_reproduction_{run_tag}",
        help="Template used to resolve prior results directory names.",
    )
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for generated next-round TOMLs.")
    parser.add_argument("--audit-csv", type=Path, help="Optional CSV summarizing centers, sigmas, and bounds.")
    parser.add_argument("--events", nargs="+", required=True, help="Event list to build.")
    parser.add_argument("--sigma-multiple", type=float, default=10.0, help="Prior width multiplier in units of prior-run sigma.")
    parser.add_argument("--theta-c", type=float, default=1.0, help="Fixed top-hat opening angle in radians.")
    parser.add_argument("--theta-v", type=float, default=0.0, help="Fixed observing angle in radians.")
    parser.add_argument(
        "--pl-model-name",
        default="powerlawVegasDylanSpectrumModel",
        help="Model class name to use for PL events.",
    )
    parser.add_argument(
        "--sbpl-model-name",
        default="VegasAfterglowModel",
        help="Model class name to use for SBPL events.",
    )
    parser.add_argument(
        "--skip-missing",
        action="store_true",
        help="Skip events missing minimized.json or summary.csv instead of failing.",
    )
    args = parser.parse_args()

    all_audit_rows: list[dict[str, Any]] = []
    args.output_dir.mkdir(parents=True, exist_ok=True)

    built = 0
    skipped = 0
    for raw_event in args.events:
        event = normalize_event_name(raw_event)
        if event not in THESIS:
            raise SystemExit(f"No thesis metadata found for event: {event}")

        results_name = results_name_for(event, args.run_tag, args.results_name_template)
        results_dir = resolve_results_dir(
            event=event,
            results_name=results_name,
            results_root=args.results_root,
            drive_root=args.drive_root,
            owner_subdir=args.owner_subdir,
        )
        source_path = results_dir / "model.toml"
        summary_path = results_dir / "summary.csv"
        minimized_path = results_dir / "minimized" / "minimized.json"
        output_path = args.output_dir / f"{event}.toml"

        missing = [str(path) for path in (source_path, summary_path, minimized_path) if not path.exists()]
        if missing:
            if args.skip_missing:
                print(f"SKIP {event}: missing {', '.join(missing)}")
                skipped += 1
                continue
            raise SystemExit(f"Missing required prior-run files for {event}: {', '.join(missing)}")

        source = _load_toml(source_path)
        minimized_flat = load_minimized_params(minimized_path)
        summary_stats = load_summary_stats(summary_path)
        config, audit_rows = build_config_from_results(
            source,
            event=event,
            minimized_flat=minimized_flat,
            summary_stats=summary_stats,
            sigma_multiple=args.sigma_multiple,
            theta_c=args.theta_c,
            theta_v=args.theta_v,
            pl_model_name=args.pl_model_name,
            sbpl_model_name=args.sbpl_model_name,
        )
        _write_toml(output_path, config)

        for row in audit_rows:
            row["event"] = event
            all_audit_rows.append(row)

        print(f"WROTE {event}: {output_path}")
        built += 1

    if args.audit_csv is not None:
        write_audit_csv(args.audit_csv, all_audit_rows)
        print(f"AUDIT {args.audit_csv}")

    print(f"SUMMARY built={built} skipped={skipped} run_tag={args.run_tag}")


if __name__ == "__main__":
    main()
