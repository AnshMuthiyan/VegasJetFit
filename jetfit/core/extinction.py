"""
Trotter/Reichart hybrid (CCM89 + FM88/90) source-frame dust extinction law.

This module implements the deterministic mapping

    x = 1 / lambda[um]  --->  A_lambda

described in Trotter's dissertation [T11]_ Section 3.3.3 ("Source-Frame Dust
Extinction Model"), which in turn is built on the Cardelli, Clayton & Mathis
(1989) [CCM89]_ IR/optical law and the Fitzpatrick & Massa (1988) [FM88]_ UV
law, following the hybrid prescription first assembled by Reichart (2001)
[R01]_.

Wavelength convention
----------------------
Every function in this module takes ``x``, **not** a wavelength. By
definition (Trotter Eq. 3.10; Reichart Eq. 54)::

    x = 1 / lambda_um = (lambda / 1 micron)^-1

This matches the convention already used by the project's data layer:
``jetfit.core.input.ObsArray.wave_numbers`` is computed as
``1 / wavelength.to_value('um')`` at ingestion time (see
``ObsArray.from_data``), i.e. it *is* ``x`` in this sense. Production code
should pass those precomputed values straight into this module. A
convenience :func:`wavelength_to_x` is provided for standalone use (tests,
validation scripts, notebooks) where only a wavelength is on hand; it is not
used anywhere in the hot path and performs no redshift/frame handling of its
own (see "Frame handling" below).

Frame handling
--------------
This module is deliberately frame-agnostic: it has no notion of redshift,
observer frame, or source frame. Converting an observer-frame wavelength to
a source (host-galaxy) frame wavelength, i.e. ``lambda_host = lambda_obs /
(1+z)``, is the caller's responsibility (see
``jetfit.mcmc.mcmc.MCMCModels.model_extinction``, which multiplies the
observed wave numbers by ``(1+z)`` before calling into this module for
source-frame extinction, and passes them through unmodified for Milky Way
extinction).

Fundamental parameters
-----------------------
The source-frame law has eight fundamental parameters (Trotter Section
3.3.3; Reichart Section 3): ``Av``, ``Rv``, ``c1``, ``c2``, ``c3`` (or
equivalently the bump height ``BH = c3 / gamma**2``), ``c4``, ``gamma`` and
``x0``. Because the project's Trotter-dust machinery
(``jetfit.mcmc.mcmc.TrotterDustPrior``) is parameterized by bump height
rather than by ``c3`` directly, :func:`trotter_extinction` accepts ``c3``
while :func:`trotter_extinction_bh` accepts ``BH`` and reconstructs
``c3 = BH * gamma**2`` internally. Do not pass ``BH`` to a ``c3`` argument
or vice versa -- see the "BH vs. c3" note below.

Splice equation: a discrepancy between the task brief and the thesis
----------------------------------------------------------------------
Reichart (2001) Eq. 61 (and, identically, the equation handed down in this
task's brief) splices the CCM and FM curves for ``1.82 <= x <= 3.3`` as a
plain linear blend of the two curves, each evaluated at the *current* x::

    A_lambda = A_CCM(x) + [(x - 1.82) / 1.48] * [A_FM(x) - A_CCM(x)]      (*)

Trotter's dissertation (the primary reference this task names explicitly,
Eq. 3.29, p. 111) instead scales the CCM curve's own shape by a single
linear ramp between 1 (at x=1.82) and the fixed ratio A_FM(3.3)/A_CCM(3.3)
(at x=3.3)::

    A_lambda = A_CCM(x) * [1 + (A_FM(3.3)/A_CCM(3.3) - 1) * (x-1.82)/1.48]  (**)

Both forms are continuous at x=1.82 and x=3.3 (they reduce to A_CCM(1.82)
and A_FM(3.3) respectively, since A_CCM(1.82) == A_FM(1.82's boundary value)
is not required -- continuity is with the CCM branch below 1.82 and the FM
branch above 3.3, not between each other), but they are *not* algebraically
identical in between: (*) blends the shapes of both curves pointwise, while
(**) rescales only the CCM curve's shape. This was confirmed by direct
comparison against Trotter's Figure 3.5 (see the validation script and
implementation report); Trotter's own worked example reproduces (**), not
(*).

Per the task's own stated hierarchy ("Trotter/Reichart equations > published
numerical parameters > independent implementations > visual plot
agreement") and because Trotter's dissertation Sections 3.3-3.4 are the
explicitly named primary reference, this module implements (**) as the
default (``splice="thesis"``). Form (*) is retained as
``splice="reichart"`` for comparison, reproducibility of results derived
against the older Reichart (2001) formulation, and regression testing. Do
not silently prefer one over the other elsewhere in the codebase without
checking which convention a given downstream figure/paper used.

BH vs. c3
---------
``BH = c3 / gamma**2`` is the bump *height*: the Drude profile
``D(x0; x0, gamma) = 1/gamma**2``, so ``c3 * D(x0) = BH`` exactly, i.e. BH is
the bump's peak amplitude above the underlying linear continuum. Fitting to
BH is preferred over fitting to c3 directly because BH and gamma are
observed to be only weakly correlated, whereas c3 and gamma are strongly
correlated (Trotter p. 109-110). :func:`trotter_extinction_bh` performs the
``c3 = BH * gamma**2`` reconstruction; :func:`trotter_extinction` takes c3
as given and performs no such reconstruction, so passing a bump height where
c3 is expected (or vice versa) will silently produce a differently-shaped
bump rather than raising an error. A regression test
(``test_bh_c3_equivalence`` in ``test/core/test_extinction.py``) locks in
the correct relationship between the two entry points.

What this module does *not* do
--------------------------------
- No MCMC sampling, priors, or likelihood evaluation. The c2-dependent
  correlative priors on c1, Rv and BH are implemented in
  ``jetfit.mcmc.mcmc.TrotterDustPrior`` and are not duplicated here.
- No redshift or observer/source frame conversion.
- No Milky Way extinction. Trotter models Milky Way extinction with the
  *full* CCM89 law (Eq. 3.10-3.15), extended with the original CCM89
  UV/far-UV polynomial branches out to the Lyman limit (x < 10.97), rather
  than the CCM+FM hybrid used for source-frame extinction. That is already
  correctly handled elsewhere in this project via
  ``dust_extinction.parameter_averages.CCM89`` (see ``jetfit/ampy.py`` and
  ``jetfit/mcmc/mcmc.py``) and is not reimplemented here.
- No Ly-alpha forest, damped Ly-alpha, Lyman-limit, or any other hydrogen
  absorption (Trotter Section 3.4). Dust extinction and HI absorption are
  distinct physical processes and are not mixed in this module: this
  function never returns infinite extinction to emulate the Lyman limit.
- No filter/bandpass integration.

References
----------
.. [T11] Trotter, A. S. 2011, Ph.D. dissertation, UNC-Chapel Hill,
   "The Gamma-Ray Burst Afterglow Modeling Project: Foundational Statistics
   and Absorption & Extinction Models", Sections 3.3.3-3.3.4.
.. [R01] Reichart, D. E. 2001, ApJ, 553, 235 (preprint arXiv:astro-ph/9912368),
   "Dust Extinction Curves and Ly-alpha Forest Flux Deficits for Use in
   Modeling GRB Afterglows and All Other Extragalactic Point Sources",
   Section 3, Eqs. 54-61.
.. [CCM89] Cardelli, J. A., Clayton, G. C., & Mathis, J. S. 1989, ApJ, 345, 245.
.. [FM88] Fitzpatrick, E. L., & Massa, D. 1988, ApJ, 328, 734.
"""

