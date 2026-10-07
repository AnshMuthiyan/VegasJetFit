"""Band integration through calibrated photometric response curves.

What a response curve MEANS decides how it is integrated (2026-10 team
decision: "the response function and its provenance determine how it should
be used"). Every :class:`Bandpass` therefore records, from the provenance of
its file, which detector convention its tabulated values follow, and the
band-averaging measure is derived from that -- curves are NOT all forced into
one formula, and they are stored exactly as published.

Model fluxes are F_nu [mJy] at observer-frame wavelength lambda [A]. The
band-averaged model flux is the AB-equivalent mean: the constant F_nu that
would produce the same detector signal as the actual spectrum,

    <F_nu> = integral F_nu(lambda) m(lambda) dlambda / integral m(lambda) dlambda,

with the measure m(lambda) set by the response convention:

``"photon"`` -- a photon-counting response R(lambda) (quantum-efficiency x
    throughput, or an effective area that maps PHOTON flux to counts). The
    count rate is C ~ integral F_lambda R lambda/(hc) dlambda; with
    F_lambda = F_nu c / lambda^2 this is C ~ (1/h) integral F_nu R dlambda/lambda,
    so m = R / lambda  (equivalently R dnu / nu). 1/h and c cancel in the ratio.

``"energy"`` -- an energy-counting ("energy integrating") response T(lambda):
    signal ~ integral F_lambda T dlambda = integral F_nu T c/lambda^2 dlambda,
    so m = T / lambda^2  (equivalently T dnu: a frequency-uniform average --
    the form of Trotter 2011 Eq. 3.47). Curves published this way already
    carry one extra factor of lambda relative to the photon response of the
    same system (e.g. Bessell 1990 UBVRI as served by SVO with
    ``DetectorType = 0``); applying the photon measure to them, or dividing
    them by lambda AND applying the energy measure, would each be wrong.

``"unknown"`` -- the file does not say. Such a curve is kept (with its
    provenance) but refuses to integrate until the convention is stated;
    no convention is invented.

The overall normalization of a response never matters (the measure is
normalized). Attenuation (dust, H I, Milky Way) is NOT applied here: callers
multiply the model spectrum by the wavelength-dependent attenuation at the
quadrature nodes and then form the weighted sum (see
``jetfit.mcmc.mcmc.MCMCModels.integrate_spectral_bandpass``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.io.votable import parse_single_table


C_ANGSTROM_PER_SECOND = 2.99792458e18

RESPONSE_CONVENTIONS = ("photon", "energy", "unknown")
# SVO Filter Profile Service ``DetectorType`` PARAM: "0: Energy counter,
# 1: Photon counter".
_SVO_DETECTOR_TYPES = {"0": "energy", "1": "photon"}


@dataclass(frozen=True)
class Bandpass:
    """A tabulated detector response curve, its provenance and its measure.

    ``effective_area_cm2`` holds the response values exactly as published:
    an effective area in cm^2 for OGIP ARFs, a dimensionless throughput for
    SVO curves. ``response_convention`` says what they represent (module
    docstring); loaders set it from the file's provenance. Constructing a
    ``Bandpass`` directly defaults to ``"photon"`` -- pass the convention
    explicitly whenever the curve is not a photon-counting response.
    """

    canonical_name: str
    wavelength_angstrom: np.ndarray
    effective_area_cm2: np.ndarray
    source_file: Path
    # How the tabulated values sample the response (2026-09-25 audit):
    # "points" -- values at the listed wavelengths (SVO VOTables); the end
    #             points own half a cell, as in the trapezoid rule.
    # "bins"   -- each value is the average over a contiguous bin centred on
    #             the listed wavelength (OGIP ARF WAVE_MIN..WAVE_MAX); every
    #             bin, including the first and last, owns its full width.
    tabulation: str = "points"
    # What the values represent -> which measure integrates them (module doc).
    response_convention: str = "photon"
    # Human-readable statement of where the convention came from.
    convention_basis: str = "constructed directly (photon-counting assumed by the caller)"

    def __post_init__(self):
        if self.tabulation not in ("points", "bins"):
            raise ValueError("Bandpass tabulation must be 'points' or 'bins'.")
        if self.response_convention not in RESPONSE_CONVENTIONS:
            raise ValueError(
                f"Bandpass response_convention must be one of {RESPONSE_CONVENTIONS}."
            )
        wavelength = np.asarray(self.wavelength_angstrom, dtype=float)
        area = np.asarray(self.effective_area_cm2, dtype=float)
        if wavelength.ndim != 1 or area.shape != wavelength.shape:
            raise ValueError("Bandpass wavelength and effective area must be matching 1-D arrays.")
        finite = np.isfinite(wavelength) & np.isfinite(area)
        if not finite.all() or np.any(wavelength <= 0.0) or np.any(area < 0.0):
            raise ValueError("Bandpass contains invalid wavelength or effective-area values.")
        order = np.argsort(wavelength)
        wavelength = wavelength[order]
        area = area[order]
        if np.any(np.diff(wavelength) <= 0.0) or not np.any(area > 0.0):
            raise ValueError("Bandpass wavelengths must be unique and response must be nonzero.")
        wavelength.setflags(write=False)
        area.setflags(write=False)
        object.__setattr__(self, "wavelength_angstrom", wavelength)
        object.__setattr__(self, "effective_area_cm2", area)

    @classmethod
    def from_ogip_arf(cls, path: str | Path, canonical_name: str | None = None):
        """Load wavelength bins and ``SPECRESP`` from an OGIP ARF.

        Convention: ``"photon"``. By the OGIP definition (CAL/GEN/92-002) an
        ARF's ``SPECRESP`` [cm^2] is the effective area that converts a PHOTON
        flux density into detected counts, i.e. a photon-counting response;
        Swift/UVOT is a photon-counting instrument. It carries no extra
        lambda factor, so the photon measure A/lambda applies directly.
        """
        path = Path(path)
        with fits.open(path, memmap=False) as hdus:
            table = hdus[1]
            names = set(table.data.names)
            required = {"WAVE_MIN", "WAVE_MAX", "SPECRESP"}
            if not required.issubset(names):
                raise ValueError(f"{path} is missing OGIP columns {sorted(required - names)}")
            edge_a = np.asarray(table.data["WAVE_MIN"], dtype=float)
            edge_b = np.asarray(table.data["WAVE_MAX"], dtype=float)
            wavelength = 0.5 * (edge_a + edge_b)
            area = np.asarray(table.data["SPECRESP"], dtype=float)
            filter_name = str(table.header.get("FILTER", path.stem)).strip().lower()
        # Swift/UVOT ARFs list bins in energy order, so WAVE_MIN holds each
        # bin's LONGER wavelength; order the edges explicitly. The "bins"
        # quadrature assumes contiguous bins whose widths equal the spacing of
        # their centres -- check it rather than assume it.
        lo, hi = np.minimum(edge_a, edge_b), np.maximum(edge_a, edge_b)
        order = np.argsort(wavelength)
        lo, hi = lo[order], hi[order]
        if lo.size > 1 and not (
            np.allclose(lo[1:], hi[:-1], rtol=0.0, atol=1e-6 * float(hi[-1]))
            and np.allclose(hi - lo, (hi - lo)[0], rtol=1e-6)
        ):
            raise ValueError(f"{path}: ARF bins are not contiguous and uniform.")
        # JETFIT_BANDPASS_ARF_EDGES=half restores the earlier treatment (edge
        # bins at half width) to reproduce pre-2026-09-25 runs exactly. Read
        # when the file is loaded; get_bandpass caches the result.
        edges = os.environ.get("JETFIT_BANDPASS_ARF_EDGES", "full").strip().lower()
        if edges not in ("full", "half"):
            raise ValueError("JETFIT_BANDPASS_ARF_EDGES must be 'full' or 'half'.")
        return cls(canonical_name or filter_name, wavelength, area, path,
                   tabulation="bins" if edges == "full" else "points",
                   response_convention="photon",
                   convention_basis="OGIP ARF SPECRESP: photon-counting effective area")

    @classmethod
    def from_svo_votable(
        cls,
        path: str | Path,
        canonical_name: str,
        response_convention: str | None = None,
    ):
        """Load a response curve, exactly as published, from an SVO FPS VOTable.

        SVO tags each curve with a ``DetectorType`` PARAM ("0: Energy counter,
        1: Photon counter"); that tag is the provenance of the convention:

        * ``response_convention=None`` (default): follow the tag -- ``1`` ->
          ``"photon"``, ``0`` -> ``"energy"``; no tag -> ``"unknown"`` (the
          curve loads but refuses to integrate; nothing is assumed).
        * an explicit value: used when the file has no tag, and cross-checked
          against the tag when it has one -- a contradiction raises rather
          than silently integrating with the wrong measure.

        The values are NOT rescaled: an energy-counter curve (e.g. Bessell
        1990 as served by SVO) is integrated with the energy measure, which is
        algebraically identical to dividing it by lambda and using the photon
        measure (see ``jetfit.core.bessell_convention``).
        """
        path = Path(path)
        detector_type = _svo_detector_type(path)
        tagged = _SVO_DETECTOR_TYPES.get(detector_type)
        if response_convention is not None and response_convention not in RESPONSE_CONVENTIONS:
            raise ValueError(f"response_convention must be one of {RESPONSE_CONVENTIONS}.")
        if response_convention is None:
            convention = tagged or "unknown"
            basis = (f"SVO DetectorType={detector_type}" if tagged
                     else "no SVO DetectorType tag in the file: convention unknown")
        elif tagged is not None and response_convention != tagged:
            raise ValueError(
                f"{path}: response_convention={response_convention!r} contradicts the "
                f"file's SVO DetectorType={detector_type!r} (0: energy counter, "
                "1: photon counter)."
            )
        else:
            convention = response_convention
            basis = (f"SVO DetectorType={detector_type} (matches the stated convention)"
                     if tagged else f"stated by caller ({response_convention}); file has no tag")
        table = parse_single_table(path).array
        names = set(table.dtype.names or ())
        required = {"Wavelength", "Transmission"}
        if not required.issubset(names):
            raise ValueError(f"{path} is missing SVO columns {sorted(required - names)}")
        wavelength = np.asarray(table["Wavelength"], dtype=float)
        response = np.asarray(table["Transmission"], dtype=float)
        return cls(canonical_name, wavelength, response, path,
                   response_convention=convention, convention_basis=basis)

    @property
    def frequency_hz(self):
        return C_ANGSTROM_PER_SECOND / self.wavelength_angstrom

    @property
    def pivot_wavelength_angstrom(self):
        """Pivot wavelength of the response under its own convention.

        lambda_p^2 = integral m lambda^2 dlambda / integral m dlambda with the
        measure m of the module docstring: integral R lambda / integral R/lambda
        for a photon counter, integral T / integral T/lambda^2 for an energy
        counter (the standard definitions, e.g. SVO FPS).
        """
        wavelength = self.wavelength_angstrom
        area = self.effective_area_cm2
        self._require_known_convention()
        if self.response_convention == "photon":
            numerator = np.trapezoid(area * wavelength, wavelength)
            denominator = np.trapezoid(area / wavelength, wavelength)
        else:
            numerator = np.trapezoid(area, wavelength)
            denominator = np.trapezoid(area / wavelength ** 2, wavelength)
        return float(np.sqrt(numerator / denominator))

    def _require_known_convention(self):
        if self.response_convention == "unknown":
            raise ValueError(
                f"{self.canonical_name}: response convention unknown "
                f"({self.convention_basis}); state it explicitly before integrating."
            )

    def _measure_weights(self):
        """Unnormalized quadrature weights m(lambda_i) * dlambda_i (module doc)."""
        self._require_known_convention()
        wavelength = self.wavelength_angstrom
        weight = self.effective_area_cm2 * self._cell_widths() / wavelength
        if self.response_convention == "energy":
            weight = weight / wavelength
        return weight

    def quadrature(self, max_nodes: int | None = None):
        """Return wavelengths and normalized band-averaging weights.

        The weights are the response convention's measure (module docstring)
        times the cell widths, normalized to sum to 1, so ``sum(F_nu * w)`` is
        the AB-equivalent band-averaged F_nu. If ``max_nodes`` is supplied,
        adjacent weight quantiles are compressed to weighted-mean wavelengths
        (preserves constant F_nu exactly).
        """
        wavelength = self.wavelength_angstrom
        weight = self._measure_weights()
        keep = weight > 0.0
        wavelength = wavelength[keep]
        weight = weight[keep]
        weight /= weight.sum()

        if max_nodes is None or max_nodes >= weight.size:
            return wavelength.copy(), weight.copy()
        return quantile_nodes(wavelength, weight, max_nodes, normalize=False)

    def photon_quadrature(self, max_nodes: int | None = None):
        """Backward-compatible name of :meth:`quadrature`.

        Kept because existing code and tests call it. For a photon-counting
        curve the weights are the photon measure A/lambda; for an energy-
        counting curve they are the energy measure T/lambda^2 -- the name
        predates the per-curve convention.
        """
        return self.quadrature(max_nodes)

    def _cell_widths(self):
        """Width [A] of the wavelength cell each tabulated value represents.

        Interior cells reach half-way to each neighbour. The first and last
        cells are half-cells for point samples ("points", trapezoid-like) but
        full bins for bin averages ("bins", OGIP ARFs) -- an ARF's edge bins
        cover their whole WAVE_MIN..WAVE_MAX range like every other bin.
        """
        wavelength = self.wavelength_angstrom
        delta = np.empty_like(wavelength)
        delta[1:-1] = 0.5 * (wavelength[2:] - wavelength[:-2])
        edge = 1.0 if self.tabulation == "bins" else 0.5
        delta[0] = edge * (wavelength[1] - wavelength[0])
        delta[-1] = edge * (wavelength[-1] - wavelength[-2])
        return delta

    def _cell_edges(self):
        """Lower and upper edge [A] of every tabulated cell (see _cell_widths)."""
        wavelength = self.wavelength_angstrom
        half = 0.5 * np.diff(wavelength)
        outer = (half[0], half[-1]) if self.tabulation == "bins" else (0.0, 0.0)
        lower = wavelength - np.concatenate(([outer[0]], half))
        upper = wavelength + np.concatenate((half, [outer[1]]))
        return lower, upper

    def quadrature_cells(self):
        """Full-resolution quadrature nodes with their cell boundaries.

        Returns ``(wavelength, weight, lower, upper)`` where ``wavelength`` and
        ``weight`` are exactly ``quadrature(None)`` and each node owns the cell
        ``[lower, upper]`` implied by that rule (half-way to each neighbour; at
        the two ends, a half cell for point samples or the full bin for bin
        averages -- see :meth:`_cell_widths`). The response is treated as
        constant across a cell, as the midpoint rule already assumes.
        """
        lower, upper = self._cell_edges()
        keep = self._measure_weights() > 0.0
        nodes, weight = self.quadrature(None)
        return nodes, weight, lower[keep].copy(), upper[keep].copy()

    def photon_cells(self):
        """Backward-compatible name of :meth:`quadrature_cells`."""
        return self.quadrature_cells()

    def support_angstrom(self):
        """(blue, red) edges [A] of the response's nonzero support.

        Taken from the cells the quadrature actually integrates, so a bin (or
        point cell) with any nonzero response counts in full -- no tail is
        clipped.
        """
        lower, upper = self._cell_edges()
        nonzero = self.effective_area_cm2 > 0.0
        return float(lower[nonzero].min()), float(upper[nonzero].max())

    def integrate_fnu(self, fnu, max_nodes: int | None = None):
        """Integrate values sampled at :meth:`quadrature` nodes."""
        _, weights = self.quadrature(max_nodes=max_nodes)
        values = np.asarray(fnu, dtype=float)
        if values.shape[-1] != weights.size:
            raise ValueError(
                f"Expected final F_nu dimension {weights.size}, got {values.shape[-1]}."
            )
        return np.sum(values * weights, axis=-1)


def _svo_detector_type(path) -> str | None:
    """Return the SVO FPS ``DetectorType`` PARAM value ("0"/"1") or ``None``.

    Read with the standard library rather than astropy so the result does
    not depend on astropy's PARAM value types across versions. Missing file,
    unparsable XML, or no such PARAM all return ``None`` (no tag to check).
    """
    import xml.etree.ElementTree as ET

    try:
        root = ET.parse(str(path)).getroot()
    except (OSError, ET.ParseError):
        return None
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == "PARAM" and element.get("name") == "DetectorType":
            value = (element.get("value") or "").strip()
            return value or None
    return None


def quantile_nodes(wavelength, weight, max_nodes, normalize=True):
    """Compress ``(wavelength, weight)`` to ``max_nodes`` equal-weight nodes.

    Adjacent weight quantiles are replaced by their weighted-mean wavelength,
    each carrying 1/max_nodes of the total weight. ``weight`` need not be
    normalized. This is the compression :meth:`Bandpass.photon_quadrature`
    applies to the response; bandpass integration also applies it to the
    response weight times the attenuation, so nodes sit where the transmitted
    photons are. normalize=False is for weights that already sum to 1
    (keeps photon_quadrature's result bit-identical to its earlier form).
    """
    if max_nodes < 2:
        raise ValueError("Bandpass quadrature requires at least two nodes.")
    wavelength = np.asarray(wavelength, dtype=float)
    weight = np.asarray(weight, dtype=float)
    if normalize:
        weight = weight / weight.sum()
    cumulative = np.concatenate(([0.0], np.cumsum(weight)))
    edges = np.linspace(0.0, 1.0, int(max_nodes) + 1)
    node_wavelength = []
    node_weight = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (cumulative[1:] > lo) & (cumulative[:-1] < hi)
        if not np.any(mask):
            continue
        clipped = np.minimum(cumulative[1:][mask], hi) - np.maximum(
            cumulative[:-1][mask], lo
        )
        local_weight = clipped / clipped.sum()
        node_wavelength.append(float(np.sum(local_weight * wavelength[mask])))
        node_weight.append(float(hi - lo))
    weights = np.asarray(node_weight, dtype=float)
    weights /= weights.sum()
    return np.asarray(node_wavelength, dtype=float), weights


def refine_photon_cells(wavelength, weight, lower, upper, refine, breakpoints=(),
                        subdivisions=8):
    """Split selected quadrature cells into sub-cells.

    Each selected cell ``[lower, upper]`` is cut at any ``breakpoints`` strictly
    inside it and every piece is divided into ``subdivisions`` equal
    sub-intervals. Sub-cell weights share the cell's weight in proportion to
    ``integral dlambda / lambda`` over each sub-interval (the response is
    constant within a cell), so every cell's total photon weight -- and hence
    the normalization -- is preserved exactly. Unselected cells are returned
    unchanged, in order. Nodes sit at sub-interval midpoints.
    """
    wavelength = np.asarray(wavelength, dtype=float)
    weight = np.asarray(weight, dtype=float)
    refine = np.asarray(refine, dtype=bool)
    if not np.any(refine):
        return wavelength, weight
    breakpoints = np.sort(np.asarray(breakpoints, dtype=float))
    out_wl, out_w = [], []
    for wl, w, lo, hi, split in zip(wavelength, weight, lower, upper, refine):
        if not split or hi <= lo:
            out_wl.append([wl])
            out_w.append([w])
            continue
        cuts = np.concatenate(([lo], breakpoints[(breakpoints > lo) & (breakpoints < hi)], [hi]))
        edges = np.concatenate([
            np.linspace(a, b, subdivisions + 1)[:-1] for a, b in zip(cuts[:-1], cuts[1:])
        ] + [[hi]])
        log_width = np.log(edges[1:] / edges[:-1])
        out_wl.append(0.5 * (edges[1:] + edges[:-1]))
        out_w.append(w * log_width / log_width.sum())
    return np.concatenate(out_wl), np.concatenate(out_w)


# Rest-frame inverse-microns boundary at which the dust law's UV structure
# (and, further blueward, Ly-alpha-forest/Lyman-limit structure) becomes
# significant enough that a single central-wavelength evaluation is no
# longer a safe stand-in for integrating the full filter response. Per the
# 2026-09-22 filter-integration sync: "the magic spot...was 3.3 inverse
# microns...if a filter function crosses 3.3 inverse microns, we're going to
# want to integrate it. If it's all on the lower side, then we won't."
#
# This is a distinct physical boundary from Ly-alpha (1215.67 A) and the
# Lyman limit (911.8 A) -- do not conflate the three. See
# ``jetfit.core.hydrogen_absorption`` for those.
X_INTEGRATION_THRESHOLD_INV_MICRON = 3.3

ANGSTROM_PER_MICRON = 1.0e4


def requires_bandpass_integration(
    response: "Bandpass",
    redshift,
    x_threshold: float = X_INTEGRATION_THRESHOLD_INV_MICRON,
) -> bool:
    """Return whether ``response`` crosses ``x_threshold`` at ``redshift``.

    A fixed observed-frame filter maps to a different source-frame
    wavenumber range for every burst redshift,
    ``x_rest = (1 + z) / lambda_obs[micron]`` -- the same mapping used for
    source-frame dust attenuation in ``MCMCModels._node_source_attenuation``.
    The filter needs integration when ANY part of its actual response lies at
    ``x_rest >= x_threshold``: this includes a filter lying entirely on the
    high-frequency side, and a filter that reaches the boundary only through
    a faint tail (2026-10 team decision: integrate wherever the response
    crosses; no fractional-response threshold; do not clip tails to avoid
    integration). "Any part" is judged on the cells the quadrature integrates
    (:meth:`Bandpass.support_angstrom`), i.e. the blue edge of the bluest
    cell with nonzero response, not its centre. A filter lying entirely
    redward of the boundary (``x_rest < x_threshold`` everywhere) does not
    require integration.
    """
    blue_edge, _ = response.support_angstrom()
    x_max = (1.0 + float(redshift)) * ANGSTROM_PER_MICRON / blue_edge
    return bool(x_max >= x_threshold)


_FILTER_RESOURCE_DIR = Path(__file__).resolve().parents[1] / "resources" / "filters"
_UVOT_RESOURCE_DIR = _FILTER_RESOURCE_DIR / "swift_uvot"
_HST_RESOURCE_DIR = _FILTER_RESOURCE_DIR / "hst_wfc3"

_UVOT_FILES = {
    "uvot-v": "swuvv_20041120v104.arf",
    "uvot-b": "swubb_20041120v104.arf",
    "uvot-u": "swuuu_20041120v104.arf",
    "uvw1": "swuw1_20041120v106.arf",
    "uvm2": "swum2_20041120v105.arf",
    "uvw2": "swuw2_20041120v105.arf",
}

_ALIASES = {
    "uvot-v": "uvot-v",
    "uvot-b": "uvot-b",
    "uvot-u": "uvot-u",
    "uvw1": "uvw1",
    "uvm2": "uvm2",
    "uvw2": "uvw2",
    "f775w": "hst-wfc3-uvis2-f775w",
    "f125w": "hst-wfc3-ir-f125w",
    "hst-wfc3-uvis2-f775w": "hst-wfc3-uvis2-f775w",
    "hst-wfc3-ir-f125w": "hst-wfc3-ir-f125w",
}

_HST_FILES = {
    "hst-wfc3-uvis2-f775w": "HST_WFC3_UVIS2_F775W.xml",
    "hst-wfc3-ir-f125w": "HST_WFC3_IR_F125W.xml",
}

# --- 2026-09-25 filter-integration audit: SDSS / Bessell / UVOT-White slots ---
#
# These three filter families are explicitly called for by Sections 3 and 13
# of the filter-integration task but this audit could NOT source real,
# numeric response-curve files for them: this sandbox's network egress
# blocks every science-data host tried (SVO Filter Profile Service,
# HEASARC/Swift CALDB), confirmed by direct connection test, not assumed --
# see RESPONSE_CURVE_PROVENANCE.md for exactly what to fetch and from where.
#
# Rather than fabricate curve data (which Section 0/Rule 2 explicitly
# forbid) or wire in files that don't exist (which would raise a confusing
# error deep inside astropy on first use), this registers the aliases and
# expected filenames now -- get_bandpass returns None for these, exactly
# like an unmapped label, until the real file is dropped in at the path
# below. No code changes are needed at that point.
_SDSS_RESOURCE_DIR = _FILTER_RESOURCE_DIR / "sdss"
_BESSELL_RESOURCE_DIR = _FILTER_RESOURCE_DIR / "bessell"

_SDSS_FILES = {
    "sdss-u": "SLOAN_SDSS.u.xml",
    "sdss-g": "SLOAN_SDSS.g.xml",
    "sdss-r": "SLOAN_SDSS.r.xml",
    "sdss-i": "SLOAN_SDSS.i.xml",
    "sdss-z": "SLOAN_SDSS.z.xml",
}
# Bessell (1990) UBVRI, served by SVO FPS as Generic/Bessell.<band> (tagged
# DetectorType=0, energy counter) -- loaded with response_convention="energy",
# which from_svo_votable cross-checks against that tag, and integrated with
# the energy-counter measure T/lambda^2 (see the module docstring and
# jetfit/core/bessell_convention.py for why that is the right measure). Note: SVO's
# Bessell.U is Bessell's "UX", which INCLUDES atmospheric extinction (1.0
# air mass at 2.5 km); Bessell (1990, Sec. 9) says UX and BX are for (U-B)
# colors and B, V, R, I for other colors and magnitudes. See
# RESPONSE_CURVE_PROVENANCE.md before using bessell-u.
_BESSELL_FILES = {
    "bessell-u": "Generic_Bessell.U.xml",
    "bessell-b": "Generic_Bessell.B.xml",
    "bessell-v": "Generic_Bessell.V.xml",
    "bessell-r": "Generic_Bessell.R.xml",
    "bessell-i": "Generic_Bessell.I.xml",
}
# Swift/UVOT White: listed in the HEASARC Swift/UVOTA CALDB index
# (cif_swift_uvota_20170130) as swuwh_20041120v104.arf, "WHITE FILTER SPECTRAL
# RESPONSE" -- the same 20041120/v104 family as the bundled V, B and U files.
# Whether it is still the latest CAL_QUAL=0 file was NOT re-checked (2026-09-25
# audit); check the current index when fetching. No observation file in the
# repository contains UVOT White data (label "W" in 080319B is a 97 GHz radio
# channel), so this slot is inert: get_bandpass returns None until the file
# exists.
_UVOT_WHITE_FILES = {
    "uvot-white": "swuwh_20041120v104.arf",
}

_ALIASES.update({
    "sdss-u": "sdss-u", "sdss-g": "sdss-g", "sdss-r": "sdss-r",
    "sdss-i": "sdss-i", "sdss-z": "sdss-z",
    "bessell-u": "bessell-u", "bessell-b": "bessell-b", "bessell-v": "bessell-v",
    "bessell-r": "bessell-r", "bessell-i": "bessell-i",
    "uvot-white": "uvot-white",
})


@lru_cache(maxsize=None)
def get_bandpass(name: str) -> Bandpass | None:
    """Return a verified bandpass or ``None`` for an unmapped label.

    Deliberately do not map generic ``U/B/V`` labels to UVOT. Those labels in
    the campaign combine multiple instruments and cannot be assigned a unique
    response without additional provenance.

    SDSS/Bessell/UVOT-White are registered but return ``None`` until their
    real response-curve files are added under ``resources/filters/`` (see
    ``RESPONSE_CURVE_PROVENANCE.md``) -- unlike the UVOT/HST branches below,
    whose bundled files are always expected to be present, so a missing file
    there still raises loudly rather than silently returning ``None``.
    """
    canonical = _ALIASES.get(str(name).strip().lower())
    if canonical is None:
        return None
    if canonical in _UVOT_FILES:
        return Bandpass.from_ogip_arf(
            _UVOT_RESOURCE_DIR / _UVOT_FILES[canonical], canonical
        )
    if canonical in _HST_FILES:
        return Bandpass.from_svo_votable(
            _HST_RESOURCE_DIR / _HST_FILES[canonical], canonical
        )
    if canonical in _SDSS_FILES:
        # Convention follows the file's SVO DetectorType tag (not yet
        # confirmed for SDSS: no SDSS file has been available to inspect). An
        # untagged file loads as "unknown" and refuses to integrate.
        path = _SDSS_RESOURCE_DIR / _SDSS_FILES[canonical]
        return Bandpass.from_svo_votable(path, canonical) if path.exists() else None
    if canonical in _BESSELL_FILES:
        path = _BESSELL_RESOURCE_DIR / _BESSELL_FILES[canonical]
        return (
            Bandpass.from_svo_votable(path, canonical, response_convention="energy")
            if path.exists() else None
        )
    if canonical in _UVOT_WHITE_FILES:
        path = _UVOT_RESOURCE_DIR / _UVOT_WHITE_FILES[canonical]
        return Bandpass.from_ogip_arf(path, canonical) if path.exists() else None
    return None


def response_source(name: str) -> dict:
    """Say which kind of response a label would use, without loading it.

    ``kind`` is one of:

    * ``"instrument"`` -- the actual instrument response (Swift/UVOT CALDB
      ARFs, HST/WFC3 SVO curves; UVOT White once its file exists);
    * ``"canonical_system"`` -- a documented standard-system passband
      (SDSS 2.5 m, Bessell 1990) for a label that explicitly names that
      system (``sdss-r``, ``bessell-v``) and whose file exists;
    * ``"monochromatic"`` -- no response is used; the row is evaluated at its
      catalogue frequency. ``reason`` says why.

    When a file is used, ``response_convention`` ("photon", "energy" or
    "unknown") and ``convention_basis`` record what the curve represents and
    where that came from (module docstring).

    Generic labels (``r``, ``R``, ``Ic``, ``J`` ...) are deliberately NOT mapped
    to a canonical system: the observing instrument is not recorded in the
    data, and assigning one would invent provenance. This mirrors
    :func:`get_bandpass`, which returns ``None`` exactly when ``kind`` is
    ``"monochromatic"``.
    """
    canonical = _ALIASES.get(str(name).strip().lower())
    if canonical is None:
        return {
            "kind": "monochromatic",
            "reason": "no response registered for this label "
                      "(instrument not recorded in the data)",
        }
    families = (
        (_UVOT_FILES, _UVOT_RESOURCE_DIR, "instrument"),
        (_HST_FILES, _HST_RESOURCE_DIR, "instrument"),
        (_UVOT_WHITE_FILES, _UVOT_RESOURCE_DIR, "instrument"),
        (_SDSS_FILES, _SDSS_RESOURCE_DIR, "canonical_system"),
        (_BESSELL_FILES, _BESSELL_RESOURCE_DIR, "canonical_system"),
    )
    for files, directory, kind in families:
        if canonical in files:
            path = directory / files[canonical]
            if not path.exists():
                return {
                    "kind": "monochromatic",
                    "canonical_name": canonical,
                    "reason": f"registered response file {files[canonical]} is absent",
                }
            band = get_bandpass(name)
            return {"kind": kind, "canonical_name": canonical, "file": path.name,
                    "response_convention": band.response_convention,
                    "convention_basis": band.convention_basis}
    return {"kind": "monochromatic", "reason": "label not mapped to a response file"}


def available_bandpasses():
    """Return the filter labels recognized in campaign observation files."""
    return ('F125W', 'F775W', 'uvm2', 'uvot-b', 'uvot-u', 'uvot-v', 'uvw1', 'uvw2')
