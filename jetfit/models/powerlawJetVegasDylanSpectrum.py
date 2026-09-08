from jetfit.models.powerlawVegasDylanSpectrum import powerlawVegasDylanSpectrumModel


class PowerlawJetVegasDylanSpectrumModel(powerlawVegasDylanSpectrumModel):
    """Native VegasAfterglow power-law jet with GS02/Dylan-style smoothing.

    The current VegasAfterglow structured-jet API uses ``k_e`` and ``k_g`` to
    define the angular profile.  The campaign notes also specify ``s=4``; that
    value is retained here for bookkeeping and cross-checks, but the local
    VegasAfterglow power-law jet implementation does not consume it directly.

    The historical model name is retained so existing campaign configs do not
    need to change when switching from the old Python smoothing wrapper to the
    compiled native spectrum path.
    """

    def __init__(
        self,
        *args,
        k_e=2.0,
        k_g=2.0,
        s=4.0,
        jet_type="powerlaw",
        diagnostic_jet_type=None,
        **kwargs,
    ):
        resolved_jet_type = str(diagnostic_jet_type or jet_type).lower()
        if resolved_jet_type != "powerlaw" and diagnostic_jet_type is None:
            raise ValueError(
                "PowerlawJetVegasDylanSpectrumModel requires jet_type='powerlaw'"
            )

        self.s = float(s)
        super().__init__(
            *args,
            k_e=float(k_e),
            k_g=float(k_g),
            jet_type=resolved_jet_type,
            **kwargs,
        )


class PowerlawJetCommonSVegasDylanSpectrumModel(PowerlawJetVegasDylanSpectrumModel):
    """Power-law structured jet with one fitted angular index.

    This one-off model is for tests where the historical ``s`` parameter should
    actually control the angular jet structure.  The native VegasAfterglow
    power-law jet accepts separate ``k_e`` and ``k_g`` indices, so here we map
    the sampled common index as ``k_e = k_g = s``.  The original
    ``PowerlawJetVegasDylanSpectrumModel`` keeps treating ``s`` as bookkeeping
    only, preserving existing campaign behavior.
    """

    def __init__(self, *args, s=4.0, **kwargs):
        common_s = float(s)
        self.s = common_s
        # Configs keep k_e/k_g rows for compatibility with ordinary power-law
        # jet products; this explicit common-s wrapper makes sampled s
        # authoritative for both native angular indices.
        kwargs.pop("k_e", None)
        kwargs.pop("k_g", None)
        super().__init__(*args, k_e=common_s, k_g=common_s, s=common_s, **kwargs)
