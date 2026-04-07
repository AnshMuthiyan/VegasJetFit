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
)
from jetfit.models.base import has_fts_transition, RadiationModel, SpectralIndexModel
from jetfit.models.fireball import StratifiedFireballModel
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
    out_dir=None,
    output_path=None,
    ncurves=10,
    nfreq=400,
):
    """
    Plot a VegasAfterglow-style spectrum-timeseries figure for the
    best-fit parameter set from a completed Ampy object.

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
    model_kw=None,
    out_dir=None,
    output_path=None,
    ncurves=10,
    nfreq=400,
):
    """
    Plot stacked instantaneous spectra across the observed time span.

    This is the VegasAfterglow-style frequency-vs-flux figure useful for
    inspecting the sharpness of spectral breaks.
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
    nu = _spectrum_frequency_grid(obs, model_obj, times, nfreq=max(100, int(nfreq)))

    fig, ax = plt.subplots(figsize=(10, 7.5))
    colors = plt.cm.viridis(np.linspace(0.02, 0.98, len(times)))

    for color, time_days in zip(colors, times):
        fts = _fts_flag(model_obj, time_days)
        flux_mjy = np.asarray(model_obj.spectral_flux(time_days, nu, fts=fts), dtype=float).reshape(-1)
        flux_cgs = flux_mjy * 1e-26
        mask = np.isfinite(flux_cgs) & (flux_cgs > 0.0)
        if not mask.any():
            continue
        ax.loglog(
            nu[mask],
            flux_cgs[mask],
            color=color,
            linewidth=1.6,
            label=_format_seconds_label(time_days),
        )

    tref = float(np.sqrt(times[0] * times[-1]))
    ref_spectrum = model_obj.spectrum(np.atleast_1d(tref))
    for key, color in (("nu_a", "tab:blue"), ("nu_m", "tab:orange"), ("nu_c", "tab:green")):
        values = np.atleast_1d(ref_spectrum.get(key, np.array([])))
        if values.size == 0:
            continue
        value = float(values.flat[0])
        if np.isfinite(value) and value > 0.0:
            ax.axvline(value, color=color, linestyle="--", linewidth=2.0, alpha=0.9)

    ax.set_title("Synchrotron Spectra")
    ax.set_xlabel("frequency (Hz)")
    ax.set_ylabel(r"flux density (erg/cm$^2$/s/Hz)")
    ax.grid(alpha=0.25, which="both")
    ax.legend(loc="lower left", frameon=True, fancybox=False, framealpha=0.9)
    fig.tight_layout()
    apply_plot_run_label(fig)

    if output_path is not None:
        fig.savefig(output_path, dpi=300)
    elif out_dir is not None:
        save_plot_unique("spectrum_timeseries", "pdf", str(out_dir), dpi=300)

    plt.close(fig)


def plot_frequencies(chain, log_prob, obs, params, model, model_kw=None, best=None, out_dir=None):
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
    fp = FrequencyPlotter(chain, log_prob, params, model, model_kw)
    fp.plot_all(obs, best=best, out_dir=out_dir)
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
        return

    try:
        profiler = DensityProfiler(chain, log_prob, params, model, model_kw)
        profiler.profile(obs.times().min(), obs.times().max(), best_params=best)
        profiler.plot_profile(out_dir)
        plt.close()
    except Exception as exc:
        print(
            f"WARNING: Density profile plotting failed for model "
            f"'{model.__name__}': {type(exc).__name__}: {exc}"
        )


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
    if ((model.x_range[0] < wn) & (wn < model.x_range[1])).all():
        return model.extinguish(wn, Ebv=ebv_sf)
    return 1.0


def model_host_contamination(bands, hosts):
    """ Additive host galaxy contamination. """
    if hosts is None:
        return 1.0
    return np.array([hosts.get(b + '_host') or 0.0 for b in bands])