import numpy as np

__all__ = [
    "X_LOW",
    "X_HIGH",
    "X_SPLICE_WIDTH",
    "X_FUV",
    "CCM_X_IR_MAX",
    "wavelength_to_x",
    "x_to_wavelength_um",
    "drude",
    "fm_curvature",
    "ccm_ab",
    "ccm_extinction",
    "fm_color_excess",
    "fm_extinction",
    "trotter_extinction",
    "trotter_extinction_bh",
    "transmission",
    "delta_log10_flux",
    "TrotterExtinction",
    "resolve_source_frame_transmission",
]

# --------------------------------------------------------------------------
# Domain boundaries (Trotter Eqs. 3.10-3.29; Reichart Eqs. 54-61)
# --------------------------------------------------------------------------
X_LOW = 1.82
"""x below which the source-frame law is pure CCM."""

X_HIGH = 3.30
"""x above which the source-frame law is pure FM."""

X_SPLICE_WIDTH = X_HIGH - X_LOW
"""3.3 - 1.82 = 1.48, the width of the CCM/FM transition zone."""

X_FUV = 5.9
"""x above which the FM far-UV curvature term F(x) turns on."""

CCM_X_IR_MAX = 1.1
"""x boundary between the CCM IR branch and the CCM optical/NIR polynomial."""

