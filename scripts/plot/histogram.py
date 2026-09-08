import numpy as np
import matplotlib

matplotlib.use('Agg', force=True)
from matplotlib import pyplot as plt

from jetfit.core.utils import save_plot_unique, apply_plot_title
from jetfit.models.base import SpectralIndexModel, has_fts_transition, OpeningAngleModel
from jetfit.models.jetsim import JetSimpy
from scripts.plot.base import Profiler


def plot_spectral_indices_ampy(ampy, out_dir=None):
    """
    Plot the spectral indices from a completed Ampy object.

    Parameters
    ----------
    ampy : Ampy
        The completed Ampy object.

    out_dir : Path, optional
        The output directory.
    """
    plot_spectral_indices(
        ampy.mcmc.sampler.get_chain(flat=True),
        ampy.mcmc.sampler.get_log_prob(flat=True),
        ampy.obs, ampy.mcmc.params, ampy.afterglow_model,
        model_kw=ampy.mcmc.models.afg_kw, out_dir=out_dir
    )


def plot_jet_correction_ampy(ampy, out_dir=None):
    """
    Plot the beam-corrected quantities.

    Parameters
    ----------
    ampy : Ampy
        The completed Ampy object.

    out_dir : Path
        The output directory.
    """
    if ampy.afterglow_model.__name__ == 'FireballModel':
        plot_jet_correction(
            ampy.mcmc.sampler.get_chain(flat=True),
            ampy.mcmc.sampler.get_log_prob(flat=True),
            ampy.mcmc.params, out_dir=out_dir,
            ref=ampy.mcmc.models.afg_model.ref_radius
        )


def plot_spectral_indices(chain, log_prob, obs, params, model, model_kw=None, out_dir=None, best=None):
    """
    Plot the spectral indices from a completed MCMC sampler object.

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

    out_dir : Path, optional
        The output directory.

    best : dict, optional
    """
    plotter = SpectralIndexPlot(chain, log_prob, params, obs, model, model_kw)
    plotter.model(obs.data[obs.sindex_loc], out_dir=out_dir, best_params=best)
    plt.close()


def plot_jet_correction(chain, log_prob, params, ref, out_dir=None):
    """
    Plot the beam-corrected quantities.

    Parameters
    ----------
    chain :

    log_prob :

    params : Parameters
        The model parameters.

    out_dir : Path
        The output directory.
    """
    if params.has('tj'):
        plotter = Beaming(chain, log_prob, params)
        plotter.beaming(out_dir=out_dir, ref=ref)
        plt.close()


