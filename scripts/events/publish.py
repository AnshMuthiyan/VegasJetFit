## Change parameters and json files

import json
import sys
from pathlib import Path

# Add VegasJetFit to path to use local modules instead of installed ones
VEGASJETFIT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(VEGASJETFIT_ROOT))

import argparse
import numpy as np
import corner
from corner import quantile
from dust_extinction.parameter_averages import CCM89
from matplotlib import pyplot as plt

from jetfit.ampy import Ampy
from jetfit.core import utils
from jetfit.core.utils import save_plot_unique
from scripts.plot import histogram, visualize, diagnose
from scripts.plot.base import latex, OPTION_MAP
from scripts.plot.diagnose import OPTIONS
from scripts.plot.histogram import SpectralIndexPlot
from scripts.sandbox.light_curve import sample_light_curve

global OUTPUT_DIR

import seaborn as sns
import scienceplots
plt.style.use(['science'])


def plot_spectral_indices(chain, log_prob, ampy, minimized):
    """ Plots the spectral indices. """
    indices = ampy.obs.data[ampy.obs.sindex_loc]

    fig, axs = plt.subplots(len(indices), 1, figsize=(8, 5), sharex=True)

    # Temporary: Reuse old plotting routine
    plotter = SpectralIndexPlot(
        chain, log_prob, ampy.mcmc.params,
        ampy.obs, ampy.mcmc.models.afg_model
    )

    samples, best, xrt, labels, times = [], [], [], [], []

    for index in indices:
        times.append(index.time.to_value('d'))
        labels.append(f"{index.time.to_value('d'):.3f} days")

        # Get the MCMC distribution for each index
        samples.append(
            plotter.evaluate(
                index.time.to_value('d'),
                index.int_range.lower.to_value('Hz'),
                index.int_range.upper.to_value('Hz'),
            )
        )

        # Get the minimized values
        best.append(
            plotter.evaluate_best(
                index.time.to_value('d'),
                index.int_range.lower.to_value('Hz'),
                index.int_range.upper.to_value('Hz'),
                minimized.get('model')
            )
        )

        # Get the XRT values
        xrt.append(
            (
                index.value,
                index.uncertainty.lower.value,
                index.uncertainty.upper.value
            )
        )

    if not isinstance(axs, tuple):
        axs = (axs,)

    # Plot the XRT and minimized vales
    for i, (val, xrt_lo, xrt_hi) in enumerate(xrt):
        data = {"Spectral Index": samples[i], "label": [labels[i]] * len(samples[i])}

        sns.swarmplot(x='Spectral Index', y='label', data=data, ax=axs[i], size=5, color='k', alpha=0.3)

        axs[i].plot(best[i], 0, color='tab:red', marker='o' ,ms=5, label=r'Minimized' if i == 0 else None, zorder=999)
        axs[i].errorbar(val, 0, xerr=[[xrt_lo], [xrt_hi]],  elinewidth=1.5, fmt='o', barsabove=True, color='tab:blue', capsize=6, ms=9, label=r'XRT  $\pm$ 1$\sigma$' if i == 0 else None, zorder=998)
        axs[i].set_ylabel("", fontsize=14)
        axs[i].grid(alpha=0.5, axis='y', which='major')
        axs[i].tick_params(axis='y', which='both', left=False, right=False)
        axs[i].legend()

        plt.setp(axs[i].get_yticklabels(), rotation=90, va='center')

    # axs[0].set_xlabel("Spectral Index", fontsize=14)
    # plt.grid(alpha=0.5, axis='y')
    fig.subplots_adjust(hspace=0)
    save_plot_unique('index_dist_new', 'pdf', str(OUTPUT_DIR))
    # plt.show()
    plt.close()

    # histogram.plot_spectral_indices(
    #     chain, log_prob, ampy.obs, ampy.mcmc.params,
    #     ampy.mcmc.models.afg_model, best=minimized.get('model'),
    #     out_dir=OUTPUT_DIR
    # )
    # plt.close()