# Wavelength-unit conversion factors to microns, for the wavelength_to_x
# convenience function only (not used internally).
_UNIT_TO_UM = {
    "um": 1.0,
    "micron": 1.0,
    "microns": 1.0,
    "AA": 1.0e-4,
    "angstrom": 1.0e-4,
    "A": 1.0e-4,
    "nm": 1.0e-3,
    "m": 1.0e6,
}


def wavelength_to_x(wavelength, unit="AA"):
    """
    Convenience conversion from a wavelength to ``x = 1 / lambda_um``.

    This is provided for standalone use (tests, validation scripts,
    notebooks) and is *not* used by the production data path: the project's
    ``ObsArray`` already performs this conversion once, at data-ingestion
    time, from an ``astropy.units`` wavelength. This function exists so the
    same convention can be exercised without needing an ``astropy.units``
    object on hand, and so unit handling is explicit and testable in one
    place rather than repeated ad hoc in scripts.

    Parameters
    ----------
    wavelength : float or array_like
        Wavelength value(s), in the unit given by ``unit``.

    unit : str, optional, default='AA'
        One of ``'AA'``/``'angstrom'``/``'A'`` (Angstrom), ``'nm'``,
        ``'um'``/``'micron'``/``'microns'``, or ``'m'``.

    Returns
    -------
    float or np.ndarray
        ``x = 1 / lambda_um``, with the same shape as ``wavelength``.
    """
    try:
        factor = _UNIT_TO_UM[unit]
    except KeyError:
        raise ValueError(
            f"Unknown wavelength unit {unit!r}; expected one of "
            f"{sorted(_UNIT_TO_UM)}."
        )

    wl = np.asarray(wavelength, dtype=np.float64) * factor

    if not np.all(np.isfinite(wl)):
        raise ValueError("wavelength must be finite.")
    if np.any(wl <= 0):
        raise ValueError("wavelength must be strictly positive.")

    return 1.0 / wl


def x_to_wavelength_um(x):
    """Inverse of the x convention: ``lambda_um = 1 / x``."""
    x = np.asarray(x, dtype=np.float64)
    _validate_x(x)
    return 1.0 / x


def _validate_x(x):
    """Raise a clear error for non-finite or non-positive x."""
    if not np.all(np.isfinite(x)):
        raise ValueError(
            "x (= 1/lambda_um) must be finite; got NaN/Inf. This usually "
            "indicates a zero or negative wavelength upstream."
        )
    if np.any(x <= 0):
        raise ValueError("x (= 1/lambda_um) must be strictly positive.")


def _validate_finite(**kwargs):
    """Raise a clear, per-parameter error for any non-finite scalar kwarg."""
    for name, val in kwargs.items():
        if not np.isfinite(val):
            raise ValueError(f"Parameter {name!r} must be finite; got {val!r}.")


# --------------------------------------------------------------------------
# Drude profile and FM far-UV curvature (Trotter Eqs. 3.26-3.27)
# --------------------------------------------------------------------------
def drude(x, x0, gamma):
    """
    Fitzpatrick & Massa (1988) Drude profile, ``D(x; x0, gamma)``.

    ``D(x; x0, gamma) = x**2 / [(x**2 - x0**2)**2 + x**2 * gamma**2]``

    This is the functional form of the absorption cross-section of a
    forced, damped harmonic oscillator; near resonance it reduces to a
    Lorentzian (Trotter p. 109; Reichart Section 3.2). ``D`` peaks at
    ``x = x0`` with peak value ``1 / gamma**2``, so ``c3 * D(x0) = c3 /
    gamma**2 = BH`` exactly -- the "bump height" -- which is why the bump is
    more naturally parameterized by ``(BH, gamma)`` than by ``(c3, gamma)``
    (see :func:`trotter_extinction_bh`).

    Parameters
    ----------
    x : float or array_like
        Inverse wavelength(s), in inverse microns.

    x0 : float
        Bump center, in inverse microns (Trotter/Reichart find
        ``x0 ~ 4.6``, corresponding to ~2175 A).

    gamma : float
        Bump width parameter (approximately the FWHM in x).

    Returns
    -------
    float or np.ndarray
        ``D(x; x0, gamma)``, with the same shape as ``x``.
    """
    x = np.asarray(x, dtype=np.float64)
    return x**2 / ((x**2 - x0**2) ** 2 + x**2 * gamma**2)