# <editor-fold desc="Spectral Index">
class SpectralIndexPlot(Profiler):
    """
    Models a distribution of spectral indexes and provides
    methods to generates plots.

    Parameters
    ----------
    params : Parameters
        The model parameters.

    obs : Observation
        The observational data.

    model :
        The afterglow model class.

    chain : , optional
        The chain.

    model_kw : dict
        Any kwargs used in ``model`` constructor.
    """
    def __init__(self, chain, log_prob, params, obs, model, model_kw=None):
        super().__init__(chain, log_prob, params)
        self.afterglow_model = model
        self.model_kw = model_kw or {}
        self.obs = obs

    def evaluate(self, time, lower, upper, nsamps=100, samples=None):
        """
        Evaluates the spectral index model for each
        randomly drawn set of parameters from the
        sampler.

        Parameters
        ----------
        time : float
            The time to evaluate [d].

        lower : float
            The lower integration bound [Hz].

        upper : float
            The upper integration bound [Hz].

        samples : np.ndarray, optional
            The number of samples to use.

        nsamps : int, optional, default=100
            Number of samples to draw.

        Returns
        -------
        np.ndarray
            The evaluated spectral index values.
        """
        if samples is None:
            samples = self.draw(nsamps)

        modeled = np.full(len(samples), np.nan)

        for i, s in enumerate(samples):
            p = self.params.samples_to_dict(s)

            model = self.afterglow_model(**p.get('model'))
            index_spectrum = model.spectrum(time)

            # Is there a fast-to-slow transition?
            fts = False

            if not isinstance(model, JetSimpy):
                full_spectrum = model.spectrum(self.obs.times())
                fts = has_fts_transition(full_spectrum['nu_m'], full_spectrum['nu_c'])

            # Model the spectral index
            modeled[i] = SpectralIndexModel(**index_spectrum).evaluate(
                lower, upper, fts=fts
            )

        return modeled

    def evaluate_best(self, time, lower, upper, best=None):
        """
        Evaluates the spectral index model using the
        maximum likelihood values.

        Parameters
        ----------
        time : float
            The time to evaluate [d].

        lower : float
            The lower integration bound [Hz].

        upper : float
            The upper integration bound [Hz].

        best : dict, optional

        Returns
        -------
        float
            The most likely spectral index value.
        """
        if best is None:
            best = self.best(cat='model').get('model')

        model = self.afterglow_model(**best)
        index_spectrum = model.spectrum(time)

        # Is there a fast-to-slow transition?
        fts = False

        if not isinstance(model, JetSimpy):
            full_spectrum = model.spectrum(self.obs.times())
            fts = has_fts_transition(full_spectrum['nu_m'], full_spectrum['nu_c'])

        # Model the spectral index
        return SpectralIndexModel(**index_spectrum).evaluate(
            lower, upper, fts=fts
        )

    def model(self, indices, out_dir=None, best_params=None):
        """
        Calculates and plots the spectral index distribution
        for each provided spectral index.

        Parameters
        ----------
        indices : array_like of `SpectralIndex`
            The `SpectralIndex` objects to model using
            the randomly sampled values.

        out_dir : Path, optional
            The output directory to save the figures.

        best_params : dict, optional
        """
        for index in indices:

            # Convert to floats with expected units
            time = index.time.to_value('d')
            lower = index.int_range.lower.to_value('Hz')
            upper = index.int_range.upper.to_value('Hz')

            # Get a distribution of values and the best value
            best = self.evaluate_best(time, lower, upper, best_params)
            distribution = self.evaluate(time, lower, upper)

            # Create the various AMAZING plots
            self.plot_hist(distribution, best, index, time, out_dir=out_dir)

    def plot_hist(self, dist, best, truth, time, out_dir=None):
        """
        Plots the distribution of spectral index values.
        Over-plots with the best fit value and truth value.

        Parameters
        ----------
        dist : np.ndarray
            The distribution of spectral indices.

        best : float
            The best fit spectral index.

        truth : SpectralIndex
            The accepted spectral index.

        time : float
            The time of the measurement.

        out_dir : Path, optional
            The directory to save the figures.
        """
        self.plot_distribution(dist)
        self.plot_best(best)

        self.plot_truth(
            truth.value.value,
            truth.uncertainty.lower.value,
            truth.uncertainty.upper.value,
        )

        # Configure the plot
        apply_plot_title(plt.gcf(), f'Spectral Index Distribution, t = {round(time, 2)} days', y=0.98, top=0.88)
        plt.xlabel('Spectral Index')
        plt.ylabel('Count')
        plt.legend()
        plt.grid(alpha=0.3)

        if out_dir is not None:
            save_plot_unique('index_dist', 'pdf', str(out_dir), dpi=400)
        plt.close()

    @staticmethod
    def plot_truth(val, l, up, **kwargs):
        """
        Over-plots the accepted value.

        Parameters
        ----------
        val : float
            The spectral index value.

        l: float
            The lower uncertainty range.

        up: float
            The upper uncertainty range.

        kwargs
            Any kwargs accepted by `plt.axvline`.
        """

        options = {
            'color': 'tab:purple',
            'linewidth': 2,
            'linestyle': '--',
        } | kwargs

        plt.axvline(val, label='XRT', **options)

        # Plot the uncertainty as a shaded region
        plt.axvspan(val - l, val + up, color=options.get('color'), alpha=0.2)

    @staticmethod
    def plot_best(val, **kwargs):
        """
        Over-plots the best fit value.

        Parameters
        ----------
        val : float
            The spectral index value.

        kwargs
            Any kwargs accepted by `plt.axvline`.
        """

        options = {
            'color': 'red',
            'linewidth': 2,
            'linestyle': '--'
        } | kwargs

        val = round(val, 4)

        plt.axvline(val, label='Minimized', **options)

    @staticmethod
    def plot_distribution(dist, **kwargs):
        """
        Over-plots the accepted value.

        Parameters
        ----------
        dist : np.ndarray
            The distribution of spectral index values.

        kwargs
            Any kwargs accepted by `plt.hist`.
        """

        options = {
            'facecolor': '#2ab0ff',
            'edgecolor': '#169acf',
            'bins': 'auto',
            'linewidth': 0.5,
            'alpha': 0.5,
        } | kwargs
        # plt.figure(figsize=(10, 6))
        cts, bins, _ = plt.hist(dist, **options)
