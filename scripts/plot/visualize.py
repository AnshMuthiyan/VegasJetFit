import gc
import os
import csv
import json
from pathlib import Path

import numpy as np
from astropy import units as u
import matplotlib

matplotlib.use('Agg', force=True)
from matplotlib import pyplot as plt
from synphot import SpectralElement

from jetfit.core.structs import DataType
from jetfit.core.utils import (
    save_plot_unique,
    days_to_sec,
    sec_to_days,
    apply_plot_run_label,
    apply_plot_title,
    add_collision_aware_grb_label,
)
from jetfit.models.base import BlastWaveModel, DAY2SEC, has_fts_transition, RadiationModel, SpectralIndexModel
from jetfit.models.fireball import StratifiedFireballModel
from jetfit.models.jet_energy import resolve_e_iso52, resolve_gamma0_axis
from jetfit.models.jetsim import JetSimpy
from scripts.plot.base import OPTION_MAP, Profiler
from scripts.plot.histogram import SpectralIndexPlot

EFF_WL = {
    'U': SpectralElement.from_filter('johnson_u').pivot(),
    'B': SpectralElement.from_filter('johnson_b').pivot(),
    'V': SpectralElement.from_filter('johnson_v').pivot(),
    'R': SpectralElement.from_filter('johnson_r').pivot(),  # 6899 AA
    'I': SpectralElement.from_filter('johnson_i').pivot(),
    'J': SpectralElement.from_filter('bessel_j').pivot(),
    'H': SpectralElement.from_filter('bessel_h').pivot(),
    'K': SpectralElement.from_filter('bessel_k').pivot(),
    'Rc': SpectralElement.from_filter('cousins_r').pivot(),
    'Ic': SpectralElement.from_filter('cousins_i').pivot(),

    # SDSS
    'u' : u.Quantity(3540.0, unit='AA'),
    'g' : u.Quantity(4770.0, unit='AA'),
    'r' : u.Quantity(6231.0, unit='AA'),
    'i' : u.Quantity(7625.0, unit='AA'),
    'z' : u.Quantity(9134.0, unit='AA'),

    # Swift-UVOT wavelengths
    'uvw2': u.Quantity(1928.0, unit='AA'),
    'uvm2': u.Quantity(2246.0, unit='AA'),
    'uvw1': u.Quantity(2600.0, unit='AA'),
    'uvot-u': u.Quantity(3465.0, unit='AA'),
    'uvot-b': u.Quantity(4392.0, unit='AA'),
    'uvot-v': u.Quantity(5468.0, unit='AA'),

    # RADIO/MM
    'S': u.Quantity(8.6896e6, unit='AA'),
    'Ka': u.Quantity(2.29e11, unit='Hz').to('AA', equivalencies=u.spectral()),
    'Kb': u.Quantity(2.72e11, unit='Hz').to('AA', equivalencies=u.spectral()),
    'Kc': u.Quantity(2.90e11, unit='Hz').to('AA', equivalencies=u.spectral()),
    'Kd': u.Quantity(3.41e11, unit='Hz').to('AA', equivalencies=u.spectral()),
    'W': u.Quantity(9.70E+10, unit='Hz').to('AA', equivalencies=u.spectral()),

    # HST
    'F125W': u.Quantity(2.4e14 , unit='Hz').to('AA', equivalencies=u.spectral()),
    'F775W': u.Quantity(3.9e14 , unit='Hz').to('AA', equivalencies=u.spectral()),
}

# aliases
EFF_WL['C'] = EFF_WL['S']
EFF_WL['r2'] = EFF_WL['r']
EFF_WL['i2'] = EFF_WL['i']
EFF_WL['z2'] = EFF_WL['z']
EFF_WL['Ks'] = EFF_WL['K']
EFF_WL['uprime'] = EFF_WL['u']
EFF_WL['gprime'] = EFF_WL['g']
EFF_WL['rprime'] = EFF_WL['r']
EFF_WL['iprime'] = EFF_WL['i']
EFF_WL['zprime'] = EFF_WL['z']
EFF_WL['uvot-uvw2'] = EFF_WL['uvw2']
EFF_WL['uvot-uvm2'] = EFF_WL['uvm2']
EFF_WL['uvot-uvw1'] = EFF_WL['uvw1']
EFF_WL['xray'] = (1e17 * u.Hz).to('AA', equivalencies=u.spectral())


LABELS = {
    # OPTICAL
    'Ic': 'I', 'Rc': 'R',

    # RADIO
    'Ka': '229 GHz', 'Kb': '272 GHz',
    'Kc': '290 GHz', 'Kd': '341 GHz',
    'S': '345 GHz',

    # UVOT
    'uvot-u': 'UVOT-u', 'uvot-b': 'UVOT-b',
    'uvot-v': 'UVOT-v', 'uvw1': 'UVOT-uvw1',
    'uvm2': 'UVOT-uvm2', 'uvw2': 'UVOT-uvw2',

    # XRT
    'xray': 'XRT'
}


def plot_frequencies_ampy(ampy, out_dir=None):
    """
    Plot a distribution of characteristic frequencies using
    randomly indexed MCMC samples from a completed Ampy object.

    Parameters
    ----------
    ampy : Ampy
        The completed Ampy object.

    out_dir : Path, optional
        The output directory.
    """
    return plot_frequencies(
        ampy.mcmc.sampler.get_chain(flat=True),
        ampy.mcmc.sampler.get_log_prob(flat=True),
        ampy.obs, ampy.mcmc.params, ampy.afterglow_model,
        model_kw=ampy.mcmc.models.afg_kw, out_dir=out_dir
    )


def plot_light_curve_ampy(ampy, title=None, out_dir=None):
    """
    Plot the best fitting light curve from a completed Ampy object.

    Parameters
    ----------
    ampy : Ampy
        The completed Ampy object.

    title : str, optional
        The title of the plot.

    out_dir : Path, optional
        The output directory.
    """
    # Light curve plotter takes an extinction object
    ext_model = None
    if ampy.extinction_model is not None:
        ext_model = ampy.extinction_model(Rv=3.1)

    plot_light_curve(
        ampy.afterglow_model, ampy.get_best_params(), ampy.obs,
        model_kw=ampy.mcmc.models.afg_kw, title=title,
        out_dir=out_dir, ext_model=ext_model
    )


def plot_density_profile_ampy(ampy, out_dir=None):
    """
    Plot the density profile as a function of radius.

    Parameters
    ----------
    ampy : Ampy
        The completed Ampy object.

    out_dir : Path, optional
        The output directory.
    """
    plot_density_profile(
        ampy.mcmc.sampler.get_chain(flat=True),
        ampy.mcmc.sampler.get_log_prob(flat=True),
        ampy.mcmc.params, ampy.obs, ampy.afterglow_model,
        model_kw=ampy.mcmc.models.afg_kw, out_dir=out_dir
    )


def plot_spectrum_timeseries_ampy(
    ampy,
    params=None,
    walker_params=None,
    walker_indices=None,
    out_dir=None,
    output_path=None,
    ncurves=10,
    nfreq=400,
):
    """
    Plot a VegasAfterglow-style spectrum-timeseries figure.

    When ``walker_params`` is supplied, each selected epoch includes the
    terminal cold-chain walker spectra as a translucent ensemble underneath
    the minimized/best-fit spectrum.

    Parameters
    ----------
    ampy : Ampy
        The completed Ampy object.

    params : dict, optional
        Parameter dictionary in the same layout as ``best_fit.json``.
        Defaults to the best sampled parameter set.

    out_dir : Path, optional
        Output directory used when ``output_path`` is not provided.

    output_path : Path, optional
        Exact destination for the PDF.

    ncurves : int, optional
        Number of time slices to plot.

    nfreq : int, optional
        Number of frequencies per spectrum.
    """
    if params is None:
        params = ampy.get_best_params()

    plot_spectrum_timeseries(
        ampy.afterglow_model,
        params,
        ampy.obs,
        walker_params=walker_params,
        walker_indices=walker_indices,
        model_kw=ampy.mcmc.models.afg_kw,
        out_dir=out_dir,
        output_path=output_path,
        ncurves=ncurves,
        nfreq=nfreq,
    )


def _format_seconds_label(time_days):
    """Format a time in days as a compact scientific-notation seconds label."""
    secs = float(days_to_sec(time_days))
    if not np.isfinite(secs) or secs <= 0.0:
        return f"{time_days:.3g} d"

    exponent = int(np.floor(np.log10(secs)))
    coefficient = secs / (10.0 ** exponent)
    return rf"${coefficient:.1f} \times 10^{{{exponent}}}\ \mathrm{{s}}$"


def _spectrum_frequency_grid(observation, model_obj, times, nfreq):
    """Build a robust frequency grid spanning data and modeled break scales."""
    freq_values = []

    for datum in observation.data:
        if datum.type == DataType.SPECTRAL_INDEX:
            continue
        freq = datum.frequency.to_value("Hz")
        if np.isfinite(freq) and freq > 0.0:
            freq_values.append(freq)

    try:
        spectrum = model_obj.spectrum(times)
    except Exception:
        spectrum = {}

    for key in ("nu_a", "nu_m", "nu_c"):
        values = np.atleast_1d(spectrum.get(key, np.array([])))
        mask = np.isfinite(values) & (values > 0.0)
        if mask.any():
            freq_values.extend(values[mask].tolist())

    if freq_values:
        freq_min = max(min(freq_values) / 100.0, 1e6)
        freq_max = min(max(freq_values) * 100.0, 1e25)
    else:
        freq_min, freq_max = 1e6, 1e22

    if not np.isfinite(freq_min) or not np.isfinite(freq_max) or freq_min <= 0.0 or freq_min >= freq_max:
        freq_min, freq_max = 1e6, 1e22

    return np.geomspace(freq_min, freq_max, num=nfreq)


def _fts_flag(model_obj, time_days):
    """Determine whether the model is in a fast-to-slow transition at ``time_days``."""
    if isinstance(model_obj, JetSimpy):
        return False
    try:
        spec = model_obj.spectrum(np.atleast_1d(time_days))
        return has_fts_transition(spec["nu_m"], spec["nu_c"])
    except Exception:
        return False


