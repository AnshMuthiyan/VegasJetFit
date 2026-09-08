def resolve_vegas_resolutions(
    *,
    vegas_resolutions=None,
    vegas_resolution_phi=None,
    vegas_resolution_theta=None,
    vegas_resolution_t=None,
):
    """Return a VegasAfterglow ``resolutions`` tuple or None for its default."""
    components = (
        vegas_resolution_phi,
        vegas_resolution_theta,
        vegas_resolution_t,
    )
    if vegas_resolutions is not None:
        if any(value is not None for value in components):
            raise ValueError(
                "Use either vegas_resolutions or the three "
                "vegas_resolution_phi/theta/t values, not both."
            )
        values = tuple(vegas_resolutions)
    elif all(value is None for value in components):
        return None
    elif any(value is None for value in components):
        raise ValueError(
            "Set all three VegasAfterglow resolution values: "
            "vegas_resolution_phi, vegas_resolution_theta, vegas_resolution_t."
        )
    else:
        values = components

    if len(values) != 3:
        raise ValueError(
            "VegasAfterglow resolutions must contain exactly three values: "
            "(phi, theta, t)."
        )

    resolved = tuple(float(value) for value in values)
    if any(value <= 0.0 for value in resolved):
        raise ValueError("VegasAfterglow resolution values must be positive.")
    return resolved


def model_kwargs_with_resolution(
    *, jet, medium, observer, radiation, resolutions, reverse_radiation=None
):
    kwargs = {
        "jet": jet,
        "medium": medium,
        "observer": observer,
        "fwd_rad": radiation,
    }
    if resolutions is not None:
        kwargs["resolutions"] = resolutions
    if reverse_radiation is not None:
        kwargs["rvs_rad"] = reverse_radiation
    return kwargs