def plot_light_curve(ampy, minimized, pretty=True, chain=None):
    """ Plots the light curve. """
    lcg = visualize.plot_light_curve(
        ampy.mcmc.models.afg_model, minimized, ampy.obs, ext_model=CCM89(Rv=3.1), dual=pretty
    )
    ranges = ampy.obs.epoch(ampy.obs.flux_loc)
    times = np.geomspace(ranges[0] / 2, ranges[1] * 2, num=200)
    lcg.ax.set_xlim(times.min(), times.max())
    # lcg.ax.set_xlim(8e-4, times.max())
    # lcg.ax.set_ylim(1e-6)

    if pretty and chain is not None:
        # Load in the file with the spacing values
        with open(r"C:\Projects\repos\JetFit\scripts\events\spacing.json", "r") as f:
            scales = json.load(f)[event]

        # Get the times to plot
        ranges = ampy.obs.epoch(ampy.obs.flux_loc)
        times = np.geomspace(ranges[0] / 2, ranges[1] * 2, num=200)
        # times = np.geomspace(8e-3, ranges[1] * 2, num=200)

        # Generate LCs from randomly samples sets
        # samples = chain[np.random.randint(len(chain), size=100)]
        # modeled = sample_light_curve(samples, ampy, lcg, times)

        # Plot the best fitting LC
        best_modeled = lcg.model_fluxes(minimized, times, ext_model=CCM89(Rv=3.1))

        for band, fluxes in best_modeled.items():
            lcg.ax1.loglog(times, fluxes * scales[band], color=OPTION_MAP[band]['color'])

        # # Plot the distribution of LCs
        # for band, fluxes in modeled.items():

        #     # Get the 1-sigmas
        #     p16, _, p84 = np.percentile(fluxes, [16, 50, 84], axis=0)

        #     lcg.ax1.fill_between(
        #         times, p16 * scales[band], p84 * scales[band],
        #         color=OPTION_MAP[band]['color'], alpha=0.2
        #     )

        lcg.plot_observation(minimized, spreads=scales, offset=True, excluded=True, axes='lower')
        lcg.ax.set_xlim(times.min(), times.max())
        lcg.ax1.set_xlim(times.min(), times.max())

        bbox = dict(facecolor="white", alpha=0.5, edgecolor='white')

        lcg.ax.text(0.98, 0.95, "Raw", transform=lcg.ax.transAxes,
                 ha="right", va="top", fontsize=12, bbox=bbox)

        # lcg.ax.legend(
        #     loc="center left",
        #     bbox_to_anchor=(1.01, 0.5),  # x = just outside the axis; y = center
        #     borderaxespad=0,
        #     ncol=1,
        # )

        lcg.ax1.text(0.98, 0.95, "Calibration Applied", transform=lcg.ax1.transAxes,
                 ha="right", va="top", fontsize=12, bbox=bbox)

        # lcg.ax1.legend(
        #     loc="center left",
        #     bbox_to_anchor=(1.01, 0.5),  # x = just outside the axis; y = center
        #     borderaxespad=0,
        #     ncol=1,
        # )

        save_plot_unique('light_curve_dual', 'pdf', str(OUTPUT_DIR))
    else:
        save_plot_unique('light_curve', 'pdf', str(OUTPUT_DIR))


def get_param_boundaries(samples, prior):
    """"""
    smin = np.min(samples)
    smax = np.max(samples)
    prior_min, prior_max = prior.lower, prior.upper

    # Check if we're NOT at the prior boundary
    near_lower = np.isclose(smin, prior_min, rtol=0, atol=1e-6)
    near_upper = np.isclose(smax, prior_max, rtol=0, atol=1e-6)

    if not near_lower:
        smin -= 0.1 * (smax - smin)
    if not near_upper:
        smax += 0.1 * (smax - smin)

    # Clip to prior range just in case
    return max(smin, prior_min), min(smax, prior_max)


