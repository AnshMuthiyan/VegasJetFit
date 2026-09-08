#!/usr/bin/env python3
"""Build unseeded smooth-broken-CSM campaign configs.

The source files are Dylan-prior SBPL configs.  This script removes all
``initial_guess`` / ``initial_sigma`` entries so walker starts are drawn from
the full priors, then writes the three geometry variants used in the recent
single-power-law CSM tests:

1. top-hat, on-axis, theta_c = 1 rad;
2. power-law structured jet, on-axis, theta_c free;
3. power-law structured jet, theta_c and theta_v free.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path

import toml


EVENTS = ("080319B", "080413B")


def strip_initial_values(obj):
    if isinstance(obj, dict):
        obj.pop("initial_guess", None)
        obj.pop("initial_sigma", None)
        for value in obj.values():
            strip_initial_values(value)
    elif isinstance(obj, list):
        for value in obj:
            strip_initial_values(value)


def find_section(entries, name):
    for entry in entries:
        if entry.get("name") == name:
            return entry
    raise KeyError(f"missing [[model]] section for {name!r}")


def set_fixed(entries, name, value):
    entry = find_section(entries, name)
    entry.pop("prior", None)
    entry["value"] = value


def set_uniform(entries, name, lower, upper):
    entry = find_section(entries, name)
    entry.pop("value", None)
    entry["prior"] = {"type": "uniform", "lower": lower, "upper": upper}


def ensure_fixed(entries, name, value):
    for entry in entries:
        if entry.get("name") == name:
            entry.pop("prior", None)
            entry["scale"] = "linear"
            entry["value"] = value
            return
    entries.append({"name": name, "scale": "linear", "value": value})


def build_variant(base, variant):
    cfg = deepcopy(base)
    strip_initial_values(cfg)

    model_entries = cfg["model"]

    # Make the native Dylan fast-to-slow spectral smoothing explicit in the
    # run card; the SBPL wrapper defaults to this, but the fixed parameter is
    # easier to audit later.
    ensure_fixed(model_entries, "smooth_fast_to_slow_transition", 1.0)

    if variant == "tophat_onaxis_theta1p0":
        cfg["name"] = "VegasAfterglowModel"
        set_fixed(model_entries, "theta_c", 1.0)
        set_fixed(model_entries, "theta_v", 0.0)
        for name in ("k_e", "k_g", "s"):
            cfg["model"] = [e for e in cfg["model"] if e.get("name") != name]
        return cfg

    if variant == "structjet_thetacfree_onaxis":
        cfg["name"] = "PowerlawJetVegasAfterglowModel"
        set_uniform(model_entries, "theta_c", 0.001, 1.0)
        set_fixed(model_entries, "theta_v", 0.0)
        ensure_fixed(model_entries, "k_e", 2.0)
        ensure_fixed(model_entries, "k_g", 2.0)
        ensure_fixed(model_entries, "s", 4.0)
        return cfg

    if variant == "structjet_thetav_thetacfree":
        cfg["name"] = "PowerlawJetVegasAfterglowModel"
        set_uniform(model_entries, "theta_c", 0.001, 1.0)
        set_uniform(model_entries, "theta_v", 0.0, 1.0)
        ensure_fixed(model_entries, "k_e", 2.0)
        ensure_fixed(model_entries, "k_g", 2.0)
        ensure_fixed(model_entries, "s", 4.0)
        return cfg

    raise ValueError(f"unknown variant: {variant}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir",
        default="/Users/jkeohane/GRBs/VegasJetFit/dylan_sbpl_configs_init5pct_active",
    )
    parser.add_argument(
        "--output-root",
        default="/Users/jkeohane/GRBs/VegasJetFit",
    )
    parser.add_argument("--events", nargs="+", default=list(EVENTS))
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    output_root = Path(args.output_root)
    variants = {
        "tophat_onaxis_theta1p0": output_root / "sbpl_unseeded_tophat_configs_active",
        "structjet_thetacfree_onaxis": output_root / "sbpl_unseeded_structjet_thetacfree_onaxis_configs_active",
        "structjet_thetav_thetacfree": output_root / "sbpl_unseeded_structjet_thetav_thetacfree_configs_active",
    }

    for out_dir in variants.values():
        out_dir.mkdir(parents=True, exist_ok=True)

    for event in args.events:
        source = source_dir / f"{event}.toml"
        if not source.exists():
            raise FileNotFoundError(source)
        base = toml.load(source)
        for variant, out_dir in variants.items():
            cfg = build_variant(base, variant)
            out_path = out_dir / f"{event}.toml"
            out_path.write_text(toml.dumps(cfg), encoding="utf-8")
            print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
