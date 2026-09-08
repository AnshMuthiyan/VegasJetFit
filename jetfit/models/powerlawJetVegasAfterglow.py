from jetfit.models.vegasafterglow import VegasAfterglowModel


class PowerlawJetVegasAfterglowModel(VegasAfterglowModel):
    """VegasAfterglow wrapper with a fixed power-law jet structure."""

    def __init__(
        self,
        *args,
        k_e=2.0,
        k_g=2.0,
        s=4.0,
        jet_type="powerlaw",
        **kwargs,
    ):
        if str(jet_type).lower() != "powerlaw":
            raise ValueError(
                "PowerlawJetVegasAfterglowModel requires jet_type='powerlaw'"
            )

        self.s = float(s)
        super().__init__(
            *args,
            k_e=float(k_e),
            k_g=float(k_g),
            jet_type="powerlaw",
            **kwargs,
        )
