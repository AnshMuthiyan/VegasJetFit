import numpy as np


TINY = 1e-300

# Fixed empirical bubble profile calibrated from the AMRVAC ``density_21``
# snapshot. We originally tried a median over the bubble-like subset, but the
# simple-model x-coordinate map pulled the ``density_23`` outer wall inward and
# created a nonphysical bump near x~0.8. The current implementation therefore
# adopts the smoother ``density_21`` profile directly, while still keeping the
# same three physical fit parameters (rt, nt, nism) and using the simple bubble
# closure for R2.
#
# Profile definition:
#   x = (r - Rt) / (R2 - Rt)
#   log10 n = log10(4 nt) + [log10(nism) - log10(4 nt)] * psi(x)
#
# We enforce a short post-shock shelf at 4 nt, then follow a reduced linearized
# approximation to the calibrated ``density_21`` psi(x), and finally blend
# smoothly to nism as x -> 1.
PSI_SHELF_END = 0.02
PSI_BLEND_START = 0.82
PSI_BLEND_VALUE = -0.97596627

PSI_KNOT_X = np.asarray(
    [
        0.0,
        0.02,
        0.05,
        0.10,
        0.15,
        0.20,
        0.35,
        0.50,
        0.65,
        0.72,
        0.78,
        0.82,
    ],
    dtype=float,
)
PSI_KNOT_Y = np.asarray(
    [
        0.0,
        0.0,
        -0.02387276,
        -0.02557549,
        -0.05940523,
        -0.29653253,
        -0.53368392,
        -0.62300054,
        -1.09729905,
        -1.10627881,
        -1.09210474,
        PSI_BLEND_VALUE,
    ],
    dtype=float,
)
PSI_KNOT_SLOPES = np.diff(PSI_KNOT_Y) / np.diff(PSI_KNOT_X)


def smoothstep(u):
    u = np.clip(np.asarray(u, dtype=float), 0.0, 1.0)
    return u * u * (3.0 - 2.0 * u)


def smoothstep_derivative(u):
    u = np.clip(np.asarray(u, dtype=float), 0.0, 1.0)
    return 6.0 * u * (1.0 - u)


def simple_bubble_outer_radius_cm(rt_cm, nt_cm3, nism_cm3):
    """Return the simple-bubble outer radius using the legacy mass closure."""
    n_sh = 4.0 * nt_cm3
    n_sh_old = max(4.0 * nt_cm3, 4.0 * nism_cm3)
    denom_old = max(n_sh_old - nism_cm3, TINY)
    ratio_old = (n_sh_old + 3.0 * nt_cm3) / denom_old
    r2_old = rt_cm * max(ratio_old, 1.0 + 1e-12) ** (1.0 / 3.0)
    delta_old = max(r2_old**3 - rt_cm**3, 0.0)
    r2_cubed = rt_cm**3 + (n_sh_old / max(n_sh, TINY)) * delta_old
    return max(r2_cubed, rt_cm**3 * (1.0 + 1e-12)) ** (1.0 / 3.0)


def empirical_psi_and_slope(x):
    """
    Return psi(x) and dpsi/dx for the fixed empirical bubble profile.

    The derivative is used to compute the local effective density slope
    k(r) = -d ln n / d ln r for the Dylan-smoothed spectral wrapper.
    """
    x_arr = np.atleast_1d(np.asarray(x, dtype=float))
    psi = np.ones_like(x_arr, dtype=float)
    dpsi_dx = np.zeros_like(x_arr, dtype=float)

    mask_inner = x_arr <= PSI_BLEND_START
    if np.any(mask_inner):
        x_inner = np.clip(x_arr[mask_inner], PSI_KNOT_X[0], PSI_BLEND_START)
        psi[mask_inner] = np.interp(x_inner, PSI_KNOT_X, PSI_KNOT_Y)

        idx = np.searchsorted(PSI_KNOT_X[1:], x_inner, side="right")
        idx = np.clip(idx, 0, len(PSI_KNOT_SLOPES) - 1)
        dpsi_dx[mask_inner] = PSI_KNOT_SLOPES[idx]

    mask_blend = (x_arr > PSI_BLEND_START) & (x_arr < 1.0)
    if np.any(mask_blend):
        u = (x_arr[mask_blend] - PSI_BLEND_START) / (1.0 - PSI_BLEND_START)
        s = smoothstep(u)
        psi[mask_blend] = (1.0 - s) * PSI_BLEND_VALUE + s
        dpsi_dx[mask_blend] = (
            (1.0 - PSI_BLEND_VALUE)
            * smoothstep_derivative(u)
            / (1.0 - PSI_BLEND_START)
        )

    if np.ndim(x) == 0:
        return float(psi[0]), float(dpsi_dx[0])
    return psi, dpsi_dx


def empirical_number_density_cm3(radius_cm, rt_cm, nt_cm3, nism_cm3, r2_cm):
    """Evaluate the fixed empirical-bubble number-density profile."""
    radius = np.asarray(radius_cm, dtype=float)
    r_safe = np.maximum(radius, 1.0)
    inner = nt_cm3 * np.maximum(rt_cm / r_safe, 1e-30) ** 2.0

    delta_r = max(r2_cm - rt_cm, 1e-30)
    x = (r_safe - rt_cm) / delta_r
    psi, _ = empirical_psi_and_slope(x)

    log_inner = np.log10(max(4.0 * nt_cm3, TINY))
    log_outer = np.log10(max(nism_cm3, TINY))
    cavity = 10.0 ** (log_inner + (log_outer - log_inner) * psi)
    number_density = np.where(r_safe < rt_cm, inner, cavity)

    if np.ndim(radius_cm) == 0:
        return float(np.asarray(number_density))
    return number_density


def empirical_local_k(radius_cm, rt_cm, nt_cm3, nism_cm3, r2_cm):
    """Return local effective k(r) = -d ln n / d ln r for the empirical bubble."""
    radius = np.asarray(radius_cm, dtype=float)
    r_safe = np.maximum(radius, 1.0)

    delta_r = max(r2_cm - rt_cm, 1e-30)
    x = (r_safe - rt_cm) / delta_r
    _, dpsi_dx = empirical_psi_and_slope(x)
    log_delta = np.log10(max(nism_cm3, TINY)) - np.log10(max(4.0 * nt_cm3, TINY))
    k_eff = -r_safe * log_delta * dpsi_dx / delta_r
    k_eff = np.where(r_safe < rt_cm, 2.0, np.where(r_safe >= r2_cm, 0.0, k_eff))
    # The Dylan/GS02 spectral surrogate expects a modest local power-law index.
    # The empirical outer wall can be much steeper than that, so clamp to the
    # same exploratory negative-k regime we already use in fitting.
    k_eff = np.clip(k_eff, -10.0, 2.0)

    if np.ndim(radius_cm) == 0:
        return float(np.asarray(k_eff))
    return k_eff