def plot_corners_custom(chain, ampy, filename, include=None):
    """"""

    # mask = chain[:, 4] > (2.96875 * chain[:, 0] - 3.5625) # 050525A
    mask = chain[:, 6] > (-2.3214 * chain[:, 5] + 6.7857) # 090424

    chain1 = chain[mask]
    chain2 = chain[~mask]

    fig = None
    options = OPTIONS | {'quantiles': None}
    colors = ('salmon', 'mediumblue')

    for i, chain_sub in enumerate((chain2, chain1)):
        ranges, labels, pos = [], [], []
        param_pos = {}
        options['color'] = colors[i]

        for i, p in enumerate(ampy.mcmc.params.fitting):
            param_pos[p.name] = i

            smin, smax = get_param_boundaries(chain[:, i], p.prior)

            if p.name in include:
                labels.append(latex(p.name))
                pos.append(param_pos[p.name])
                ranges.append((smin, smax))

            elif 'slop' in p.name and 'slop' in include:
                labels.append(latex(p.name))
                pos.append(param_pos[p.name])
                ranges.append((smin, smax))

        # if 'p' in include:
        #     ranges[0] = (2.0, 2.25)
        #     ranges[1] = (0.4, 1.8)

        fig = corner.corner(chain_sub[:, pos], bins=50, range=ranges, labels=labels, **options, fig=fig, hist2d_kwargs={'density': True})

    axes = np.array(fig.axes).reshape((len(pos), len(pos)))

    # Compute the quantiles for each chain
    q1 = [quantile(chain1[:, i], [0.16, 0.5, 0.84]) for i in pos]
    q2 = [quantile(chain2[:, i], [0.16, 0.5, 0.84]) for i in pos]

    for i in range(len(pos)):
        ax = axes[i, i]

        m1, lo1, hi1 = q1[i][1], q1[i][1] - q1[i][0], q1[i][2] - q1[i][1]
        m2, lo2, hi2 = q2[i][1], q2[i][1] - q2[i][0], q2[i][2] - q2[i][1]

        # Stack both titles using LaTeX with color
        title_str1 = labels[i] + r"$ = {0:.2f}_{{-{1:.2f}}}^{{+{2:.2f}}}$".format(m1, lo1, hi1)
        title_str2 = labels[i] + r"$ = {0:.2f}_{{-{1:.2f}}}^{{+{2:.2f}}}$".format(m2, lo2, hi2)

        ax.set_title(title_str1 + '\n\n' + title_str2, fontsize=14)


    fig.savefig(OUTPUT_DIR / filename, dpi=300)

    return fig


def plot_corners(chain, ampy, fig=None, fig1=None, save=True, kwargs=None):
    """ Plots the corners. """

    options = OPTIONS | (kwargs or {})

    ranges, labels, pos = [], [], []
    ranges1, labels1, pos1 = [], [], []
    param_pos = {}

    for i, p in enumerate(ampy.mcmc.params.fitting):
        param_pos[p.name] = i

        smin, smax = get_param_boundaries(chain[:, i], p.prior)

        if p.name in ('E52', 'lf0', 'n0t', 'rt', 'n017', 'eps_e', 'eps_b'):
            labels.append(latex(p.name))
            pos.append(param_pos[p.name])
            ranges.append((smin, smax))

        elif p.name in ('p', 'k', 'k1', 'k2', 'sn', 'sni', 'rv_milky_way', 'ebv_source_frame', 'tj', 'sj', 'sji'):
            labels1.append(latex(p.name))
            pos1.append(param_pos[p.name])
            ranges1.append((smin, smax))

        elif 'slop' in p.name:
            labels1.append(latex(p.name))
            pos1.append(param_pos[p.name])
            ranges1.append((smin, smax))

        # if 'host' in p.name:
        #     labels.append(latex(p.name))
        #     pos.append(param_pos[p.name])
        #     ranges.append((smin, smax))

    fig = corner.corner(chain[:, pos], bins=50, range=ranges, labels=labels, **options, fig=fig)

    if save:
        fig.savefig(OUTPUT_DIR / 'corner_bw.pdf', dpi=300)

    fig1 = corner.corner(chain[:, pos1], bins=50, range=ranges1, labels=labels1, **options, fig1=fig1)

    if save:
        fig1.savefig(OUTPUT_DIR / 'corner_em.pdf', dpi=300)

    return fig, fig1


def plot_frequencies( ampy, minimized):
    """ Plots the frequencies. """
    visualize.plot_frequencies(
        chain = None, log_prob = None, obs=ampy.obs, params =  ampy.mcmc.params,
        model = ampy.mcmc.models.afg_model, best=minimized,
        out_dir=OUTPUT_DIR,
    )