def fm_curvature(x):
    """
    Fitzpatrick & Massa (1988) far-UV curvature term, ``F(x)`` (Trotter Eq.
    3.27; Reichart Eq. 59).

    ``F(x) = 0``                                      for ``x < 5.9``
    ``F(x) = 0.5392*(x-5.9)**2 + 0.05644*(x-5.9)**3``  for ``x >= 5.9``

    Parameters
    ----------
    x : float or array_like
        Inverse wavelength(s), in inverse microns.

    Returns
    -------
    float or np.ndarray
        ``F(x)``, with the same shape as ``x``. Identically zero below
        ``X_FUV`` (5.9 um^-1); this function performs no extrapolation
        beyond what the polynomial itself gives above that point (the task
        brief explicitly calls for using the equation as given, not an
        approximation).
    """
    x = np.asarray(x, dtype=np.float64)
    out = np.zeros(x.shape, dtype=np.float64)
    hi = x >= X_FUV
    dx = x[hi] - X_FUV
    out[hi] = 0.5392 * dx**2 + 0.05644 * dx**3
    if x.ndim == 0:
        return out.item()
    return out


# --------------------------------------------------------------------------
# CCM89 IR/optical component (Trotter Eqs. 3.10-3.12; Reichart Eqs. 54-56)
# --------------------------------------------------------------------------
def ccm_ab(x):
    """
    Cardelli, Clayton & Mathis (1989) ``a(x)``, ``b(x)`` polynomials.

    Covers the two branches needed by the source-frame hybrid law: the IR
    branch (``x < 1.1``) and the optical/near-UV branch (``1.1 <= x <=
    3.3``). The extended CCM89 UV/far-UV branches (``3.3 < x < 10.97``,
    Trotter Eqs. 3.13-3.15) are *not* implemented here, because the
    source-frame model never evaluates CCM above x=3.3 -- above 1.82 it
    blends into, and above 3.3 it is replaced entirely by, the FM law (see
    module docstring). Those extended branches belong to the *Milky Way*
    extinction model, which is a separate, already-implemented code path
    (``dust_extinction.parameter_averages.CCM89``).

    Note on the IR branch's lower bound: Reichart (2001) restricts the IR
    branch to ``0.3 <= x < 1.1``. Trotter's dissertation states the IR
    branch as simply ``x < 1.1`` with no lower bound (Eq. 3.11), and his own
    Figure 3.5 plots the combined curve smoothly down to ``x = 0`` using
    exactly this formula (``a(0) = b(0) = 0``, so the curve there reduces to
    ``E(lambda-V)/E(B-V) = -Rv``, matching the figure). This module follows
    Trotter and evaluates the IR polynomial for any ``0 < x < 1.1``; no
    warning or restriction is applied at ``x = 0.3``, since the formula is
    mathematically well-behaved there and the primary reference itself
    relies on this. (In practice, real photometric data never approaches
    ``x ~ 0`` -- the project's own "extinguishable" wavelength mask spans
    ``x`` from about 0.3 to 10 -- so this only matters for validation
    plots that reproduce Trotter's Figure 3.5.)

    Parameters
    ----------
    x : float or array_like
        Inverse wavelength(s), in inverse microns. Must be > 0 and <= 3.3;
        use :func:`fm_color_excess`/:func:`fm_extinction` above x=3.3.

    Returns
    -------
    (a, b) : tuple of (float or np.ndarray)
        ``a(x)`` and ``b(x)``, each with the same shape as ``x``.
    """
    x = np.asarray(x, dtype=np.float64)
    _validate_x(x)
    if np.any(x > X_HIGH):
        raise ValueError(
            "ccm_ab is only defined for 0 < x <= 3.3; use fm_extinction "
            "above x=3.3."
        )

    a = np.empty(x.shape, dtype=np.float64)
    b = np.empty(x.shape, dtype=np.float64)

    ir = x < CCM_X_IR_MAX
    opt = ~ir

    x_ir = x[ir]
    a[ir] = 0.574 * x_ir**1.61
    b[ir] = -0.527 * x_ir**1.61

    y = x[opt] - X_LOW
    a[opt] = (
        1.0
        + 0.17699 * y
        - 0.50447 * y**2
        - 0.02427 * y**3
        + 0.72085 * y**4
        + 0.01979 * y**5
        - 0.77530 * y**6
        + 0.32999 * y**7
    )
    b[opt] = (
        1.41338 * y
        + 2.28305 * y**2
        + 1.07233 * y**3
        - 5.38434 * y**4
        - 0.62251 * y**5
        + 5.30260 * y**6
        - 2.09002 * y**7
    )

    if x.ndim == 0:
        return a.item(), b.item()
    return a, b