def plot_spectrum_timeseries(
    model,
    params,
    obs,
    walker_params=None,
    walker_indices=None,
    model_kw=None,
    out_dir=None,
    output_path=None,
    ncurves=10,
    nfreq=400,
):
    """
    Plot stacked instantaneous spectra across the observed time span.

    This is the VegasAfterglow-style frequency-vs-flux figure useful for
    inspecting the sharpness of spectral breaks.  The reference spectrum is
    the minimized/best-fit solution.  Supplied terminal walker parameters are
    evaluated at every selected epoch and plotted underneath it.
    """
    epoch = obs.epoch(mask=obs.flux_loc)
    tmin = float(epoch[0])
    tmax = float(epoch[1])
    if not np.isfinite(tmin) or not np.isfinite(tmax) or tmin <= 0.0 or tmax <= 0.0:
        raise ValueError("Observation epoch is invalid for spectrum-timeseries plotting.")

    if np.isclose(tmin, tmax):
        times = np.asarray([tmin], dtype=float)
    else:
        times = np.geomspace(tmin, tmax, num=max(2, int(ncurves)))

    model_obj = model(**params.get("model"), **(model_kw or {}))
    walker_params = list(walker_params or [])
    if walker_indices is None:
        walker_indices = list(range(len(walker_params)))
    if len(walker_indices) != len(walker_params):
        raise ValueError("walker_indices must have one entry for each walker parameter set.")
    nu = _spectrum_frequency_grid(obs, model_obj, times, nfreq=max(100, int(nfreq)))
    # VegasAfterglow accepts paired time/frequency vectors.  Evaluate every
    # displayed epoch for each walker in one call so the 100-walker product is
    # affordable during normal post-processing.
    walker_times = np.repeat(np.asarray(times, dtype=float), len(nu))
    walker_frequencies = np.tile(nu, len(times))
    walker_models = []
    failed_walker_evaluations = 0
    for walker_index, walker_param in zip(walker_indices, walker_params):
        try:
            walker_models.append((int(walker_index), model(**walker_param.get("model"), **(model_kw or {}))))
        except Exception:
            failed_walker_evaluations += len(times)

    fig, ax = plt.subplots(figsize=(10, 7.5))
    colors = plt.cm.viridis(np.linspace(0.02, 0.98, len(times)))
    curve_rows = []
    break_rows = []
    finite_walker_curves = 0
    curve_fieldnames = (
        "curve_kind",
        "walker_index",
        "curve_index",
        "time_days",
        "time_seconds",
        "frequency_hz",
        "flux_mjy",
        "flux_cgs_erg_cm2_s_hz",
        "fts_transition",
    )

    walker_fluxes = []
    for walker_index, walker_model in walker_models:
        try:
            values = np.asarray(
                walker_model.spectral_flux(walker_times, walker_frequencies),
                dtype=float,
            ).reshape(len(times), len(nu))
        except Exception:
            failed_walker_evaluations += len(times)
            continue
        walker_fluxes.append((walker_index, values))

    for curve_index, (color, time_days) in enumerate(zip(colors, times)):
        fts = _fts_flag(model_obj, time_days)
        # Draw the walker cloud first so the reference solution remains
        # legible.  Walker color identifies epoch, not walker identity.
        for walker_index, walker_flux_grid in walker_fluxes:
            walker_flux_mjy = walker_flux_grid[curve_index]
            walker_flux_cgs = walker_flux_mjy * 1e-26
            walker_mask = np.isfinite(walker_flux_cgs) & (walker_flux_cgs > 0.0)
            if not walker_mask.any():
                failed_walker_evaluations += 1
                continue
            finite_walker_curves += 1
            ax.loglog(
                nu[walker_mask],
                walker_flux_cgs[walker_mask],
                color=color,
                linewidth=0.45,
                alpha=0.035,
                zorder=1,
            )
            for frequency_hz, flux_mjy_value, flux_cgs_value in zip(
                nu[walker_mask], walker_flux_mjy[walker_mask], walker_flux_cgs[walker_mask]
            ):
                curve_rows.append(
                    {
                        "curve_kind": "terminal_cold_chain_walker",
                        "walker_index": int(walker_index),
                        "curve_index": curve_index,
                        "time_days": float(time_days),
                        "time_seconds": float(days_to_sec(time_days)),
                        "frequency_hz": float(frequency_hz),
                        "flux_mjy": float(flux_mjy_value),
                        "flux_cgs_erg_cm2_s_hz": float(flux_cgs_value),
                        "fts_transition": int(bool(fts)),
                    }
                )

        flux_mjy = np.asarray(model_obj.spectral_flux(time_days, nu), dtype=float).reshape(-1)
        flux_cgs = flux_mjy * 1e-26
        mask = np.isfinite(flux_cgs) & (flux_cgs > 0.0)
        if not mask.any():
            continue
        time_sec = float(days_to_sec(time_days))
        for frequency_hz, flux_mjy_value, flux_cgs_value in zip(nu[mask], flux_mjy[mask], flux_cgs[mask]):
            curve_rows.append(
                {
                    "curve_kind": "minimized_reference",
                    "walker_index": -1,
                    "curve_index": curve_index,
                    "time_days": float(time_days),
                    "time_seconds": time_sec,
                    "frequency_hz": float(frequency_hz),
                    "flux_mjy": float(flux_mjy_value),
                    "flux_cgs_erg_cm2_s_hz": float(flux_cgs_value),
                    "fts_transition": int(bool(fts)),
                }
            )
        ax.loglog(
            nu[mask],
            flux_cgs[mask],
            color=color,
            linewidth=1.8,
            label=_format_seconds_label(time_days),
            zorder=10,
        )
        try:
            spectrum = model_obj.spectrum(np.atleast_1d(time_days))
        except Exception:
            spectrum = {}
        row = {
            "curve_index": curve_index,
            "time_days": float(time_days),
            "time_seconds": time_sec,
            "fts_transition": int(bool(fts)),
        }
        for key in ("nu_a", "nu_m", "nu_c", "f_peak"):
            values = np.atleast_1d(spectrum.get(key, np.array([np.nan])))
            row[key] = float(values.flat[0]) if values.size else float("nan")
        break_rows.append(row)

    tref = float(np.sqrt(times[0] * times[-1]))
    ref_spectrum = model_obj.spectrum(np.atleast_1d(tref))
    for key, color in (("nu_a", "tab:blue"), ("nu_m", "tab:orange"), ("nu_c", "tab:green")):
        values = np.atleast_1d(ref_spectrum.get(key, np.array([])))
        if values.size == 0:
            continue
        value = float(values.flat[0])
        if np.isfinite(value) and value > 0.0:
            ax.axvline(value, color=color, linestyle="--", linewidth=2.0, alpha=0.9)

    apply_plot_title(fig, "Synchrotron Spectra", y=0.985, top=0.90)
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel(r"flux density (erg/cm$^2$/s/Hz)")
    ax.grid(alpha=0.25, which="both")
    ax.legend(loc="lower left", frameon=True, fancybox=False, framealpha=0.9)
    if walker_params:
        ax.text(
            0.985,
            0.035,
            f"{len(walker_params)} terminal walkers\nthin: walkers; thick: minimized",
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=9,
            color="0.25",
            zorder=20,
        )
    fig.tight_layout(rect=[0, 0.04, 1, 0.92])
    apply_plot_run_label(fig)

    written_pdf = None
    if output_path is not None:
        written_pdf = Path(output_path)
    elif out_dir is not None:
        written_pdf = Path(out_dir) / "spectrum_timeseries.pdf"

    if written_pdf is not None:
        written_pdf.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(written_pdf, dpi=300)
        fig.savefig(written_pdf.with_suffix(".png"), dpi=220)
        if curve_rows:
            with written_pdf.with_name(f"{written_pdf.stem}_curves.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=curve_fieldnames)
                writer.writeheader()
                writer.writerows(curve_rows)
            np.savez_compressed(
                written_pdf.with_name(f"{written_pdf.stem}_data.npz"),
                time_days=np.asarray(times, dtype=float),
                frequency_hz=np.asarray(nu, dtype=float),
                curve_index=np.asarray([row["curve_index"] for row in curve_rows], dtype=int),
                curve_kind=np.asarray([row["curve_kind"] for row in curve_rows], dtype="U32"),
                curve_walker_index=np.asarray([row["walker_index"] for row in curve_rows], dtype=int),
                curve_time_days=np.asarray([row["time_days"] for row in curve_rows], dtype=float),
                curve_time_seconds=np.asarray([row["time_seconds"] for row in curve_rows], dtype=float),
                curve_frequency_hz=np.asarray([row["frequency_hz"] for row in curve_rows], dtype=float),
                curve_flux_mjy=np.asarray([row["flux_mjy"] for row in curve_rows], dtype=float),
                curve_flux_cgs_erg_cm2_s_hz=np.asarray(
                    [row["flux_cgs_erg_cm2_s_hz"] for row in curve_rows],
                    dtype=float,
                ),
                curve_fts_transition=np.asarray([row["fts_transition"] for row in curve_rows], dtype=bool),
                terminal_cold_chain_walker_count=np.asarray(len(walker_params), dtype=int),
                finite_walker_curve_count=np.asarray(finite_walker_curves, dtype=int),
                failed_walker_evaluations=np.asarray(failed_walker_evaluations, dtype=int),
            )
        if break_rows:
            with written_pdf.with_name(f"{written_pdf.stem}_breaks.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(break_rows[0]))
                writer.writeheader()
                writer.writerows(break_rows)

    plt.close(fig)


def plot_frequencies(
    chain,
    log_prob,
    obs,
    params,
    model,
    model_kw=None,
    best=None,
    out_dir=None,
    nsamps=None,
    ntimes=None,
    fast_indices=False,
):
    """
    Plot a distribution of characteristic frequencies using
    randomly indexed MCMC samples.

    Parameters
    ----------
    chain :

    log_prob :

    obs : Observation
        The observational data.

    params : Parameters
        The model parameters.

    model :
        The afterglow model class.

    model_kw : dict
        Any kwargs used in ``model`` constructor.

    best : dict, optional

    out_dir : Path
        The output directory.
    """
    fp = FrequencyPlotter(chain, log_prob, params, model, model_kw, nsamps=nsamps)
    fp.plot_all(obs, best=best, out_dir=out_dir, ntimes=ntimes, fast_indices=fast_indices)
    plt.close()


def plot_light_curve(model, params, obs, model_kw=None, title=None, out_dir=None, ext_model=None, dual=False):
    """
    Plot the best fitting light curve over the data.

    Parameters
    ----------
    model :
        The afterglow model class.

    params : dict
        The model parameters.

    obs : Observation
        The observational data.

    model_kw : dict, optional
        Any kwargs used in ``model`` constructor.

    title : str, optional
        The title of the plot.

    out_dir : Path
        The output directory.

    ext_model : , optional
        The dust extinction model object.
    """
    lc = LightCurvePlot(model, params, obs, model_kw, title, dual=dual)
    lc.plot(out_dir=out_dir, ext_model=ext_model)
    # plt.close()
    return lc


def plot_density_profile(chain, log_prob, params, obs, model, model_kw=None, best=None, out_dir=None):
    """
    Plot the density profile of the external medium.

    Parameters
    ----------
    chain :

    log_prob :

    params : Parameters
        The model parameters.

    obs : Observation
        The observational data.

    model :
        The afterglow model class.

    model_kw : dict
        Any kwargs used in ``model`` constructor.

    best : dict, optional

    out_dir : Path
        The output directory.
    """
    required = ('smooth', 'radii')
    if not all(hasattr(model, name) for name in required):
        print(
            f"WARNING: Skipping density profile for model '{model.__name__}'; "
            f"missing required methods: {required}"
        )
        return False

    try:
        # Zero means every supplied walker.  The post-fit pipeline supplies the
        # terminal cold-chain walker state, so this preserves the full walker
        # ensemble instead of drawing a small random historical subset.
        nsamps = int(os.environ.get("JETFIT_DENSITY_PROFILE_SAMPLES", "0"))
        profiler = DensityProfiler(chain, log_prob, params, model, model_kw)
        profiler.profile(obs.times().min(), obs.times().max(), nsamps=nsamps, best_params=best)
        profiler.plot_profile(out_dir)
        plt.close()
        return True
    except Exception as exc:
        print(
            f"WARNING: Density profile plotting failed for model "
            f"'{model.__name__}': {type(exc).__name__}: {exc}"
        )
        return False


# <editor-fold desc="Light Curve">
def model_extinction(flux, model, sdata, params):
    """ Model contamination. """
    wn = [1.0 / d.wavelength.to_value('um') for d in sdata]

    # Multiplicative source-frame extinction
    if ebv_sf := params.get('extinction').get('ebv_source_frame'):
        z = params.get('model').get('z')
        flux *= model_source_extinction((1.0 + z) * np.array(wn), model, ebv_sf)

    # Additive host galaxy contamination
    if params.get('host') is not None:
        bands = [d.band for d in sdata]
        flux += model_host_contamination(np.array(bands), params.get('host'))

    # Multiplicative source-frame extinction
    if ebv_mw := params.get('extinction').get('ebv_milky_way'):
        rv = params.get('extinction').get('rv_milky_way')
        flux *= model_galactic_extinction(np.array(wn), model, ebv_mw, rv)

    return flux


def model_source_extinction(wn, model, ebv_sf) :
    """ Multiplicative source dust extinction. """
    return _model_extinction_in_range(wn, model, ebv_sf)


def model_host_contamination(bands, hosts):
    """ Additive host galaxy contamination. """
    if hosts is None:
        return 1.0
    return np.array([hosts.get(b + '_host') or 0.0 for b in bands])


def model_galactic_extinction(wn, model, ebv_mw, rv=None):
    """ Multiplicative Galactic dust extinction. """
    if rv is not None:
        model = model.__class__(Rv=rv)
    return _model_extinction_in_range(wn, model, ebv_mw)


def _model_extinction_in_range(wn, model, ebv):
    """Apply a dust law only where its wavelength domain is valid.

    Light-curve plots evaluate several bands at once.  Radio and X-ray bands
    are intentionally outside optical dust-law domains, but they must not
    suppress extinction for the optical entries in the same vector.
    """
    values = np.asarray(wn, dtype=float)
    scalar_input = values.ndim == 0
    values = np.atleast_1d(values)
    attenuation = np.ones(values.shape, dtype=float)
    valid = np.isfinite(values) & (model.x_range[0] < values) & (values < model.x_range[1])
    if np.any(valid):
        attenuation[valid] = model.extinguish(values[valid], Ebv=ebv)
    return float(attenuation[0]) if scalar_input else attenuation


def spread_data(flux, band, spread):
    """ Multiplicative offset. """
    for key, val in spread.items():
        flux[band == key] *= val
    return flux


def get_offset(d, data, offsets, positions):
    """"""
    for key, vals in positions.items():
        if d in data[vals]:
            value = offsets.get(key) if offsets is not None else None
            if value is None:
                return 1.0
            return 10.0 ** (0.4 * value)
    return 1.0


class LightCurvePlot:
    """ Plots the modeled light curve. """
    def __init__(self, model, params, observation, meta=None, title=None, dual=False):
        self.model = model
        self.params = params
        self.observation = observation
        self.meta = meta if meta is not None else {}

        self.ax = None
        self._set_axes(title, dual=dual)

    def _set_axes(self, title: str, dual=False):
        """ Sets the plotting axes. """
        ax1 = None

        if dual:
            fig, (ax, ax1) = plt.subplots(2, 1, sharex=True, figsize=(8, 10))
            ax1.set_xlabel('Time Since Trigger [days]')
            ax1.set_ylabel('Scaled Flux Density [mJy]')
            fig.subplots_adjust(hspace=0)
        else:
            fig, ax = plt.subplots(figsize=(8, 10))

        if title:
            fig.suptitle(str(title), fontsize=14, y=0.965)
            if dual:
                fig.subplots_adjust(top=0.88, hspace=0)
            else:
                fig.subplots_adjust(top=0.86)

        ax.set_ylabel('Flux Density [mJy]')
        ax.set_xlabel('Time Since Trigger [days]')
        ax.set_yscale('log')
        ax.set_xscale('log')
        ax.tick_params(axis='x', top=False, bottom=True, reset=True)

        # Add secondary x-axis
        # ax.xaxis.set_ticks_position('none')
        # ax.tick_params(axis='x', top=False, bottom=True)
        ax2 = ax.secondary_xaxis('top', functions=(days_to_sec, sec_to_days))
        ax2.set_xlabel("Time Since Trigger [seconds]", labelpad=10)
        ax2.xaxis.set_ticks_position('none')
        ax2.tick_params(axis='x', top=True, bottom=False)

        self.ax = ax
        self.ax1 = ax1

    def plot(self, out_dir=None, spread=None, **kwargs) -> None:
        """

        Parameters
        ----------
        out_dir : Path, optional
            The directory to save `light_curve.png.`

        spread : dict, optional

        kwargs : dict
            Optional args for `plot_model(show, **kwargs)`.
        """
        self.plot_model(self.params, ext_model=kwargs['ext_model'])
        self.plot_observation(self.params, spread)

        if out_dir is not None:
            save_plot_unique('light_curve', 'pdf', str(out_dir), dpi=400)

    def get_spectral_data(self):
        """ Returns single spectral flux for each filter. """
        return self.get_flux(DataType.SPECTRAL_FLUX)

    def get_integrated_data(self):
        """ Returns single integrated flux for each filter. """
        return self.get_flux(DataType.INTEGRATED_FLUX)

    def get_flux(self, flux_type):
        """ Returns single ``flux_type`` flux for each filter. """
        flux_mask = self.observation.flux_loc
        type_mask = self.observation.as_arrays.types[flux_mask]

        # Get all the filtered flux data
        _, filter_loc = self.observation.bands(unique=True, mask=flux_mask)
        data = self.observation.data[flux_mask][filter_loc]

        # return the filtered flux data
        return data[type_mask[filter_loc] == flux_type]

    def model_spectral_flux(self, sdata, params, t, ext_model=None):
        """ Model the spectral fluxes. """
        nu = np.array([d.frequency.to_value('Hz') for d in sdata])

        # Unextinguished spectral flux
        sflux = self.model_flux(params.get('model'), t, dict(nu=nu))

        return (
            sflux if ext_model is None else
            model_extinction(sflux, ext_model, sdata, params)
        )

    def model_integrated_flux(self, idata, params, t):
        """ Model the integrated fluxes. """
        lower = np.array([d.int_range.lower.to_value('Hz') for d in idata])
        upper = np.array([d.int_range.upper.to_value('Hz') for d in idata])
        return self.model_flux(params.get('model'), t, dict(lower=lower, upper=upper))

    def model_flux(self, params, t, args):
        """ Model the fluxes. Duh! """
        ag_model = self.model(**params, **self.meta)

        # What type of flux are we modeling?
        method = 'spectral_flux' if 'nu' in args else 'integrated_flux'

        # Is there a fast-to-slow transition?
        fts = has_fts_transition(ag_model.nu_m(t), ag_model.nu_c(t))

        return getattr(ag_model, method)(t, **args, fts=fts)

    def model_fluxes(self, params, times, ext_model=None):
        """ Return the modeled fluxes sorted by band. """
        fluxes = {}

        # Generate the spectral flux
        for ds in self.get_spectral_data():
            fluxes[ds.band] = self.model_spectral_flux(np.atleast_1d(ds), params, times, ext_model)

        # Generate the integrated flux
        for di in self.get_integrated_data():
            iflux = self.model_integrated_flux(np.atleast_1d(di), params, times)

            # Temporary: Force conversion to mJy
            iflux_q = u.Quantity(iflux, unit=self.observation.as_arrays.if_units)
            fluxes[di.band] = (iflux_q / di.int_range.width).to_value('mJy')

        return fluxes

    def default_times(self, ndata):
        """ Default time range to plot. """
        ranges = self.observation.epoch(self.observation.flux_loc)
        return np.geomspace(ranges[0] / 2, ranges[1] * 2, num=ndata)

    def plot_model(self, params, times=None, spread=None, ext_model=None, ndata=200):
        """
        Plots the light curve.

        Parameters
        ----------
        params : dict

        times : array-like, optional

        spread : dict, optional

        ext_model : dust_extinction model, optional
            Extinction model to use.

        ndata : int, optional, default=200
            The number of time points to generate if ``times`` is None.
        """
        if times is None:
            times = self.default_times(ndata)

        # Generate the flux for each band
        fluxes = self.model_fluxes(params, times, ext_model)

        for band, flux in fluxes.items():

            # Optional: Spread the data for legibility
            if spread is not None and band in spread:
                flux *= spread[band]

            # Configure the plotting options as desired
            color = OPTION_MAP[band]['color']

            self.ax.loglog(times, flux, '--', linewidth=1.0, color=color)

        # self.ax.set_xlim(times.min(), times.max())

    def plot_observation(self, params, spreads=None, offset=False, excluded=False, axes='upper'):
        """"""
        formatted_data = self._format_observation(params, spreads, offset)

        ax = self.ax if axes == 'upper' else self.ax1
        self._plot_observation(formatted_data, spreads, excluded, axes)
        # if axes == 'upper':
        ax.legend(loc='lower left', ncols=2, columnspacing=0.25, handletextpad=0.25, fontsize=12)
        ax.grid(alpha=0.3)
        # self.ax.set_ylim(bottom=1e-7)

    def _format_observation(self, params, spreads=None, offset=False):
        """ Formats the observation. Intended for internal use only. """
        plot_data = {}

        # Get all the data (included + excluded)
        data = self.observation.get_data()

        for i, d in enumerate(data):
            corr = 1.0

            # We only care about flux for light curves
            if d.type == DataType.SPECTRAL_INDEX:
                continue

            if d.band not in plot_data:
                plot_data[d.band] = {
                    'time': [], 'flux': [], 'error': [], 'include': []
                }

            # Temporary: Force conversion to mJy
            if d.type == DataType.INTEGRATED_FLUX:
                d = d.to_spectral('mJy')

            # Force time conversion to days
            plot_data[d.band]['time'].append(d.time.to_value('d'))
            plot_data[d.band]['include'].append(self.observation.include[i])

            # Optional: Apply calibration offsets
            if offset and params.get('offsets') is not None:
                corr *= get_offset(d, data, params['offsets'], self.observation.get_offsets())

            # Optional: Spread the data for legibility
            if spreads is not None and d.band in spreads:
                corr *= spreads[d.band]

            # Finalize the values for detected photometry
            if d.value.to_value('mJy') != 0.0:
                plot_data[d.band]['flux'].append(d.value.to_value('mJy') * corr)
                plot_data[d.band]['error'].append(d.uncertainty.center.to_value('mJy') * corr)

            # Finalize the values for upper limits
            else:
                # Assumes error is 3-sigma limit
                limit = d.uncertainty.center.to_value('mJy') * 3.0
                plot_data[d.band]['flux'].append(limit * corr)
                plot_data[d.band]['error'].append(0.0)

        return plot_data

    def _plot_observation(self, plot_data, spreads=None, excluded=False, axes='upper'):
        """ Plots the observation. Intended for internal use only. """
        # Sort by wavelength for a pretty legend
        sorted_bands = sorted(list(plot_data.keys()), key=lambda b: EFF_WL[b], reverse=True)

        ax = self.ax if axes == 'upper' else self.ax1

        # The data has been gathered and sorted, now plot it!
        for sb in sorted_bands:
            label = LABELS.get(sb) or sb

            # Include the spread in the legend label
            if spreads is not None:
                if spreads.get(sb) is not None and spreads.get(sb) != 1:
                    label = f"{LABELS.get(sb) or sb} x {int(spreads.get(sb))}"

            mask = np.where(np.atleast_1d(plot_data[sb]['include']) == 1, True, False)

            # Plot unmodeled data as grey, open circles
            if (~mask).any() and excluded:
                e = np.atleast_1d(plot_data[sb]['error'])[~mask]
                x = np.atleast_1d(plot_data[sb]['time'])[~mask]
                y = np.atleast_1d(plot_data[sb]['flux'])[~mask]

                ax.errorbar(
                    x, y, yerr=e, marker='o', markerfacecolor='none', mew=0.5,
                    fmt='.', markersize=3.0, elinewidth=0.5, color='grey', alpha=0.5,
                    zorder=18
                )

            # Plot modeled data as usual
            if mask.any():
                e = np.atleast_1d(plot_data[sb]['error'])[mask]
                x = np.atleast_1d(plot_data[sb]['time'])[mask]
                y = np.atleast_1d(plot_data[sb]['flux'])[mask]

                ax.errorbar(
                    x, y, yerr=e, fmt='.', markersize=3.0,
                    elinewidth=0.5, label=label, zorder=20, **OPTION_MAP[sb]
                )
# </editor-fold>


# <editor-fold desc="Frequencies">
def model_freqs(model, t, params, **kwargs):
    """
    Models the critical frequencies.

    Parameters
    ----------
    model :
        The afterglow model class.

    t : np.ndarray
        The observer-frame times [d].

    params : Parameters
        The model parameters.

    kwargs :
        Any kwargs used in ``model`` constructor.
    """
    afterglow_model = model(**params.get('model'), **kwargs)
    try:
        if hasattr(afterglow_model, 'critical_frequencies'):
            try:
                freqs = afterglow_model.critical_frequencies(t)
                nu_m = freqs.get('nu_m')
                nu_c = freqs.get('nu_c')
                nu_a = freqs.get('nu_a')
                if nu_m is not None and nu_c is not None:
                    return nu_m, nu_c, nu_a
            except Exception:
                # Fall back for older models that do not fully support the compact
                # diagnostic frequency API.
                pass

        if hasattr(afterglow_model, 'spectrum'):
            try:
                spectrum = afterglow_model.spectrum(t)
                nu_m = spectrum.get('nu_m')
                nu_c = spectrum.get('nu_c')
                nu_a = spectrum.get('nu_a')
                if nu_m is not None and nu_c is not None:
                    return nu_m, nu_c, nu_a
            except Exception:
                # Fall back to the older per-frequency path for models whose
                # diagnostic spectrum helper is incomplete.
                pass

        nu_m = afterglow_model.nu_m(t)
        nu_c = afterglow_model.nu_c(t)
        nu_a = model_nu_a(afterglow_model, t, nu_m, nu_c)
        return nu_m, nu_c, nu_a
    finally:
        del afterglow_model
        gc.collect()


def model_nu_a(model, t, nu_m, nu_c):
    """
    Models self-absorption which can be optional.

    Parameters
    ----------
    model :
        The afterglow model class.

    t : np.ndarray
        The observer-frame times [d].

    nu_m : np.ndarray of float
        The synchrotron frequencies [Hz].

    nu_c : np.ndarray of float
        The cooling frequencies [Hz].

    Returns
    -------
    np.ndarray of float or None
        The self-absorption frequencies [Hz].
    """
    if hasattr(model, 'nu_a'):
        if hasattr(model, 'use_sa') and not model.use_sa:
            return None
        return model.nu_a(t, nu_m=nu_m, nu_c=nu_c)


class FrequencyPlotter(Profiler):
    """
    Plots and models the characteristic frequencies.

    Parameters
    ----------

    params : Parameters
        The model parameters.

    model :
        The afterglow model class.

    model_kw : dict
        Any kwargs used in ``model`` constructor.
    """
    def __init__(self, chain, log_prob, params, model, model_kw=None, nsamps=None):
        super().__init__(chain, log_prob, params)
        self.model = model
        self.model_kw = model_kw

        self.samples = self.draw(100 if nsamps is None else int(nsamps))

        self.axes = None
        self._set_axes()

    def _set_axes(self) -> None:
        """ Set plot axes. """
        fig, axes = plt.subplots(
            2, 1, figsize=(8, 8), sharex=True,
            gridspec_kw={'height_ratios': [4.2, 0.85]},
        )
        fig.subplots_adjust(hspace=0.03)
        apply_plot_title(fig, "Critical Frequencies and Spectral Index", y=0.965, top=0.90)

        # ax.set_title('Critical Frequencies')
        axis_label_fontsize = 10
        axes[1].set_xlabel('Time Since Trigger [days]', fontsize=axis_label_fontsize)
        axes[0].set_ylabel('Frequency [Hz]', fontsize=axis_label_fontsize)
        axes[1].set_ylabel('Spectral Index', fontsize=axis_label_fontsize)

        ax2 = axes[0].secondary_xaxis('top', functions=(days_to_sec, sec_to_days))
        ax2.set_xlabel("Time Since Trigger [seconds]", labelpad=8, fontsize=axis_label_fontsize)
        ax2.tick_params(axis='x', top=True, bottom=False, labelsize=9)
        axes[0].tick_params(axis='x', top=False, bottom=False, labelbottom=False)
        self.axes = axes
        self.fig = fig

    def add_event_label(self, event=None):
        """Add an in-panel GRB label consistent with other product plots."""
        if not event:
            return
        label = str(event)
        if not label.upper().startswith('GRB '):
            label = f'GRB {label}'
        add_collision_aware_grb_label(
            self.axes[0],
            label,
            corner="upper left",
            candidates=[
                (0.02, 0.875),
                (0.02, 0.79),
                (0.02, 0.705),
                (0.02, 0.62),
                (0.08, 0.875),
                (0.08, 0.79),
            ],
            fontsize=15,
            zorder=1000,
        )

    def plot_all(self, obs, best=None, out_dir=None, ntimes=None, fast_indices=False):
        """
        Plots everything!

        Parameters
        ----------
        obs : Observation
            The observational data.

        best : dict, optional

        out_dir : Path
            The output directory.
        """
        epoch = obs.epoch(mask=obs.flux_loc)

        times = np.geomspace(
            epoch.min() / 2, epoch.max() * 2, num=200 if ntimes is None else int(ntimes)
        )

        # Compute and save frequency arrays before plotting so replots and
        # science checks do not have to rerun expensive structured-jet details.
        self.plot_dist(times, best, out_dir=out_dir)
        self.plot_data(obs)
        if fast_indices:
            self.plot_index_data_only(obs)
        else:
            self.plot_indices(obs, best, times)
        event = os.environ.get('JETFIT_PLOT_EVENT_TITLE', '').strip()
        if not event and out_dir is not None:
            event = getattr(out_dir, 'name', None) or str(out_dir).rstrip('/').split('/')[-1]
        self.add_event_label(event)

        self.axes[1].set_xlim(times.min(), times.max())

        if out_dir is not None:
            self.save_tight('frequencies', 'pdf', str(out_dir))
            self.save_tight('frequencies', 'png', str(out_dir))

    def save_tight(self, filename_base, ext, directory):
        """Save the frequency plot with a tight publication-style bbox."""
        i = 0
        while True:
            filename = f"{filename_base}.{ext}" if i == 0 else f"{filename_base}_{i}.{ext}"
            filepath = os.path.join(directory, filename)
            if not os.path.exists(filepath):
                apply_plot_run_label(self.fig)
                self.fig.savefig(filepath, bbox_inches='tight', pad_inches=0.045)
                return
            i += 1

    def plot_indices(self, obs, best=None, times=None):
        """"""
        if times is None:
            epoch = obs.epoch(mask=obs.flux_loc)

            times = np.geomspace(
                epoch.min() / 2, epoch.max() * 2, num=200
            )

        if best is None:
            best = self.best(cat='model')

        # Plot best for all times
        model = self.model(**best.get('model'), **(self.model_kw or {}))
        fts = False
        if not isinstance(model, JetSimpy):
            full_spectrum = model.spectrum(obs.times())
            fts = has_fts_transition(full_spectrum['nu_m'], full_spectrum['nu_c'])
        indices = model.spectral_index(times, obs.int_lowers()[0], obs.int_uppers()[0], fts=fts)
        self.axes[1].plot(times, indices, color='black', zorder=99, linestyle='--')

        # Plot spectral-index model curves and the observed spectral-index rows.
        for j, index in enumerate(obs.data[obs.sindex_loc]):
            lower = index.int_range.lower.to_value('Hz')
            upper = index.int_range.upper.to_value('Hz')

            for i, s in enumerate(self.samples):
                p = self.params.samples_to_dict(s)
                model = self.model(**p.get('model'), **(self.model_kw or {}))

                # Is there a fast-to-slow transition?
                fts = False

                if hasattr(model, 'smooth_fast_to_slow_transition'):
                    fts = bool(model.smooth_fast_to_slow_transition)
                elif not isinstance(model, JetSimpy):
                    full_spectrum = model.spectrum(obs.times())
                    fts = has_fts_transition(full_spectrum['nu_m'], full_spectrum['nu_c'])

                try:
                    modeled = model.spectral_index(times, lower, upper, fts=fts)
                except TypeError:
                    modeled = model.spectral_index(times, lower, upper)
                except Exception:
                    index_spectrum = model.spectrum(times)
                    modeled = SpectralIndexModel(**index_spectrum).evaluate(lower, upper, fts=fts)

                self.axes[1].plot(
                    times,
                    modeled,
                    alpha=0.2,
                    color='royalblue',
                )

            self.axes[1].errorbar(
                index.time.to_value('d'), index.value.value,
                yerr=((index.uncertainty.lower.value,), (index.uncertainty.lower.value,)),
                fmt='o',
                linestyle='none',
                capsize=3,
                color='black',
                zorder=999,
            )

        break_handles, break_labels = self.axes[0].get_legend_handles_labels()
        if break_handles:
            self.fig.legend(
                break_handles, break_labels,
                loc='upper center',
                bbox_to_anchor=(0.5, 0.925),
                ncol=3,
                fontsize=11,
                frameon=True,
                fancybox=False,
                edgecolor='black',
                borderaxespad=0.1,
                columnspacing=1.8,
                handlelength=2.4,
            )

        self.fig.tight_layout(rect=[0, 0.04, 1, 0.90])

    def plot_index_data_only(self, obs):
        """Plot only observed spectral-index points for urgent frequency refreshes."""
        for j, index in enumerate(obs.data[obs.sindex_loc]):
            self.axes[1].errorbar(
                index.time.to_value('d'), index.value.value,
                yerr=((index.uncertainty.lower.value,), (index.uncertainty.lower.value,)),
                fmt='o',
                linestyle='none',
                capsize=3,
                color='black',
                zorder=999,
            )

        break_handles, break_labels = self.axes[0].get_legend_handles_labels()
        if break_handles:
            self.fig.legend(
                break_handles, break_labels,
                loc='upper center',
                bbox_to_anchor=(0.5, 0.925),
                ncol=3,
                fontsize=11,
                frameon=True,
                fancybox=False,
                edgecolor='black',
                borderaxespad=0.1,
                columnspacing=1.8,
                handlelength=2.4,
            )

        self.fig.tight_layout(rect=[0, 0.04, 1, 0.90])

    def _write_frequency_data(self, out_dir, times, sample_data, best_data):
        """Save critical-frequency arrays before drawing the frequency plot."""
        if out_dir is None:
            return

        out_path = Path(out_dir)
        arrays = {
            "times_days": np.asarray(times, dtype=float),
            "times_seconds": np.asarray(days_to_sec(times), dtype=float),
            "sample_nu_m_hz": np.asarray(sample_data["nu_m"], dtype=float),
            "sample_nu_c_hz": np.asarray(sample_data["nu_c"], dtype=float),
            "sample_nu_a_hz": np.asarray(sample_data["nu_a"], dtype=float),
            "best_nu_m_hz": np.asarray(best_data["nu_m"], dtype=float),
            "best_nu_c_hz": np.asarray(best_data["nu_c"], dtype=float),
            "best_nu_a_hz": np.asarray(best_data["nu_a"], dtype=float),
        }
        np.savez_compressed(out_path / "frequencies_data.npz", **arrays)

        csv_path = out_path / "frequencies_best_curve.csv"
        header = "time_days,time_seconds,nu_a_hz,nu_m_hz,nu_c_hz\n"
        rows = zip(
            arrays["times_days"],
            arrays["times_seconds"],
            arrays["best_nu_a_hz"],
            arrays["best_nu_m_hz"],
            arrays["best_nu_c_hz"],
        )
        with csv_path.open("w") as handle:
            handle.write(header)
            for row in rows:
                handle.write(",".join(f"{float(value):.12e}" for value in row) + "\n")

    def _read_frequency_data(self, out_dir, times):
        """Read cached critical-frequency arrays when they match this time grid."""
        if out_dir is None:
            return None

        cache_path = Path(out_dir) / "frequencies_data.npz"
        if not cache_path.exists():
            return None

        try:
            with np.load(cache_path) as data:
                cached_times = np.asarray(data["times_days"], dtype=float)
                if cached_times.shape != np.asarray(times).shape or not np.allclose(cached_times, times):
                    return None
                return {
                    "sample": {
                        "nu_m": np.asarray(data["sample_nu_m_hz"], dtype=float),
                        "nu_c": np.asarray(data["sample_nu_c_hz"], dtype=float),
                        "nu_a": np.asarray(data["sample_nu_a_hz"], dtype=float),
                    },
                    "best": {
                        "nu_m": np.asarray(data["best_nu_m_hz"], dtype=float),
                        "nu_c": np.asarray(data["best_nu_c_hz"], dtype=float),
                        "nu_a": np.asarray(data["best_nu_a_hz"], dtype=float),
                    },
                }
        except Exception:
            return None

    def _plot_frequency_arrays(self, times, sample_data, best_data):
        """Plot cached or freshly calculated critical-frequency arrays."""
        for nu_a, nu_m, nu_c in zip(sample_data["nu_a"], sample_data["nu_m"], sample_data["nu_c"]):
            if np.isfinite(nu_a).any():
                self.axes[0].loglog(times, nu_a, color='tab:green', alpha=0.1)
            self.axes[0].loglog(times, nu_m, color='tab:blue', alpha=0.1)
            self.axes[0].loglog(times, nu_c, color='tab:orange', alpha=0.1)

        if np.isfinite(best_data["nu_a"]).any():
            self.axes[0].loglog(
                times, best_data["nu_a"], color='tab:green', linewidth=2,
                label=r'self-abs. ($\nu_a$)',
            )
        self.axes[0].loglog(
            times, best_data["nu_m"], color='tab:blue', linewidth=2,
            label=r'injection ($\nu_m$)',
        )
        self.axes[0].loglog(
            times, best_data["nu_c"], color='tab:orange', linewidth=2,
            label=r'cooling ($\nu_c$)',
        )

    def plot_dist(self, times, best=None, nsamps=None, out_dir=None):
        """
        Plot the distribution of frequencies.

        Parameters
        ----------
        times : np.ndarray
            The observer-frame times [d].
        """
        if nsamps is not None:
            samples = self.draw(nsamps)
        else:
            samples = self.samples

        cached = self._read_frequency_data(out_dir, times)
        if cached is not None:
            self._plot_frequency_arrays(times, cached["sample"], cached["best"])
            return

        sample_data = {"nu_m": [], "nu_c": [], "nu_a": []}

        # Model the frequencies for each randomly sampled set.
        for sample in samples:
            params = self.params.samples_to_dict(sample, cat='model')

            nu_m, nu_c, nu_a = model_freqs(
                self.model, times, params, **(self.model_kw or {})
            )
            sample_data["nu_m"].append(np.asarray(nu_m, dtype=float))
            sample_data["nu_c"].append(np.asarray(nu_c, dtype=float))
            sample_data["nu_a"].append(
                np.asarray(nu_a, dtype=float)
                if nu_a is not None else np.full_like(times, np.nan, dtype=float)
            )

        if best is None:
            best = self.best(cat='model')
        best_nu_ms, best_nu_cs, best_nu_as = model_freqs(
            self.model, times, best, **(self.model_kw or {})
        )
        best_data = {
            "nu_m": np.asarray(best_nu_ms, dtype=float),
            "nu_c": np.asarray(best_nu_cs, dtype=float),
            "nu_a": (
                np.asarray(best_nu_as, dtype=float)
                if best_nu_as is not None else np.full_like(times, np.nan, dtype=float)
            ),
        }
        self._write_frequency_data(out_dir, times, sample_data, best_data)

        # Plot the critical frequencies after the reusable data product exists.
        self._plot_frequency_arrays(times, sample_data, best_data)

    def plot_best(self, times, best=None):
        """
        Plot the best frequencies.

        Parameters
        ----------
        times : np.ndarray
            The observer-frame times [d].
        """
        if best is None:
            best = self.best(cat='model')

        # Model the most likely frequencies
        best_nu_ms, best_nu_cs, best_nu_as = model_freqs(
            self.model, times, best, **(self.model_kw or {})
        )

        # Get rad to ad time
        # if self.model.__name__ == 'StratifiedFireballModel':
        #     model = self.model(**best.get('model'), **(self.model_kw or {}))
        #
        #     n, k = model.smooth(times)
        #     n = n * model.ref_radius ** k
        #
        #     radiation = RadiationModel(
        #         n, k, model.p, model.eps_b, model.eps_e, model.dL, model.z, model.hmf
        #     )
        #
        #     rta = radiation.rad_to_ad_time(model.E / model.lf0, times, model.nu_m(times), model.nu_c(times))
        #     print(rta)
        #
        #     if rta is not None:
        #         self.axes[0].axvline(rta, color='grey', linestyle='--')

        # Over-plot with the most likely frequencies
        if best_nu_as is not None:
            self.axes[0].loglog(
                times, best_nu_as, color='tab:green', linewidth=2,
                label=r'self-abs. ($\nu_a$)',
            )

        self.axes[0].loglog(
            times, best_nu_ms, color='tab:blue', linewidth=2,
            label=r'injection ($\nu_m$)',
        )
        self.axes[0].loglog(
            times, best_nu_cs, color='tab:orange', linewidth=2,
            label=r'cooling ($\nu_c$)',
        )
        return {
            "nu_m": np.asarray(best_nu_ms, dtype=float),
            "nu_c": np.asarray(best_nu_cs, dtype=float),
            "nu_a": (
                np.asarray(best_nu_as, dtype=float)
                if best_nu_as is not None else np.full_like(times, np.nan, dtype=float)
            ),
        }

    def plot_data(self, obs):
        """
        Plot observed frequencies vs time.

        Parameters
        ----------
        obs : Observation
            The observational data.
        """
        plot_data = {}

        # Get the unique band names
        bands = np.unique(obs.as_arrays.bands[obs.flux_loc])

        # Organize the data by band
        for band in bands:
            plot_data[band] = {'t': [], 'nu': []}

            # Get all the data for this band
            data = obs.data[obs.as_arrays.bands == band]

            for datum in data:
                plot_data[band]['t'].append(datum.time.to_value('d'))
                plot_data[band]['nu'].append(datum.frequency.to_value('Hz'))

        # Sort by wavelength
        bands_to_plot = list(plot_data.keys())
        sorted_bands = sorted(bands_to_plot, key=lambda b: EFF_WL[b], reverse=True)

        # Plot the sorted data
        for x in sorted_bands:
            OPTION_MAP[x]['marker'] = '.'

            if x == 'Ic': band = 'I'
            elif x == 'Rc': band = 'R'
            elif x == 'C': band = '3 GHz'
            elif x == 'Ka': band = '6 GHz'
            elif x == 'Kb': band = '272 GHz'
            elif x == 'Kc': band = '290 GHz'
            elif x == 'Kd': band = '341 GHz'
            elif x == 'uvot-u': band = 'UVOT-u'
            elif x == 'uvot-b': band = 'UVOT-b'
            elif x == 'uvot-v': band = 'UVOT-v'
            elif x == 'uvw1': band = 'UVOT-uvw1'
            elif x == 'uvm2': band = 'UVOT-uvm2'
            elif x == 'uvw2': band = 'UVOT-uvw2'
            elif x == 'xray': band = 'XRAY'
            elif x == 'S': band = '345 GHz'
            else: band = x

            self.axes[0].scatter(plot_data[x]['t'], plot_data[x]['nu'], label='_nolegend_', **OPTION_MAP[x])

        # self.ax.legend(loc='center left', bbox_to_anchor=(1.0, 0.5), frameon=True, edgecolor='black', facecolor='white')
        # self.ax.set_ylim(1e2, 1e22)
        # self.axes[0].legend(loc='lower left', ncols=4, facecolor='white', columnspacing=0.25, handletextpad=0.25, fontsize=12)
        self.axes[0].grid(alpha=0.3, axis='x')
# </editor-fold>


# <editor-fold desc="Single Density Profile"
def cm_to_pc(val):
    """"""
    return val * 3.2407792896664E-19


def pc_to_cm(val):
    """"""
    return val / 3.2407792896664E-19


PROTON_MASS_G = 1.67262192369e-24
SOLAR_MASS_G = 1.98847e33
DENSITY_SHELL_METHOD_VERSION = "spherical-shell-dynamical-radius-v2"


def density_shell_properties(radius_cm, number_density_cm3):
    """Integrate an observed radial shell of hydrogen number density.

    The returned mass is the spherical/isotropic-equivalent hydrogen mass,
    ``4 pi m_p integral[n(r) r^2 dr]``.  Both mass and number-density means
    are retained because they are useful for distinct physical comparisons.
    """
    radius = np.asarray(radius_cm, dtype=float)
    density = np.asarray(number_density_cm3, dtype=float)
    valid = np.isfinite(radius) & np.isfinite(density) & (radius > 0.0) & (density >= 0.0)
    radius = radius[valid]
    density = density[valid]
    if radius.size < 2:
        return None
    order = np.argsort(radius)
    radius = radius[order]
    density = density[order]
    r_inner = float(radius[0])
    r_outer = float(radius[-1])
    if not r_outer > r_inner:
        return None
    volume_cm3 = (4.0 * np.pi / 3.0) * (r_outer ** 3 - r_inner ** 3)
    mass_g = 4.0 * np.pi * PROTON_MASS_G * float(np.trapezoid(density * radius ** 2, radius))
    if not (np.isfinite(volume_cm3) and np.isfinite(mass_g) and volume_cm3 > 0.0 and mass_g >= 0.0):
        return None
    mean_mass_density = mass_g / volume_cm3
    mean_number_density = mean_mass_density / PROTON_MASS_G
    return {
        "r_inner_cm": r_inner,
        "r_outer_cm": r_outer,
        "shell_volume_cm3": float(volume_cm3),
        "shell_mass_g": float(mass_g),
        "shell_mass_msun": float(mass_g / SOLAR_MASS_G),
        "mean_mass_density_g_cm3": float(mean_mass_density),
        "mean_number_density_cm3": float(mean_number_density),
    }


def powerlaw_density_shell_properties(r_inner_cm, r_outer_cm, n017, k, r_ref_cm=1.0e17):
    """Return exact shell properties for ``n(r) = n017 (r / r_ref)^(-k)``."""
    r_inner = float(r_inner_cm)
    r_outer = float(r_outer_cm)
    n017 = float(n017)
    k = float(k)
    r_ref = float(r_ref_cm)
    if not (
        np.isfinite(r_inner) and np.isfinite(r_outer) and np.isfinite(n017)
        and np.isfinite(k) and np.isfinite(r_ref) and r_inner > 0.0
        and r_outer > r_inner and n017 >= 0.0 and r_ref > 0.0
    ):
        return None

    # Express the integral at r_outer to avoid overflow/underflow from
    # separately evaluating r_ref**k and r_outer**(3-k).
    exponent = 3.0 - k
    radius_ratio = r_inner / r_outer
    n_outer = n017 * (r_outer / r_ref) ** (-k)
    if abs(exponent) < 1.0e-10:
        radial_integral = n_outer * r_outer ** 3 * np.log(r_outer / r_inner)
    else:
        radial_integral = n_outer * r_outer ** 3 * (1.0 - radius_ratio ** exponent) / exponent
    volume_cm3 = (4.0 * np.pi / 3.0) * (r_outer ** 3 - r_inner ** 3)
    mass_g = 4.0 * np.pi * PROTON_MASS_G * radial_integral
    if not (np.isfinite(volume_cm3) and np.isfinite(mass_g) and volume_cm3 > 0.0 and mass_g >= 0.0):
        return None
    mean_mass_density = mass_g / volume_cm3
    return {
        "r_inner_cm": r_inner,
        "r_outer_cm": r_outer,
        "shell_volume_cm3": float(volume_cm3),
        "shell_mass_g": float(mass_g),
        "shell_mass_msun": float(mass_g / SOLAR_MASS_G),
        "mean_mass_density_g_cm3": float(mean_mass_density),
        "mean_number_density_cm3": float(mean_mass_density / PROTON_MASS_G),
    }


class DensityProfiler(Profiler):
    """
    Density profiler.

    Parameters
    ----------

    params : `Parameters`
        The parameters object.

    Attributes
    ----------
    n0 : dict
        The density normalizations [cm-3].

    k : dict
        The density power-law indices.

    r : dict
        The blast wave radii [cm].

    r_ref : dict
        The transition radius [cm].
    """
    r_ref_options = {
        'alpha': 0.5, 'linestyle': '--',
        'color': 'black', 'label': r'$R_{t}$',
    }

    def __init__(self, chain, log_prob, params, model, model_kw=None):
        super().__init__(chain, log_prob, params)

        self.afterglow_model = model
        self.afterglow_model_kw = model_kw or {}

        self.n0 = {'best': [], 'dist': []}
        self.k = {'best': [], 'dist': []}
        self.r = {'best': [], 'dist': []}
        self.r_ref = {'best': [], 'dist': []}
        self.observed_shell = {'best': [], 'dist': []}

    def profile(self, start, stop, nsamps=100, best_params=None):
        """
        Generates a profile for a random distribution of
        samples drawn from ``sampler``. Over plots with the
        highest likelihood profile.

        Parameters
        ----------
        start, stop : float
            The start, stop time [days].

        nsamps : int, optional, default=100
            Number of samples to draw.  A non-positive value uses every
            supplied sample.

        best_params : dict, optional
        """
        samples = self.chain if nsamps <= 0 else self.draw(nsamps)

        # For the production single-power-law CSM model, density is exactly
        # n(r) = n017 (r / r_ref)^(-k).  A separate full afterglow simulation
        # for every walker is unnecessary and can exhaust memory before all
        # walkers are drawn.  Use one best-fit radius grid and evaluate every
        # walker's analytic density law on that shared physical grid.
        if "powerlaw" in self.afterglow_model.__name__.lower():
            self._profile_single_powerlaw(start, stop, samples, best_params)
            return

        for s in samples:
            params = self.params.samples_to_dict(s).get('model')

            # If jet-break, use as end time
            times = np.geomspace(start, params.get('tj') or stop, 500)

            # Model and store using random distribution of params
            self.model(times, params, 'dist')

        # Model and store using the best fitting params
        if best_params is None:
            best_params = self.best().get('model')

        times = np.geomspace(start, best_params.get('tj') or stop, 500)

        self.model(times, best_params, 'best')

    def _profile_single_powerlaw(self, start, stop, samples, best_params):
        if best_params is None:
            best_params = self.best().get('model')
        if best_params is None:
            raise ValueError("Missing best-fit model parameters for density profile.")

        # The density law is analytic, so walker-specific radius extents can be
        # restored without a costly native model evaluation per walker.
        ref_radius = 1.0e17

        for sample in samples:
            model_params = self.params.samples_to_dict(sample).get('model')
            if model_params is None:
                continue
            n017 = float(model_params["n017"])
            k = float(model_params["k"])
            radii = self._dynamical_walker_radius_grid(start, stop, model_params)
            shell_radii = self._dynamical_observed_shell_radius_grid(start, stop, model_params)
            self.r['dist'].append(radii)
            self.n0['dist'].append(np.full_like(radii, n017))
            self.k['dist'].append(np.full_like(radii, k))
            self.r_ref['dist'].append(ref_radius)
            self.observed_shell['dist'].append((
                shell_radii, np.full_like(shell_radii, n017), np.full_like(shell_radii, k), ref_radius,
            ))

        best_n017 = float(best_params["n017"])
        best_k = float(best_params["k"])
        best_radii = self._dynamical_walker_radius_grid(start, stop, best_params)
        self.r['best'].append(best_radii)
        self.n0['best'].append(np.full_like(best_radii, best_n017))
        self.k['best'].append(np.full_like(best_radii, best_k))
        self.r_ref['best'].append(ref_radius)
        best_shell_radii = self._dynamical_observed_shell_radius_grid(start, stop, best_params)
        self.observed_shell['best'].append((
            best_shell_radii, np.full_like(best_shell_radii, best_n017), np.full_like(best_shell_radii, best_k), ref_radius,
        ))

    def _blast_wave_radii(self, times, model_params):
        """Fast dynamical radii using the fitted on-axis blast-wave parameters.

        This deliberately avoids the former ballistic ``2 c Gamma_0^2 t``
        shortcut, which grossly overestimated late-time radii for high-Gamma
        walkers.  It is an analytic relativistic blast-wave approximation;
        the native VegasAfterglow details calculation remains available for
        dedicated high-fidelity diagnostics but is impractical for 100 walkers.
        """
        jet_type = str(self.afterglow_model_kw.get("jet_type", "powerlaw"))
        theta_c = float(model_params.get("theta_c", 0.1))
        e_iso52 = resolve_e_iso52(
            E52=model_params.get("E52"),
            E_j_52=model_params.get("E_j_52"),
            E_j_core_52=model_params.get("E_j_core_52"),
            jet_type=jet_type,
            theta_c=theta_c,
            k_e=model_params.get("k_e"),
        )
        gamma0 = resolve_gamma0_axis(
            lf0=model_params.get("lf0"),
            Gamma_0_core_avg=model_params.get("Gamma_0_core_avg"),
            jet_type=jet_type,
            theta_c=theta_c,
            k_g=model_params.get("k_g"),
        )
        blast_wave = BlastWaveModel(e_iso52, float(model_params["n017"]), float(model_params["k"]), ref=1.0e17)
        t_decel_days = float(blast_wave.decel_time(gamma0) / DAY2SEC)
        radii = np.asarray(blast_wave.shock_radius(float(model_params.get("z", 0.0)), np.asarray(times, dtype=float), t_decel_days), dtype=float)
        if not np.all(np.isfinite(radii)) or np.any(radii <= 0.0):
            raise ValueError("Dynamical walker radius extent is non-finite.")
        return radii

    def _dynamical_walker_radius_grid(self, start, stop, model_params):
        """Return a display grid through each walker's fitted time extent."""
        start_time = max(float(start), 1.0e-12)
        end_time = max(float(model_params.get("tj") or stop), start_time * 1.01)
        return self._blast_wave_radii(np.geomspace(start_time, end_time, 500), model_params)

    def _dynamical_observed_shell_radius_grid(self, start, stop, model_params):
        """Use dynamical radii at the first and last observed epochs."""
        start_time = max(float(start), 1.0e-12)
        stop_time = max(float(stop), start_time * 1.01)
        radii = self._blast_wave_radii(np.asarray([start_time, stop_time]), model_params)
        return np.geomspace(float(np.min(radii)), float(np.max(radii)), 500)

    def model(self, times, params, loc):
        """
        Models the blast wave radii, densities, and
        power-law indices.

        Parameters
        ----------
        times : np.ndarray
            Times since trigger [days].

        params : dict
            The model parameters.

        loc : str, {'dist', 'best'}
            Where to store the modeled values.
        """
        model = self.afterglow_model(**params, **self.afterglow_model_kw)

        # Calculate the radii
        n_eff, k_eff = model.smooth(times)
        radii = model.radii(times)

        # Store the interesting values
        self.r[loc].append(radii)
        self.n0[loc].append(n_eff)
        self.k[loc].append(k_eff)
        self.r_ref[loc].append(model.ref_radius)

    def plot_profile(self, out_dir=None):
        """
        Plots the profiles.

        Parameters
        ----------
        out_dir : Path or str, optional
            The directory to output the plots.
        """
        self.plot_k(out_dir)
        self.plot_n(out_dir)
        self.plot_n0(out_dir)
        self.plot_observed_shell_mass_posterior(out_dir)

    @staticmethod
    def _density_curve(radius, n0, slope, r_ref):
        return np.asarray(n0, dtype=float) * (np.asarray(radius, dtype=float) / float(r_ref)) ** -np.asarray(slope, dtype=float)

    def _observed_shell_rows(self):
        rows = []
        profiles = self.observed_shell['dist'] or zip(
            self.r['dist'], self.n0['dist'], self.k['dist'], self.r_ref['dist'], strict=True
        )
        for walker_index, (radius, n0, slope, r_ref) in enumerate(profiles):
            radius = np.asarray(radius, dtype=float)
            n0 = np.asarray(n0, dtype=float)
            slope = np.asarray(slope, dtype=float)
            if n0.size and slope.size and np.allclose(n0, n0[0]) and np.allclose(slope, slope[0]):
                properties = powerlaw_density_shell_properties(radius[0], radius[-1], n0[0], slope[0], r_ref)
            else:
                density = self._density_curve(radius, n0, slope, r_ref)
                properties = density_shell_properties(radius, density)
            if properties is None:
                continue
            mid_radius = np.sqrt(properties["r_inner_cm"] * properties["r_outer_cm"])
            slope_at_mid = float(np.interp(mid_radius, radius, slope))
            rows.append({"walker_index": walker_index, "k_at_geometric_midpoint": slope_at_mid, **properties})
        return rows

    def _best_observed_shell(self):
        if self.observed_shell['best']:
            radius, n0, slope, r_ref = self.observed_shell['best'][0]
        elif self.r['best']:
            radius, n0, slope, r_ref = self.r['best'][0], self.n0['best'][0], self.k['best'][0], self.r_ref['best'][0]
        else:
            return None
        radius = np.asarray(radius, dtype=float)
        n0 = np.asarray(n0, dtype=float)
        slope = np.asarray(slope, dtype=float)
        if n0.size and slope.size and np.allclose(n0, n0[0]) and np.allclose(slope, slope[0]):
            properties = powerlaw_density_shell_properties(radius[0], radius[-1], n0[0], slope[0], r_ref)
        else:
            density = self._density_curve(radius, n0, slope, r_ref)
            properties = density_shell_properties(radius, density)
        if properties is None:
            return None
        mid_radius = np.sqrt(properties["r_inner_cm"] * properties["r_outer_cm"])
        properties["k_at_geometric_midpoint"] = float(np.interp(
            mid_radius, radius, slope
        ))
        return properties

    def plot_observed_shell_mass_posterior(self, out_dir=None):
        """Write/plot the observed radial-shell mass for every terminal walker."""
        if out_dir is None:
            return
        out_dir = Path(out_dir)
        rows = self._observed_shell_rows()
        if not rows:
            raise RuntimeError("No finite observed-shell density mass values were available.")
        best = self._best_observed_shell()
        csv_path = out_dir / "density_shell_mass_walkers.csv"
        fields = [
            "walker_index", "r_inner_cm", "r_outer_cm", "shell_volume_cm3",
            "shell_mass_g", "shell_mass_msun", "mean_mass_density_g_cm3",
            "mean_number_density_cm3", "k_at_geometric_midpoint",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

        mass = np.asarray([row["shell_mass_msun"] for row in rows], dtype=float)
        density = np.asarray([row["mean_number_density_cm3"] for row in rows], dtype=float)
        mass_density = np.asarray([row["mean_mass_density_g_cm3"] for row in rows], dtype=float)
        slopes = np.asarray([row["k_at_geometric_midpoint"] for row in rows], dtype=float)
        log_mass = np.log10(mass)
        log_density = np.log10(density)
        finite = np.isfinite(log_mass) & np.isfinite(log_density)
        if finite.sum() < 2:
            raise RuntimeError("Observed-shell mass posterior has fewer than two finite walkers.")
        log_mass = log_mass[finite]
        log_density = log_density[finite]
        slopes = slopes[finite]

        summary = {
            "method_version": DENSITY_SHELL_METHOD_VERSION,
            "definition": "spherical hydrogen shell mass and volume-averaged hydrogen number density over first-to-last observed epoch",
            "mass_equation": "4*pi*m_p*integral(n(r)*r^2 dr)",
            "mean_mass_density_equation": "mass / ((4*pi/3)*(r_outer^3-r_inner^3))",
            "mean_number_density_equation": "mass / (m_p * (4*pi/3)*(r_outer^3-r_inner^3))",
            "radius_method": "analytic relativistic blast-wave radius using fitted E_iso, n017, k, and Gamma_0",
            "walker_count": int(len(log_mass)),
            "mass_msun_percentiles_16_50_84": [float(x) for x in np.percentile(10.0 ** log_mass, [16, 50, 84])],
            "mean_mass_density_g_cm3_percentiles_16_50_84": [float(x) for x in np.percentile(mass_density[finite], [16, 50, 84])],
            "mean_number_density_cm3_percentiles_16_50_84": [float(x) for x in np.percentile(10.0 ** log_density, [16, 50, 84])],
        }
        if best is not None:
            summary["minimized_solution"] = best
        (out_dir / "density_shell_mass_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

        fig, ax = plt.subplots(figsize=(8.2, 5.3))
        ax.hist(log_mass, bins="auto", color="tab:blue", histtype="step", lw=1.8)
        if best is not None and best["shell_mass_msun"] > 0.0:
            ax.axvline(np.log10(best["shell_mass_msun"]), color="tab:orange", lw=1.8, label="minimized")
            ax.legend(loc="best")
        ax.set_xlabel(r"$\log_{10}(M_{\rm shell}/M_\odot)$")
        ax.set_ylabel("Terminal-walker count")
        ax.grid(alpha=0.25)
        apply_plot_title(fig, "Observed-Shell Density Mass Posterior", y=0.98, top=0.86)
        self.save_profile_plot("density_shell_mass_histogram", out_dir, dpi=220)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8.2, 5.3))
        ax.hist(log_density, bins="auto", color="tab:green", histtype="step", lw=1.8)
        if best is not None and best["mean_number_density_cm3"] > 0.0:
            ax.axvline(np.log10(best["mean_number_density_cm3"]), color="tab:orange", lw=1.8, label="minimized")
            ax.legend(loc="best")
        ax.set_xlabel(r"$\log_{10}\langle n_{\rm H}\rangle$ [atoms cm$^{-3}$]")
        ax.set_ylabel("Terminal-walker count")
        ax.grid(alpha=0.25)
        apply_plot_title(fig, "Observed-Shell Mean Hydrogen Number-Density Posterior", y=0.98, top=0.86)
        self.save_profile_plot("density_shell_density_histogram", out_dir, dpi=220)
        plt.close(fig)

        import corner

        n017 = np.asarray([self.n0['dist'][row['walker_index']][0] for row in rows], dtype=float)[finite]
        corner_fig = corner.corner(
            np.column_stack([log_mass, log_density, np.log10(n017), slopes]), bins=30,
            labels=[r"$\log_{10}(M_{\rm shell}/M_\odot)$", r"$\log_{10}\langle n_{\rm H}\rangle$ [atoms cm$^{-3}$]", r"$\log_{10} n_{17}$ [atoms cm$^{-3}$]", r"$k$"],
            color="tab:blue", plot_density=True, plot_contours=True,
            levels=(0.68, 0.95), show_titles=True, title_fmt=".3f",
        )
        if best is not None and best["shell_mass_msun"] > 0.0 and best["mean_number_density_cm3"] > 0.0:
            axes = np.asarray(corner_fig.axes).reshape((4, 4))
            axes[1, 0].plot(
                np.log10(best["shell_mass_msun"]), np.log10(best["mean_number_density_cm3"]),
                marker="*", color="tab:orange", ms=10, label="minimized",
            )
            axes[1, 0].legend(loc="best", fontsize=8)
        apply_plot_title(corner_fig, "Observed-Shell Mass, Mean Hydrogen Number Density, n17, and k", y=0.99, top=0.88)
        self.save_profile_plot("density_shell_mass_corner", out_dir, dpi=220)
        plt.close(corner_fig)

        fig, ax = plt.subplots(figsize=(7.4, 5.5))
        scatter = ax.scatter(log_mass, log_density, c=slopes, cmap="coolwarm", s=30, alpha=0.82, edgecolor="none")
        if best is not None and best["shell_mass_msun"] > 0.0 and best["mean_number_density_cm3"] > 0.0:
            ax.plot(np.log10(best["shell_mass_msun"]), np.log10(best["mean_number_density_cm3"]), marker="*", color="black", ms=12, label="minimized")
            ax.legend(loc="best")
        colorbar = fig.colorbar(scatter, ax=ax)
        colorbar.set_label(r"$k$ at shell geometric midpoint")
        ax.set_xlabel(r"$\log_{10}(M_{\rm shell}/M_\odot)$")
        ax.set_ylabel(r"$\log_{10}\langle n_{\rm H}\rangle$ [atoms cm$^{-3}$]")
        ax.grid(alpha=0.25)
        apply_plot_title(fig, "Observed-Shell Mass versus Mean Hydrogen Number Density", y=0.98, top=0.86)
        self.save_profile_plot("density_shell_mass_scatter", out_dir, dpi=220)
        plt.close(fig)

    @staticmethod
    def add_radius_pc_axis(ax):
        """Add a parsec axis above a radius-in-cm profile plot."""
        ax2 = ax.secondary_xaxis('top', functions=(cm_to_pc, pc_to_cm))
        ax2.set_xlabel("Radius [pc]", labelpad=8)
        ax2.tick_params(axis='x', top=True, bottom=False, labelsize=8)
        ax.tick_params(axis='x', top=False, bottom=True)
        return ax2

    @staticmethod
    def save_profile_plot(stem, out_dir, dpi):
        """Overwrite canonical profile products in both PDF and PNG form."""
        if out_dir:
            output = Path(out_dir)
            plt.savefig(output / f"{stem}.pdf", dpi=dpi, bbox_inches="tight", pad_inches=0.04)
            plt.savefig(output / f"{stem}.png", dpi=220, bbox_inches="tight", pad_inches=0.04)

    @staticmethod
    def apply_legacy_profile_ylim(ax, curves, best, *, log_scale):
        """Match the pre-all-walker visual scale without discarding curves."""
        values = np.concatenate([np.ravel(np.asarray(curve, dtype=float)) for curve in [*curves, best]])
        values = values[np.isfinite(values)]
        if log_scale:
            values = values[values > 0.0]
            if values.size < 2:
                return
            log_values = np.log10(values)
            lo, hi = np.quantile(log_values, [0.01, 0.99])
            # Keep the lower framing robust, but never crop a real high-side
            # walker excursion: every plotted density curve must remain visible.
            hi = max(hi, float(np.max(log_values)))
            span = max(hi - lo, 0.5)
            ax.set_ylim(10.0 ** (lo - 0.08 * span), 10.0 ** (hi + 0.08 * span))
            return
        if values.size < 2:
            return
        lo, hi = np.quantile(values, [0.01, 0.99])
        hi = max(hi, float(np.max(values)))
        span = max(hi - lo, 0.5)
        ax.set_ylim(lo - 0.08 * span, hi + 0.08 * span)

    def plot_n(self, out_dir=None):
        """"
        Plots the density profile.

        Parameters
        ----------
        out_dir : Path or str, optional
            The directory to output the plot.
        """
        dist = []

        for i in range(len(self.n0['dist'])):
            dist.append(
                np.array(self.n0['dist'][i]) *
                (np.array(self.r['dist'][i]) / np.array(self.r_ref['dist'][i])) ** -np.array(self.k['dist'][i])
            )

        best = (
            np.array(self.n0['best'][0]) *
            (np.array(self.r['best'][0]) / np.array(self.r_ref['best'][0])) ** -np.array(self.k['best'][0])
        )

        ax = self.plot(
            self.r['dist'], dist,
            self.r['best'][0], best
        )
        self.apply_legacy_profile_ylim(ax, dist, best, log_scale=True)

        # ax.axvline(self.r_ref['best'][0], **self.r_ref_options)
        # ax.set_title(r'Number Density Profile')
        ax.set_ylabel(r'n [cm$^{-3}$]')
        ax.set_xlabel('Radius [cm]')
        self.add_radius_pc_axis(ax)
        apply_plot_title(plt.gcf(), "Number Density Profile", y=0.99, top=0.78)

        self.save_profile_plot('n_profile', out_dir, dpi=800)
        plt.close()

    def plot_n0(self, out_dir=None):
        """"
        Plots the density normalization profile.

        Parameters
        ----------
        out_dir : Path or str, optional
            The directory to output the plot.
        """
        ax = self.plot(
            self.r['dist'], self.n0['dist'],
            self.r['best'][0], self.n0['best'][0]
        )
        self.apply_legacy_profile_ylim(ax, self.n0['dist'], self.n0['best'][0], log_scale=True)

        ax.axvline(self.r_ref['best'][0], **self.r_ref_options)
        ax.set_ylabel(r'$n_{0,ref} [cm^{-3}]$')
        ax.set_xlabel(r'Radius [cm]')
        self.add_radius_pc_axis(ax)
        apply_plot_title(plt.gcf(), "Density Normalization Profile", y=0.99, top=0.78)

        self.save_profile_plot('n0_profile', out_dir, dpi=1200)
        plt.close()

    def plot_k(self, out_dir=None):
        """"
        Plots the effective density slope profile.

        Parameters
        ----------
        out_dir : Path or str, optional
            The directory to output the plot.
        """
        ax = self.plot(
            self.r['dist'], self.k['dist'],
            self.r['best'][0], self.k['best'][0],
            log_scale=False
        )
        self.apply_legacy_profile_ylim(ax, self.k['dist'], self.k['best'][0], log_scale=False)

        self.add_radius_pc_axis(ax)
        ax.axvline(self.r_ref['best'][0], **self.r_ref_options)
        # ax.set_title('Power-Law Index Profile')
        ax.set_ylabel(r'Effective Slope $k_{eff}$')
        ax.set_xlabel(r'Radius [cm]')
        ax.set_xscale('log')
        apply_plot_title(plt.gcf(), "Effective Density Slope Profile", y=0.99, top=0.78)

        self.save_profile_plot('k_profile', out_dir, dpi=1200)
        plt.close()
# </editor-fold>
