"""Separate true bandpass averaging from native time-array context effects."""

import argparse
import json
from pathlib import Path

import numpy as np
from dust_extinction.parameter_averages import CCM89

from jetfit.core.bandpass import C_ANGSTROM_PER_SECOND, get_bandpass
from jetfit.core.input import Observation
from jetfit.mcmc.mcmc import MCMCModels
from jetfit.models.powerlawJetVegasDylanSpectrum import (
    PowerlawJetVegasDylanSpectrumModel,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observations", type=Path)
    parser.add_argument("minimized_json", type=Path)
    parser.add_argument("--repeat-central", type=int, default=18)
    args = parser.parse_args()
    if args.repeat_central < 1:
        parser.error("repeat-central must be positive")

    obs = Observation.from_csv(args.observations)
    with args.minimized_json.open(encoding="utf-8") as source:
        params = json.load(source)["params"]
    afterglow = PowerlawJetVegasDylanSpectrumModel(**params["model"])
    wrapper = MCMCModels(
        obs, PowerlawJetVegasDylanSpectrumModel,
        ext_model=CCM89, bandpass_integration="verified",
        bandpass_nodes=16, bandpass_selective=False,
        source_extinction_model="ccm89",
        igm_absorption_model="none", host_hi_absorption_model="none",
    )
    arrays = obs.as_arrays
    whole_context_intrinsic = np.asarray(afterglow.model(obs), dtype=float)
    for band in np.unique(arrays.bands[arrays.sflux_loc]):
        if get_bandpass(str(band)) is None:
            continue
        rows = arrays.sflux_loc & (arrays.bands == band)
        times = arrays.times[rows]
        frequencies = arrays.frequencies[rows]
        wave_numbers = frequencies / (C_ANGSTROM_PER_SECOND / 1.0e4)
        attenuation = wrapper._node_extinction(wave_numbers, params, band=str(band))
        whole_central = whole_context_intrinsic[rows] * attenuation
        repeat_times = np.repeat(times, args.repeat_central)
        repeat_freq = np.repeat(frequencies, args.repeat_central)
        repeated = np.asarray(afterglow.spectral_flux(
            repeat_times, repeat_freq
        ), dtype=float).reshape(times.size, args.repeat_central)
        center_in_band_context = repeated[:, 0] * attenuation
        if not np.allclose(repeated, repeated[:, :1], rtol=1e-12, atol=0):
            raise RuntimeError(f"Repeated central frequency changed flux in {band}")
        integrated = wrapper.integrate_spectral_bandpass(
            afterglow, str(band), times, params
        )
        grid_ratio = center_in_band_context / whole_central
        bandpass_ratio = integrated / center_in_band_context
        combined_ratio = integrated / whole_central
        print(
            f"{band:8s} n={times.size:3d} "
            f"grid_ratio=[{grid_ratio.min():.4f},{grid_ratio.max():.4f}] "
            f"bandpass_ratio=[{bandpass_ratio.min():.4f},{bandpass_ratio.max():.4f}] "
            f"combined_ratio=[{combined_ratio.min():.4f},{combined_ratio.max():.4f}]"
        )


if __name__ == "__main__":
    main()