def ccm_extinction(x, Av, Rv):
    """
    CCM89 extinction, ``A_lambda,CCM = Av * [a(x) + b(x)/Rv]`` (Trotter Eq.
    3.10; Reichart Eq. 54).

    Parameters
    ----------
    x : float or array_like
        Inverse wavelength(s), in inverse microns, with ``0 < x <= 3.3``.

    Av : float
        V-band extinction, in magnitudes.

    Rv : float
        ``Rv = Av / E(B-V)``, nonzero.

    Returns
    -------
    float or np.ndarray
        ``A_lambda`` in magnitudes, with the same shape as ``x``.
    """
    if Rv == 0:
        raise ValueError("Rv must be nonzero.")
    a, b = ccm_ab(x)
    return Av * (a + b / Rv)


# --------------------------------------------------------------------------
# FM88 UV component (Trotter Eqs. 3.25-3.28; Reichart Eqs. 57-60)
# --------------------------------------------------------------------------
def fm_color_excess(x, c1, c2, c3, c4, x0, gamma):
    """
    Fitzpatrick & Massa (1988) UV color-excess curve,
    ``k(x) = E(lambda-V)/E(B-V) = c1 + c2*x + c3*D(x;x0,gamma) + c4*F(x)``
    (Trotter Eq. 3.25; Reichart Eq. 57).

    Parameters
    ----------
    x : float or array_like
        Inverse wavelength(s), in inverse microns.

    c1, c2 : float
        Intercept and slope of the linear UV component.

    c3 : float
        Bump strength. Note this is *not* the bump height; see
        :func:`trotter_extinction_bh` if you have ``BH = c3/gamma**2``
        instead.

    c4 : float
        Far-UV curvature amplitude.

    x0 : float
        Bump center, in inverse microns.

    gamma : float
        Bump width parameter.

    Returns
    -------
    float or np.ndarray
        ``k(x)``, with the same shape as ``x``.
    """
    x = np.asarray(x, dtype=np.float64)
    return c1 + c2 * x + c3 * drude(x, x0, gamma) + c4 * fm_curvature(x)


def fm_extinction(x, Av, Rv, c1, c2, c3, c4, x0, gamma):
    """
    FM88 extinction, ``A_lambda,FM = Av * [1 + k(x)/Rv]`` (Trotter Eq. 3.28;
    Reichart Eq. 60), where ``k(x)`` is :func:`fm_color_excess`.

    Parameters
    ----------
    x : float or array_like
        Inverse wavelength(s), in inverse microns.

    Av, Rv, c1, c2, c3, c4, x0, gamma : float
        See :func:`fm_color_excess` and :func:`ccm_extinction`.

    Returns
    -------
    float or np.ndarray
        ``A_lambda`` in magnitudes, with the same shape as ``x``.
    """
    if Rv == 0:
        raise ValueError("Rv must be nonzero.")
    k = fm_color_excess(x, c1, c2, c3, c4, x0, gamma)
    return Av * (1.0 + k / Rv)


