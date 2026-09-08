import numpy as np
import matplotlib

matplotlib.use('Agg', force=True)
from matplotlib import pyplot as plt


OPTION_MAP = {
    # JC Optical/NIR (circles)
    'U': {'color': '#8601AF', 'marker': '.'},
    'B': {'color': '#0247FE', 'marker': '.'},
    'V': {'color': '#66B032', 'marker': '.'},
    'R': {'color': '#FE2712', 'marker': '.'},
    'I': {'color': '#4424D6', 'marker': '.'},
    'J': {'color': '#66B032', 'marker': '.'},
    'H': {'color': '#FC600A', 'marker': '.'},
    'K': {'color': '#FE2712', 'marker': '.'},

    # SDSS Optical (squares)
    'u': {'color': 'tab:purple', 'marker': '.'},
    'g': {'color': 'tab:blue',   'marker': '.'},
    'r': {'color': 'tab:orange', 'marker': '.'},
    'i': {'color': 'tab:red',    'marker': '.'},
    'z': {'color': 'tab:pink',   'marker': '.'},

    # Swift Optical/UV/XRAY (diamonds, hexagons)
    'uvot-u': {'color': 'cyan',       'marker': '.'},
    'uvot-b': {'color': 'lightblue',  'marker': '.'},
    'uvot-v': {'color': 'lightgreen', 'marker': '.'},
    'uvw2': {'color': 'pink',         'marker': '.'},
    'uvm2': {'color': 'darkblue',     'marker': '.'},
    'uvw1': {'color': 'green',        'marker': '.'},
    'xray': {'color': 'black',        'marker': '.'},

    # HST
    'F775W': {'color': 'yellow', 'marker': '.'},
    'F125W': {'color': 'grey',   'marker': '.'},

    # Radio
    'C': {'color': 'royalblue', 'marker': '.'},
    'C2': {'color': 'purple', 'marker': '.'},
    'Ka': {'color': 'peachpuff', 'marker': '.'},
    'Kb': {'color': 'peru', 'marker': '.'},
    'Kc': {'color': 'palevioletred', 'marker': '.'},
    'Kd': {'color': 'lightcoral', 'marker': '.'},
    'W': {'color': 'teal', 'marker': '.'},
    'S': {'color': 'teal', 'marker': 'v'},
}

# Aliases
OPTION_MAP['r2'] = OPTION_MAP['r']
OPTION_MAP['i2'] = OPTION_MAP['i']
OPTION_MAP['z2'] = OPTION_MAP['z']
OPTION_MAP['Rc'] = OPTION_MAP['R']
OPTION_MAP['Ic'] = OPTION_MAP['I']
OPTION_MAP['Ks'] = OPTION_MAP['K']
OPTION_MAP['uprime'] = OPTION_MAP['u']
OPTION_MAP['gprime'] = OPTION_MAP['g']
OPTION_MAP['rprime'] = OPTION_MAP['r']
OPTION_MAP['iprime'] = OPTION_MAP['i']
OPTION_MAP['zprime'] = OPTION_MAP['z']