# def plot_density_profile(ampy, minimized):
#     """ Plots the density profile. """
#     visualize.plot_density_profile(
#         ampy.mcmc.params, ampy.obs,
#         ampy.mcmc.models.afg_model, best=minimized.get('model'),
#         out_dir=OUTPUT_DIR
#     )


def plot_jet_properties(chain, log_prob, ampy):
    """ Plots the jet properties. """
    histogram.plot_jet_correction(
        chain, log_prob, ampy.mcmc.params,
        ref=ampy.mcmc.models.afg_model.ref_radius,
        out_dir=OUTPUT_DIR
    )


def plot_trace(chain, ampy):
    """"""
    diagnose.plot_trace(ampy.mcmc.params, chain=chain, out_dir=OUTPUT_DIR)


def main(obs, params, minimized):
    """ Does everything. """
    # Let ampy format everything
    ampy = Ampy(obs, params)

    def flatten(v):
        """ Flatten v. """
        s = list(v.shape[1:])
        s[0] = np.prod(v.shape[:2])
        return v.reshape(s)

    # Flatten the walkers
    # flat_chain = flatten(chain)
    # flat_prob = flatten(log_prob)

    # Plot everything!
    # plot_trace(chain, ampy)
    # plot_corners_custom(flat_chain, ampy, filename='corner_bw.pdf', include=('E52', 'lf0', 'n0t', 'rt', 'n017', 'eps_e', 'eps_b'))
    # plot_corners_custom(flat_chain, ampy, filename='corner_em.pdf', include=('p', 'k', 'k1', 'k2', 'sn', 'sni', 'ebv_source_frame', 'tj', 'sj', 'sji', 'slop'))
    # plot_corners(flat_chain, ampy)
    plt.close()
    plot_light_curve(ampy, minimized, pretty=False, chain=1)
    plt.close()
    plot_frequencies(ampy, minimized)
    print("Ploting spectral indices...")
    plt.close()
    # plot_density_profile( ampy, minimized)
    plt.close()
    # plot_jet_properties(flat_chain, flat_prob, ampy)


if __name__ == '__main__':
    # Run the Publisher via the command line
    parser = argparse.ArgumentParser(description="Create publication ready plots")
    parser.add_argument('--obs',     help='The input observation file.')
    parser.add_argument('--params',  help='The input parameter TOML file.')
    parser.add_argument('--sampler', help='The MCMC chain or sampler.')
    parser.add_argument('--best',    help='The best fit JSON file.')
    args = parser.parse_args()

    # Or run the Publisher manually
    event, sub_dir = "221009A", "grbs"
    p_obs = utils.get_input_csv_path(sub_dir, event)
    p_params = utils.get_event_path(sub_dir, event) / 'parameters.toml'
    # p_minimized = Path(rf"VegasJetFit\jetfit\results\Vegastesting\test1\221009A\best_fit.json")
    p_minimized = Path(rf"VegasJetFit\2210Test\best_fit.json")
    # p_sampler = rf"C:\Server\FINAL\analytic\{event}\chain.npz" COMENTED BY ANSH

    # p_params = utils.get_event_path(sub_dir, event) / 'jetsim.toml'
    # p_minimized = Path(rf"C:\Server\FINAL\numerical\ism\{event}\best_fit.json")
    # p_sampler = rf"C:\Server\FINAL\numerical\ism\{event}\chain.npz"

    # Load in the MCMC results COMMENTED BY ANSH
    # sampler = np.load(args.sampler or p_sampler)

    # Load in the minimized results
    with open(args.best or p_minimized, 'r') as f:
        min_params = json.load(f)

    # global OUTPUT_DIR
    OUTPUT_DIR = Path(rf"VegasJetFit\jetfit\results\Vegastesting\test1\{event}")
    # OUTPUT_DIR = Path(rf"C:\Server\FINAL\numerical\ism\{event}\paper")

    main(
        **{
            'obs':        args.obs or p_obs,
            'params':     args.params or p_params,
            'minimized':  min_params,
        }
    )