# --------------------------------------------------------------------------
# The Trotter/Reichart hybrid splice (Trotter Eq. 3.29; Reichart Eq. 61)
# --------------------------------------------------------------------------
def trotter_extinction(x, Av, Rv, c1, c2, c3, c4, x0, gamma, splice="thesis"):
    """
    The full Trotter/Reichart hybrid CCM+FM source-frame extinction law,
    ``A_lambda(x)``.

    .. code-block:: text

        A_lambda,CCM(x)                                    (x < 1.82)
        A_lambda,CCM(x) * [1 + (A_FM(3.3)/A_CCM(3.3) - 1)
                             * (x - 1.82)/1.48]             (1.82 <= x <= 3.3)   [splice="thesis", default]
        A_lambda,FM(x)                                      (x > 3.3)

    or, for ``splice="reichart"``, the middle branch is instead the plain
    pointwise blend ``A_CCM(x) + (x-1.82)/1.48 * [A_FM(x) - A_CCM(x)]``. See
    the module docstring ("Splice equation") for why ``"thesis"`` is the
    default and for the equation numbers in each source.

    Parameters
    ----------
    x : float or array_like
        Inverse wavelength(s), in inverse microns. Must be finite and > 0.

    Av : float
        V-band extinction, in magnitudes. If ``Av == 0`` this returns an
        array of zeros of the appropriate shape immediately, regardless of
        the other (shape) parameters -- this is Control A of the task's
        validation plan and also sidesteps a 0/0 in the splice ratio.

    Rv : float
        ``Rv = Av / E(B-V)``. Must be nonzero.

    c1, c2 : float
        Intercept and slope of the linear FM UV component.

    c3 : float
        Bump strength (*not* bump height -- see :func:`trotter_extinction_bh`
        if you have ``BH`` instead).

    c4 : float
        Far-UV curvature amplitude.

    x0 : float
        Bump center, in inverse microns.

    gamma : float
        Bump width parameter.

    splice : {'thesis', 'reichart'}, optional, default='thesis'
        Which CCM/FM transition-zone formula to use; see above.

    Returns
    -------
    float or np.ndarray
        ``A_lambda`` in magnitudes, with the same shape as ``x``. Returns a
        Python/NumPy scalar for scalar input, an array of matching shape
        for array input (any shape, not just 1-D).

    Raises
    ------
    ValueError
        If ``x`` contains non-finite or non-positive values, if ``Rv == 0``,
        if ``splice`` is not recognized, or (only for ``splice="reichart"``,
        ``Av != 0``) if ``A_lambda,CCM(3.3) == 0`` making the
        ``splice="thesis"`` ratio ill-defined.
    """
    if splice not in ("thesis", "reichart"):
        raise ValueError(f"Unknown splice {splice!r}; expected 'thesis' or 'reichart'.")

    xa = np.asarray(x, dtype=np.float64)
    _validate_x(xa)
    _validate_finite(Av=Av, Rv=Rv, c1=c1, c2=c2, c3=c3, c4=c4, x0=x0, gamma=gamma)
    if Rv == 0:
        raise ValueError("Rv must be nonzero.")

    # Control A (Section 14): Av=0 must give exactly zero extinction
    # everywhere, regardless of the shape parameters, and this also avoids
    # a 0/0 division in the "thesis" splice ratio below.
    if Av == 0:
        result = np.zeros(xa.shape, dtype=np.float64)
        return result.item() if xa.ndim == 0 else result

    result = np.empty(xa.shape, dtype=np.float64)

    lo = xa < X_LOW
    hi = xa > X_HIGH
    mid = ~(lo | hi)

    if np.any(lo):
        result[lo] = ccm_extinction(xa[lo], Av, Rv)

    if np.any(hi):
        result[hi] = fm_extinction(xa[hi], Av, Rv, c1, c2, c3, c4, x0, gamma)

    if np.any(mid):
        xm = xa[mid]
        a_ccm_mid = ccm_extinction(xm, Av, Rv)
        w = (xm - X_LOW) / X_SPLICE_WIDTH

        if splice == "reichart":
            a_fm_mid = fm_extinction(xm, Av, Rv, c1, c2, c3, c4, x0, gamma)
            result[mid] = a_ccm_mid + w * (a_fm_mid - a_ccm_mid)
        else:  # "thesis" (default)
            a_ccm_33 = ccm_extinction(X_HIGH, Av, Rv)
            a_fm_33 = fm_extinction(X_HIGH, Av, Rv, c1, c2, c3, c4, x0, gamma)
            if a_ccm_33 == 0:
                raise ValueError(
                    "A_lambda,CCM(x=3.3) == 0 for the given Av/Rv; the "
                    "splice='thesis' ratio A_FM(3.3)/A_CCM(3.3) is "
                    "ill-defined. Use splice='reichart' or check parameters."
                )
            ratio_33 = a_fm_33 / a_ccm_33
            result[mid] = a_ccm_mid * (1.0 + (ratio_33 - 1.0) * w)

    return result.item() if xa.ndim == 0 else result


