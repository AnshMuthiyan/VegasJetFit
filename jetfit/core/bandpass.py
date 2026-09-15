"""Photon-counting bandpass integration for calibrated photometric filters.

The response curves in this module are effective areas, not decorative
top-hat approximations.  For a photon-counting detector, a spectral flux
density ``F_nu`` produces a count rate proportional to

    integral F_nu(lambda) A_eff(lambda) / lambda dlambda.

Normalizing by the same integral for constant ``F_nu`` returns an
AB-equivalent band-averaged flux density in the same units as ``F_nu``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.io.votable import parse_single_table


C_ANGSTROM_PER_SECOND = 2.99792458e18


@dataclass(frozen=True)
class Bandpass:
    """A photon-counting effective-area curve and normalized quadrature."""

    canonical_name: str
    wavelength_angstrom: np.ndarray
    effective_area_cm2: np.ndarray
    source_file: Path

    def __post_init__(self):
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
        """Load wavelength bins and ``SPECRESP`` from an OGIP ARF."""
        path = Path(path)
        with fits.open(path, memmap=False) as hdus:
            table = hdus[1]
            names = set(table.data.names)
            required = {"WAVE_MIN", "WAVE_MAX", "SPECRESP"}
            if not required.issubset(names):
                raise ValueError(f"{path} is missing OGIP columns {sorted(required - names)}")
            wavelength = 0.5 * (
                np.asarray(table.data["WAVE_MIN"], dtype=float)
                + np.asarray(table.data["WAVE_MAX"], dtype=float)
            )
            area = np.asarray(table.data["SPECRESP"], dtype=float)
            filter_name = str(table.header.get("FILTER", path.stem)).strip().lower()
        return cls(canonical_name or filter_name, wavelength, area, path)

    @classmethod
    def from_svo_votable(cls, path: str | Path, canonical_name: str):
        """Load a total-system throughput from an archived SVO FPS response."""
        path = Path(path)
        table = parse_single_table(path).array
        names = set(table.dtype.names or ())
        required = {"Wavelength", "Transmission"}
        if not required.issubset(names):
            raise ValueError(f"{path} is missing SVO columns {sorted(required - names)}")
        return cls(
            canonical_name,
            np.asarray(table["Wavelength"], dtype=float),
            np.asarray(table["Transmission"], dtype=float),
            path,
        )

    @property
    def frequency_hz(self):
        return C_ANGSTROM_PER_SECOND / self.wavelength_angstrom

    @property
    def pivot_wavelength_angstrom(self):
        """Photon-counting pivot wavelength for the supplied effective area."""
        wavelength = self.wavelength_angstrom
        area = self.effective_area_cm2
        numerator = np.trapezoid(area * wavelength, wavelength)
        denominator = np.trapezoid(area / wavelength, wavelength)
        return float(np.sqrt(numerator / denominator))

    def photon_quadrature(self, max_nodes: int | None = None):
        """Return wavelengths and normalized ``A_eff/lambda`` integration weights.

        If ``max_nodes`` is supplied, adjacent response-weight quantiles are
        compressed to weighted-mean wavelengths. This preserves constant
        ``F_nu`` exactly while reducing repeated afterglow evaluations.
        """
        wavelength = self.wavelength_angstrom
        area = self.effective_area_cm2
        delta = np.empty_like(wavelength)
        delta[0] = 0.5 * (wavelength[1] - wavelength[0])
        delta[-1] = 0.5 * (wavelength[-1] - wavelength[-2])
        delta[1:-1] = 0.5 * (wavelength[2:] - wavelength[:-2])
        weight = area * delta / wavelength
        keep = weight > 0.0
        wavelength = wavelength[keep]
        weight = weight[keep]
        weight /= weight.sum()

        if max_nodes is None or max_nodes >= weight.size:
            return wavelength.copy(), weight.copy()
        if max_nodes < 2:
            raise ValueError("Bandpass quadrature requires at least two nodes.")

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

    def integrate_fnu(self, fnu, max_nodes: int | None = None):
        """Integrate values sampled at :meth:`photon_quadrature` nodes."""
        _, weights = self.photon_quadrature(max_nodes=max_nodes)
        values = np.asarray(fnu, dtype=float)
        if values.shape[-1] != weights.size:
            raise ValueError(
                f"Expected final F_nu dimension {weights.size}, got {values.shape[-1]}."
            )
        return np.sum(values * weights, axis=-1)


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


@lru_cache(maxsize=None)
def get_bandpass(name: str) -> Bandpass | None:
    """Return a verified bandpass or ``None`` for an unmapped label.

    Deliberately do not map generic ``U/B/V`` labels to UVOT. Those labels in
    the campaign combine multiple instruments and cannot be assigned a unique
    response without additional provenance.
    """
    canonical = _ALIASES.get(str(name).strip().lower())
    if canonical is None:
        return None
    if canonical in _UVOT_FILES:
        return Bandpass.from_ogip_arf(
            _UVOT_RESOURCE_DIR / _UVOT_FILES[canonical], canonical
        )
    return Bandpass.from_svo_votable(
        _HST_RESOURCE_DIR / _HST_FILES[canonical], canonical
    )


def available_bandpasses():
    """Return the filter labels recognized in campaign observation files."""
    return ('F125W', 'F775W', 'uvm2', 'uvot-b', 'uvot-u', 'uvot-v', 'uvw1', 'uvw2')
