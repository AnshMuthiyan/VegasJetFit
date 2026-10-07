"""Benchmark the same GRB observations against a selected JetFit checkout."""

import argparse
import inspect
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np


class AnalyticAfterglow:
    """Smooth spectrum for separating filter work from native Vegas work."""

    slope = -0.7

    def __init__(self, **_params):
        pass

    def spectral_flux(self, times, frequencies):
        times = np.asarray(times, dtype=float)
        frequencies = np.asarray(frequencies, dtype=float)
        return (1.0 + times) ** -1.0 * (frequencies / 1.0e15) ** self.slope

    def model(self, observation):
        values = observation.as_arrays
        return self.spectral_flux(values.times, values.frequencies)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--parameters", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", choices=("analytic", "vegas"), default="vegas")
    parser.add_argument("--rows-per-band", type=int, default=2,
                        help="Zero uses every included row; otherwise sample spectral rows.")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--cases", default="none,full,selective")
    parser.add_argument("--nodes", type=int, default=16,
                        help="Intrinsic spectrum nodes; 0 uses the full response grid.")
    parser.add_argument("--igm", choices=("none", "inoue2014", "trotter2011"),
                        default="none")
    parser.add_argument("--source-dust", choices=("ccm89", "trotter2011"),
                        default="ccm89")
    parser.add_argument("--analytic-slope", type=float, default=-0.7)
    parser.add_argument("--override-redshift", type=float)
    parser.add_argument("--override-ebv-source", type=float)
    args = parser.parse_args()
    if args.repeats < 1 or args.rows_per_band < 0 or args.nodes < 0 or args.nodes == 1:
        parser.error("repeats must be positive; nodes must be 0 or at least 2")

    sys.path.insert(0, str(args.checkout.resolve()))
    from dust_extinction.parameter_averages import CCM89
    from jetfit.core.input import Observation
    from jetfit.mcmc.mcmc import MCMCModels
    from jetfit.models.powerlawJetVegasDylanSpectrum import (
        PowerlawJetVegasDylanSpectrumModel,
    )

    with args.parameters.open(encoding="utf-8") as source:
        parameters = json.load(source)["params"]
    if args.override_redshift is not None:
        parameters["model"]["z"] = args.override_redshift
    if args.override_ebv_source is not None:
        parameters["extinction"]["ebv_source_frame"] = args.override_ebv_source
    AnalyticAfterglow.slope = args.analytic_slope
    obs = Observation.from_csv(args.observations)
    if args.rows_per_band:
        values = obs.as_arrays
        indices = []
        for band in np.unique(values.bands[values.sflux_loc]):
            band_rows = np.flatnonzero(values.sflux_loc & (values.bands == band))
            picked = np.linspace(0, band_rows.size - 1,
                                 min(args.rows_per_band, band_rows.size), dtype=int)
            indices.extend(band_rows[picked])
        data = obs.get_data("included")[np.sort(indices)]
        obs = Observation(data, include=np.ones(len(data)))
        # This subset is a forward-model timing probe, not a likelihood:
        # its host/offset group masks are intentionally absent.
        parameters["host"] = None
    if args.model == "analytic" and np.any(~obs.as_arrays.sflux_loc):
        parser.error("analytic model requires spectral-only sampled rows")
    model = (AnalyticAfterglow if args.model == "analytic"
             else PowerlawJetVegasDylanSpectrumModel)

    results = {}
    for name in args.cases.split(","):
        if name not in ("none", "full", "selective"):
            parser.error(f"unknown case {name!r}")
        kwargs = dict(
            ext_model=CCM89,
            bandpass_integration="none" if name == "none" else "verified",
            bandpass_nodes=args.nodes,
            source_extinction_model=args.source_dust,
            igm_absorption_model=args.igm,
            host_hi_absorption_model="none",
        )
        if "bandpass_selective" in inspect.signature(MCMCModels).parameters:
            kwargs["bandpass_selective"] = (name == "selective")
        elif name == "selective":
            parser.error("selective mode is absent from this checkout")
        wrapper = MCMCModels(obs, model, **kwargs)
        elapsed = []
        prediction = None
        for _ in range(args.repeats):
            start = perf_counter()
            prediction = np.asarray(wrapper.model(parameters), dtype=float)
            elapsed.append(perf_counter() - start)
            if prediction.shape != (obs.length,) or not np.all(np.isfinite(prediction)):
                raise RuntimeError(f"{name}: model returned invalid prediction")
        treatment = (
            wrapper.bandpass_treatment(parameters["model"]["z"])
            if hasattr(wrapper, "bandpass_treatment") else "unavailable"
        )
        results[name] = {
            "seconds": elapsed,
            "median_seconds": float(np.median(elapsed)),
            "prediction_mjy_or_native_units": prediction.tolist(),
            "band_treatment": treatment,
        }
        print(f"{name}: {elapsed} s; median {np.median(elapsed):.3f} s",
              flush=True)

    payload = {
        "checkout": str(args.checkout.resolve()),
        "model": args.model,
        "rows_per_band": args.rows_per_band,
        "repeats": args.repeats,
        "nodes": args.nodes,
        "igm": args.igm,
        "source_dust": args.source_dust,
        "analytic_slope": args.analytic_slope if args.model == "analytic" else None,
        "override_redshift": args.override_redshift,
        "override_ebv_source": args.override_ebv_source,
        "n_rows": obs.length,
        "bands": obs.as_arrays.bands.tolist(),
        "times_days": obs.as_arrays.times.tolist(),
        "errors": obs.as_arrays.errors.tolist(),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