def model_galactic_extinction(wn, model, ebv_mw, rv=None):
    """ Multiplicative Galactic dust extinction. """
    if ((model.x_range[0] < wn) & (wn < model.x_range[1])).all():
        if rv is not None:
            model = model.__class__(Rv=rv)
        return model.extinguish(wn, Ebv=ebv_mw)
    return 1.0


def spread_data(flux, band, spread):
    """ Multiplicative offset. """
    for key, val in spread.items():
        flux[band == key] *= val
    return flux


def get_offset(d, data, offsets, positions):
    """"""
    for key, vals in positions.items():
        if d in data[vals]:
            return 10.0 ** (0.4 * offsets.get(key))
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
                    fmt='.', markersize=3.0, elinewidth=0.5, color='grey', alpha=0.5
                )

            # Plot modeled data as usual
            if mask.any():
                e = np.atleast_1d(plot_data[sb]['error'])[mask]
                x = np.atleast_1d(plot_data[sb]['time'])[mask]
                y = np.atleast_1d(plot_data[sb]['flux'])[mask]

                ax.errorbar(
                    x, y, yerr=e, fmt='.', markersize=3.0,
                    elinewidth=0.5, label=label, **OPTION_MAP[sb]
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

    nu_m = afterglow_model.nu_m(t)
    nu_c = afterglow_model.nu_c(t)
    nu_a = model_nu_a(afterglow_model, t, nu_m, nu_c)

    return nu_m, nu_c, nu_a


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
    def __init__(self, chain, log_prob, params, model, model_kw=None):
        super().__init__(chain, log_prob, params)
        self.model = model
        self.model_kw = model_kw

        self.samples = self.draw()

        self.axes = None
        self._set_axes()

    def _set_axes(self) -> None:
        """ Set plot axes. """
        fig, axes = plt.subplots(2,1, figsize=(8, 8), sharex=True)
        fig.subplots_adjust(hspace=0)

        # ax.set_title('Critical Frequencies')
        axes[1].set_xlabel('Time Since Trigger [days]', fontsize=16)
        axes[0].set_ylabel('Frequency [Hz]', fontsize=16)
        axes[1].set_ylabel('Spectral Index', fontsize=16)

        # Define secondary axis
        # ax2 = axes[0].secondary_xaxis('top', functions=(days_to_sec, sec_to_days))
        # ax2.set_xlabel("Time Since Trigger [seconds]", labelpad=10)
        # ax2.xaxis.set_ticks_position('none')
        # ax2.tick_params(axis='x', top=True, bottom=False)
        # axes[0].tick_params(axis='x', top=False, bottom=True)
        self.axes = axes
        self.fig = fig

    def plot_all(self, obs, best=None, out_dir=None):
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
            epoch.min() / 2, epoch.max() * 2, num=200
        )

        # Plot the frequencies
        self.plot_dist(times, best)
        self.plot_data(obs)
        self.plot_indices(obs, best, times)

        self.axes[1].set_xlim(times.min(), times.max())

        if out_dir is not None:
            save_plot_unique('frequencies', 'pdf', str(out_dir))

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

        # Plot AMPy medians
        for j, index in enumerate(obs.data[obs.sindex_loc]):

            for i, s in enumerate(self.samples):
                p = self.params.samples_to_dict(s)
                model = self.model(**p.get('model'), **(self.model_kw or {}))
                index_spectrum = model.spectrum(times)

                # Is there a fast-to-slow transition?
                fts = False

                if not isinstance(model, JetSimpy):
                    full_spectrum = model.spectrum(obs.times())
                    fts = has_fts_transition(full_spectrum['nu_m'], full_spectrum['nu_c'])

                # Model the spectral index
                modeled = SpectralIndexModel(**index_spectrum).evaluate(
                    index.int_range.lower.to_value('Hz'), index.int_range.upper.to_value('Hz'), fts=fts
                )

                self.axes[1].plot(times, modeled, alpha=0.2, color='royalblue', label='AMPy' if (j==0 and i==0) else None)

            self.axes[1].errorbar(
                index.time.to_value('d'), index.value.value,
                yerr=((index.uncertainty.lower.value,), (index.uncertainty.lower.value,)),
                fmt='o', linestyle='none', capsize=3, color='black', zorder=999, label='XRT' if j==0 else None
            )
        self.axes[1].legend(loc='best')

        handles, labels = [], []
        h, l = self.axes[0].get_legend_handles_labels()
        handles.extend(h)
        labels.extend(l)

        num_entries = len(labels)
        desired_rows = 4
        ncol = int((num_entries + desired_rows - 1) // desired_rows)

        # Reserve headroom for the band legend and keep the legend fully inside
        # the figure canvas so PDF exports do not clip the top section.
        self.fig.tight_layout(rect=[0, 0, 1, 0.86])
        self.fig.legend(
            handles, labels,
            loc='upper center',
            bbox_to_anchor=(0.5, 0.995),
            ncol=max(1, ncol),
            frameon=True,
            fancybox=False,
            edgecolor='black',
            borderaxespad=0.2,
        )

    def plot_dist(self, times, best=None, nsamps=None):
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

        # Model the frequencies for each randomly sampled set
        for sample in samples:
            params = self.params.samples_to_dict(sample, cat='model')

            nu_m, nu_c, nu_a = model_freqs(
                self.model, times, params, **(self.model_kw or {})
            )

            # Plot the critical frequencies
            if nu_a is not None:
                self.axes[0].loglog(times, nu_a, color='tab:green', alpha=0.1)

            self.axes[0].loglog(times, nu_m, color='tab:blue', alpha=0.1)
            self.axes[0].loglog(times, nu_c, color='tab:orange', alpha=0.1)

        self.plot_best(times, best)

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
            self.axes[0].loglog(times, best_nu_as, color='tab:green', linewidth=2, label=r'$\nu_a$')

        self.axes[0].loglog(times, best_nu_ms, color='tab:blue', linewidth=2,   label=r'$\nu_m$')
        self.axes[0].loglog(times, best_nu_cs, color='tab:orange', linewidth=2, label=r'$\nu_c$')

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

            self.axes[0].scatter(plot_data[x]['t'], plot_data[x]['nu'], label=band, **OPTION_MAP[x])

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
            Number of samples to draw.

        best_params : dict, optional
        """
        samples = self.draw(nsamps)

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

        # ax.axvline(self.r_ref['best'][0], **self.r_ref_options)
        # ax.set_title(r'Number Density Profile')
        ax.set_ylabel(r'n [cm$^{-3}$]')
        ax.set_xlabel('Radius [cm]')

        if out_dir:
            save_plot_unique('n_profile', 'pdf', str(out_dir), dpi=800)
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

        ax.axvline(self.r_ref['best'][0], **self.r_ref_options)
        ax.set_title(r'Number Density Normalization Profile')
        ax.set_ylabel(r'$n_{0,ref} [cm^{-3}]$')
        ax.set_xlabel(r'Radius [cm]')

        if out_dir:
            save_plot_unique('n0_profile', 'pdf', str(out_dir), dpi=1200)
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

        # Define secondary axis
        ax2 = ax.secondary_xaxis('top', functions=(cm_to_pc, pc_to_cm))
        ax2.set_xlabel("Radius [pc]", labelpad=10)
        ax2.xaxis.set_ticks_position('none')
        ax2.tick_params(axis='x', top=True, bottom=False)
        ax.tick_params(axis='x', top=False, bottom=True)

        ax.axvline(self.r_ref['best'][0], **self.r_ref_options)
        # ax.set_title('Power-Law Index Profile')
        ax.set_ylabel(r'Effective Slope $k_{eff}$')
        ax.set_xlabel(r'Radius [cm]')
        ax.set_xscale('log')

        if out_dir:
            save_plot_unique('k_profile', 'pdf', str(out_dir), dpi=1200)
        plt.close()
# </editor-fold>


