def trotter_extinction_bh(x, Av, Rv, c1, c2, BH, c4, gamma, x0, splice="thesis"):
    """
    :func:`trotter_extinction`, parameterized by bump height ``BH =
    c3/gamma**2`` instead of ``c3`` directly.

    This is the entry point that code driven by
    ``jetfit.mcmc.mcmc.TrotterDustPrior`` (which produces ``c1, Rv, BH, x0,
    gamma`` from a sampled ``c2``) should use, since that machinery works in
    bump height, not ``c3``. ``c3 = BH * gamma**2`` is reconstructed here;
    ``BH`` is *not* silently treated as ``c3`` (a likely refactor bug this
    module explicitly guards against with a regression test).

    Parameters
    ----------
    x : float or array_like
        Inverse wavelength(s), in inverse microns.

    Av, Rv, c1, c2 : float
        See :func:`trotter_extinction`.

    BH : float
        Bump height, ``BH = c3 / gamma**2``.

    c4 : float
        Far-UV curvature amplitude.

    gamma : float
        Bump width parameter. Must be finite and nonzero (needed to
        reconstruct ``c3``).

    x0 : float
        Bump center, in inverse microns.

    splice : {'thesis', 'reichart'}, optional, default='thesis'
        See :func:`trotter_extinction`.

    Returns
    -------
    float or np.ndarray
        ``A_lambda`` in magnitudes, with the same shape as ``x``.
    """
    _validate_finite(BH=BH, gamma=gamma)
    if gamma == 0:
        raise ValueError(
            "gamma must be nonzero to reconstruct c3 = BH * gamma**2."
        )
    c3 = BH * gamma**2
    return trotter_extinction(x, Av, Rv, c1, c2, c3, c4, x0, gamma, splice=splice)


# --------------------------------------------------------------------------
# Return-value conveniences (Section 10 of the task brief)
# --------------------------------------------------------------------------
def transmission(a_lambda):
    """``T_lambda = 10**(-0.4 * A_lambda)``, the fractional flux transmission."""
    return 10.0 ** (-0.4 * np.asarray(a_lambda, dtype=np.float64))


def delta_log10_flux(a_lambda):
    """``Delta log10(F_nu) = -0.4 * A_lambda = log10(T_lambda)``."""
    return -0.4 * np.asarray(a_lambda, dtype=np.float64)


# --------------------------------------------------------------------------
# dust_extinction-style adapter, for drop-in use at existing call sites
# --------------------------------------------------------------------------
class TrotterExtinction:
    """
    Thin adapter exposing :func:`trotter_extinction_bh` through the same
    ``Model(Rv=...).extinguish(x, Av=... or Ebv=...)`` calling convention
    used by ``dust_extinction.parameter_averages.CCM89`` (see
    ``jetfit.mcmc.mcmc.MCMCModels._model_extinction``), so it can be used at
    that call site with minimal disruption to the surrounding code.

    This class holds no state beyond the eight shape/normalization
    parameters; it performs no caching and is cheap to construct per call.

    Parameters
    ----------
    Rv, c1, c2, BH, gamma, x0 : float
        See :func:`trotter_extinction_bh`.

    c4 : float, optional, default=0.0
        Far-UV curvature amplitude. Defaults to zero because most existing
        parameter files in this project do not yet sample c4 (see the
        implementation report); pass it explicitly once it is added to a
        given event's parameter file.

    splice : {'thesis', 'reichart'}, optional, default='thesis'
        See :func:`trotter_extinction`.
    """

    def __init__(self, Rv, c1, c2, BH, gamma, x0, c4=0.0, splice="thesis"):
        self.Rv = Rv
        self.c1 = c1
        self.c2 = c2
        self.BH = BH
        self.gamma = gamma
        self.x0 = x0
        self.c4 = c4
        self.splice = splice

    def evaluate(self, x, Av):
        """``A_lambda`` for the given wave number(s) and ``Av``."""
        return trotter_extinction_bh(
            x, Av, self.Rv, self.c1, self.c2, self.BH, self.c4, self.gamma,
            self.x0, splice=self.splice,
        )

    def extinguish(self, x, Av=None, Ebv=None):
        """
        Fractional transmission ``T_lambda``, given either ``Av`` or
        ``Ebv`` (``Av = Rv * Ebv``), matching
        ``dust_extinction`` model instances' ``.extinguish()`` signature.
        """
        if Av is None:
            if Ebv is None:
                raise ValueError("Provide either Av or Ebv.")
            Av = self.Rv * Ebv
        elif Ebv is not None:
            raise ValueError("Provide only one of Av or Ebv, not both.")
        return transmission(self.evaluate(x, Av))