# </editor-fold>


# <editor-fold desc="Beaming Correction">
class Beaming(Profiler):
    """
    Models beam-corrected quantities.

    Parameters
    ----------

    params : Parameters
        The model parameters.
    """
    def __init__(self, chain, log_prob, params):
        super().__init__(chain, log_prob, params)

    def beaming(self, out_dir=None, ref=1e17):
        """
        Calculates and plots the corrected energy and
        opening angle distributions.

        Parameters
        ----------
        out_dir : Path, optional
            The output directory to save the figures.
        """
        samples = self.draw(nsamps=100)

        angles = np.full(len(samples), np.nan)
        energies = np.full(len(samples), np.nan)

        # Calculate the distribution of values
        for i, samp in enumerate(samples):
            samp = self.params.samples_to_dict(samp)['model']

            # Model the jet opening angle
            angles[i] = OpeningAngleModel(
                samp['E52'], samp['n017'], samp['k'], samp['z']
            )(samp['tj'], ref=ref)

            # Calculate the beaming-corrected energy
            energies[i] = (1 - np.cos(angles[i])) * samp['E52']

        # Calculate the most likely opening angle
        best_samp = self.best(cat='model').get('model')

        best_ang = OpeningAngleModel(
            best_samp['E52'], best_samp['n017'], best_samp['k'], best_samp['z']
        )(best_samp['tj'], ref=ref)

        # Calculate the most likely energy
        best_en = (1 - np.cos(best_ang)) * best_samp['E52']

        # Plot the jet opening angle distribution
        title = None

        self.plot_histogram(
            angles, round(best_ang, 3), title,
            'Jet Opening Angle [rad]', 'angle_dist', out_dir
        )
        plt.close()

        self.plot_histogram(
            np.log10(energies), round(np.log10(best_en), 3), title,
            r'$\log_{10}E_{j, 52}$ [erg]', 'energy_dist', out_dir
        )

    @staticmethod
    def plot_histogram(dist, best, title=None, x_label=None, fn=None, out_dir=None):
        """
        Plots the spectral index distribution.

        Parameters
        ----------
        dist : np.ndarray
            The distribution of spectral indices.

        best : float
            The modeled spectral index using the highest
            likelihood set of parameters.

        title : str, optional
            The title of the plot.

        x_label : str, optional
            The x-axis label.

        fn : str, optional
            The output filename.

        out_dir : str or Path, optional
            The output directory to save the figures.
        """
        cts, bins, _ = plt.hist(  # Plot the value distribution
            dist, bins='auto', facecolor='#2ab0ff',
            edgecolor='#169acf', linewidth=0.5, alpha=0.5
        )

        plt.axvline(  # Plot the best fit value
            best, color='red', linestyle='--',
            linewidth=2, label='Minimized'
        )

        # Configure the plot
        apply_plot_title(plt.gcf(), title, y=0.98, top=0.88)
        plt.xlabel(x_label)
        plt.ylabel('Count')
        plt.legend(loc='best')
        plt.grid(alpha=0.3)

        if out_dir is not None:
            save_plot_unique(fn, 'pdf', str(out_dir), dpi=800)
# </editor-fold>
