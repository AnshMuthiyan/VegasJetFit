"""Compare a Vegas flux at one time with the same time in an anchored array."""

import argparse
import json

import numpy as np

from jetfit.models.powerlawJetVegasDylanSpectrum import (
    PowerlawJetVegasDylanSpectrumModel,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("minimized_json", help="Saved minimized.json with params.model")
    parser.add_argument("--time-days", type=float, default=0.02)
    parser.add_argument("--anchor-days", type=float, default=0.0002)
    parser.add_argument("--frequency-hz", type=float, default=5e14)
    args = parser.parse_args()
    if not 0 < args.anchor_days < args.time_days or args.frequency_hz <= 0:
        parser.error("Require 0 < anchor-days < time-days and frequency-hz > 0.")

    with open(args.minimized_json, encoding="utf-8") as source:
        parameters = json.load(source)["params"]["model"]
    model = PowerlawJetVegasDylanSpectrumModel(**parameters)
    single = float(model.spectral_flux(
        np.array([args.time_days]), np.array([args.frequency_hz])
    )[0])
    anchored = float(model.spectral_flux(
        np.array([args.anchor_days, args.time_days]),
        np.array([args.frequency_hz, args.frequency_hz])
    )[-1])
    print(f"time_days={args.time_days:g} anchor_days={args.anchor_days:g} "
          f"frequency_hz={args.frequency_hz:g}")
    print(f"single_mjy={single:.9g} anchored_mjy={anchored:.9g}")
    print(f"anchored_over_single_minus_one={(anchored / single - 1):.6%}")


if __name__ == "__main__":
    main()