# --------------------------------------------------------------------------
# Integration glue for jetfit.mcmc.mcmc.MCMCModels.model_extinction
# --------------------------------------------------------------------------
def resolve_source_frame_transmission(
    x, ext, get_physical_dust_params,
    av_key="av_source_frame", ebv_key="ebv_source_frame",
    c4_key="c4_source_frame", splice="thesis",
):
    """
    Compute the source-frame Trotter/Reichart dust transmission for an
    event whose extinction parameters are driven by the c2-parameterized
    model, i.e. for which ``'c2' in ext``.

    This is the one piece of glue connecting this deterministic module to
    ``jetfit.mcmc.mcmc.MCMCModels.model_extinction``. It takes the already-
    implemented ``TrotterDustPrior.get_physical_dust_params`` *as a
    parameter* (dependency injection) rather than importing
    ``jetfit.mcmc.mcmc`` directly, so that (a) this module stays free of
    any dependency on the MCMC/statistics stack (which pulls in ``emcee``),
    and (b) this glue function is unit-testable in complete isolation with
    a trivial stand-in callable -- see ``test/core/test_extinction.py``.

    Why Av needs an explicit resolution step: ``TrotterDustPrior`` derives
    ``c1``, ``Rv``, bump height and bump shape from ``c2``, but *not* the
    overall normalization ``Av`` -- that is deliberately left as a free
    parameter in Trotter's model (Section 3.3.3: "the parameters Av, Rv,
    BH and c4 are all constrained to be >= 0", with Av constrained only by
    a flat prior; see also Reichart 2001 Eq. 71, which likewise recommends
    a flat prior on Av). As of this writing, no event's parameter file in
    this project defines an explicit ``av_source_frame`` (or
    ``ebv_source_frame`` alongside ``c2``) parameter for the Trotter
    branch, so calling this with such an ``ext`` will raise a clear
    ``ValueError`` rather than silently applying zero extinction. See the
    implementation report for the parameter-file changes needed to
    activate this for a given event.

    Parameters
    ----------
    x : float or array_like
        Wave number(s) (inverse microns) at which to evaluate the
        transmission, already shifted to the source frame by the caller
        (i.e. ``(1+z) * wave_numbers_observed``; this function performs no
        frame conversion of its own -- see the module docstring).

    ext : dict
        The ``'extinction'`` sub-dictionary from
        ``Parameters.samples_to_dict``. Must contain ``'c2'``.

    get_physical_dust_params : callable
        ``get_physical_dust_params(c2, ext) -> (c1, Rv, BH, x0, gamma)``.
        Intended to be
        ``jetfit.mcmc.mcmc.TrotterDustPrior.get_physical_dust_params``,
        passed in by the caller.

    av_key, ebv_key, c4_key : str, optional
        Extinction-parameter dict keys used to resolve ``Av`` and ``c4``.
        ``Av`` is taken from ``ext[av_key]`` if present, else computed as
        ``Rv * ext[ebv_key]``. ``c4`` defaults to 0.0 if ``c4_key`` is
        absent (no event currently samples a far-UV curvature parameter;
        see the implementation report).

    splice : {'thesis', 'reichart'}, optional, default='thesis'
        See :func:`trotter_extinction`.

    Returns
    -------
    float or np.ndarray
        Fractional transmission ``T_lambda``, with the same shape as ``x``.

    Raises
    ------
    KeyError
        If ``'c2'`` is not in ``ext``.

    ValueError
        If neither ``av_key`` nor ``ebv_key`` can be found in ``ext``.
    """
    c2 = ext["c2"]
    c1, rv, bh, x0, gamma = get_physical_dust_params(c2, ext)

    av = ext.get(av_key)
    if av is None:
        ebv = ext.get(ebv_key)
        if ebv is None:
            raise ValueError(
                f"Extinction parameters include 'c2' (Trotter dust model "
                f"active) but neither {av_key!r} nor {ebv_key!r} is set, "
                f"so the absolute normalization Av is undetermined. Add "
                f"one of these to this event's [[extinction]] parameters."
            )
        av = rv * ebv

    c4 = ext.get(c4_key, 0.0)

    model = TrotterExtinction(Rv=rv, c1=c1, c2=c2, BH=bh, gamma=gamma, x0=x0, c4=c4, splice=splice)
    return model.extinguish(x, Av=av)