def latex(key: str) -> str:
    """
    Returns LaTeX label for the provided fitting parameter.

    Parameters
    ----------
    key : str
        The parameter name

    Returns
    -------
    str
        The LaTeX formatted ``key`` or just ``key``
    """
    if '_host' in key:
        return r'$log_{10}$(' + f'{key.split('_')[0]}' + r'$_{host}$)'

    if '_offset' in key:
        return r'$\delta_{' + f'{key.split('_')[0]}' r'}$'

    try:
        return {
            'slop': r'$\sigma$',
            'slop_uvot': r'$\sigma_{uvot}$',
            'slop_other': r'$\sigma_{other}$',

            # Jetsimpy
            'Eiso': r'$log_{10}E_{iso}$',
            'lf': r'$log_{10}\Gamma$',
            'theta_c': r'$\theta_c$',
            'theta_v': r'$\theta_v$',
            'A': r'$log_{10}A$',
            'n0': r'$log_{10}n_0$',

            # Stratified Fireball Model
            'n0t': r'$log_{10}n_{0, t}$',
            'rt': r'$log_{10}R_t$',
            'k1': r'$k_{pre}$',
            'k2': r'$k_{post}$',
            'sn': r'$s_n$',
            'sni': r'$s_n^{-1}$',
            'sj': r'$s_j$',
            'sji': r'$s_j^{-1}$',
            'tj': r'$log_{10}t_j$',

            # Generic Fireball Model
            'lf0': r'$log_{10}\Gamma_0$',
            'Gamma_0_core_avg': r'$\log_{10}\bar{\Gamma}_{0,c}$',
            'E52': r'$log_{10}E_{52}$',
            'E_j_52': r'$E_{j,52}$',
            'E_j_core_52': r'$E_{j,c,52}$',
            'E_iso_52': r'$E_{iso,52}$',
            'E_j_tophat_52': r'$E_{j,52}^{core}$',
            'Gamma_0': r'$\Gamma_0$',
            'M_j_g': r'$M_j$ [g]',
            'M_j_msun': r'$M_j/M_\odot$',
            'log10_E_j_52': r'$\log_{10}E_{j,52}$',
            'log10_Gamma_0': r'$\log_{10}\Gamma_0$',
            'log10_M_j_msun': r'$\log_{10}(M_j/M_\odot)$',
            'log10_E_j_core_52': r'$\log_{10}E_{j,c,52}$',
            'log10_Gamma_0_core_avg': r'$\log_{10}\bar{\Gamma}_{0,c}$',
            'log10_M_j_core_msun': r'$\log_{10}(M_{j,c}/M_\odot)$',
            'Omega_2j_pct_4pi': r'$\Omega_{2j}/4\pi$ [%]',
            'eps_e': r'$log_{10}\epsilon_e$',
            'eps_b': r'$log_{10}\epsilon_B$',
            'eps_B': r'$log_{10}\epsilon_B$',
            'rv_milky_way': r'$log_{10}R_{v}^{MW}$',
            'ebv_source_frame': r'$E(B-V)_{sf}$',
            'ebv_milky_way': r'$E(B-V)_{MW}$',
            'n017': r'$log_{10}n_{0, 17}$',
        }[key]
    except KeyError:
        return key


class Profiler:
    """

    Parameters
    ----------


    params : Parameters
        The `Parameter` object used when running the
        MCMC with `sampler`.
    """
    dist_options = {
        'alpha': 0.3, 'linewidth': 0.5,
        'linestyle': '-', 'color': 'tab:purple'
    }

    best_options = {
        'linewidth': 2, 'linestyle': '-',
        'color': 'tab:orange', 'label': 'Minimized'
    }

    def __init__(self, chain, log_prob, params):
        self.chain = chain
        self.log_prob = log_prob
        self.params = params

    def draw(self, nsamps=100):
        """
        Randomly draws `nsamps` sets of samples from
        the `sampler`.

        Parameters
        ----------
        nsamps : int, optional, default=100
            Number of samples to draw.

        Returns
        -------
        np.ndarray
            The randomly drawn sets of sampled values.
        """
        nsamps = int(nsamps)
        if nsamps <= 0:
            return self.chain[:0]
        if nsamps >= len(self.chain):
            return self.chain
        return self.chain[np.random.choice(len(self.chain), size=nsamps, replace=False)]

    def best(self, **kwargs):
        """
        Returns the highest likelihood set of parameters.

        Parameters
        ----------
        kwargs :
            Any args passed to `params.samples_to_dict()`.

        Returns
        -------
        np.ndarray or dict
            The highest likelihood set of parameters.
        """
        params = self.chain[np.nanargmax(self.log_prob)]
        return self.params.samples_to_dict(params, **kwargs)

    def plot(
        self, dist_x, dist_y, best_x=None, best_y=None,
        log_scale=True, dist_kw=None, best_kw=None
    ):
        """
        Creates the plot for an arbitrary distribution.

        Parameters
        ----------
        dist_x, dist_y : array_like of array_like
            The distribution of x, y values.

        best_x, best_y : array_like of float, optional
            The best distribution.

        log_scale : bool, optional, default=True
            Should the plot be in log scale?

        dist_kw, best_kw : dict, optional
            All parameters supported by `plt.plot` for
            the distribution and/or best curves. Defaults
            are `.dist_options` and `.best_options`.

        Returns
        -------
        matplotlib.axes.Axes
            The figure object.
        """
        # _, ax = plt.subplots(figsize=(10, 6))
        _, ax = plt.subplots()

        dist_options = self.dist_options | dist_kw if dist_kw else self.dist_options
        best_options = self.best_options | best_kw if dist_kw else self.best_options

        for i, dx in enumerate(dist_x):
            ax.plot(dx, dist_y[i], **dist_options)  # noqa

        if best_x is not None and best_y is not None:
            ax.plot(best_x, best_y, **best_options)

        if log_scale:
            ax.set_xscale('log')
            ax.set_yscale('log')

        ax.legend(loc='best')
        ax.grid(alpha=0.3)

        return ax
