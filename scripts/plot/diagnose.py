import numpy as np
import matplotlib

from jetfit.core.utils import save_plot_unique, apply_plot_run_label
from scripts.plot.base import latex

matplotlib.use('Agg', force=True)

try:
    import corner
    import arviz as az
    from matplotlib import pyplot as plt
except ImportError:
    raise ImportError(
        "This example requires 'arviz', 'corner',"
        "and 'matplotlib' to be installed."
    )
from pathlib import Path


# Default plotting options for the corner plot. Modify as desired.
OPTIONS = {
    'label_size': 16, 'show_titles': True, 'color': 'mediumblue',
    'plot_datapoints': False, 'quantiles': [0.16, 0.5, 0.84],
    'label_kwargs': {'fontsize': 14}, 'title_kwargs': {"fontsize": 14},
    'fill_contours': True, 'smooth': 0.75, 'smooth1d': 0.75,
}


def plot_trace(params, out_dir, sampler=None, chain=None) -> None:
    """
    Generate the trace plots using arviz.

    Parameters
    ----------
    sampler : , optional
        The MCMC sampler. Must be set if ``chain=None``.

    chain : , optional
        The MCMC chain. Must be set if ``sampler=None``.

    params : Parameters
        The model Parameters object.

    out_dir : Path or str
        The directory to save the results.
    """
    if chain is sampler is None:
        raise ValueError('`chain`  or `sampler` must be specified')

    # Use arviz style
    az.style.use("arviz-darkgrid")

    # Create the production inference data object
    var_names = [p.name for p in params.fitting]

    if sampler is not None:
        inf_data = az.from_emcee(sampler, var_names=var_names)
    else:
        chain = np.transpose(chain, (1, 0, 2))
        burn = {name: chain[..., i] for i, name in enumerate(var_names)}
        inf_data = az.from_dict(posterior=burn)

    # Save summary statistics to a csv
    az.summary(inf_data).to_csv(out_dir / "summary.csv")

    # Plot the trace plot
    az.plot_trace(inf_data)
    save_plot_unique('trace', 'png', out_dir)
    save_plot_unique('trace', 'pdf', out_dir)
    plt.close()


def plot_corner(chain, params, out_dir=None):
    """
    Creates the corner plot of 1D and 2D posteriors.

    Parameters
    ----------
    chain :
        The flattened MCMC chain.

    params : Parameters
        The MCMC parameters.

    out_dir : Path, optional
        The directory to save the results.
    """
    bins = 50
    ranges, labels, pos = [], [], []
    h_ranges, h_labels, h_pos = [], [], []
    np_ranges, np_labels, np_pos = [], [], []
    param_pos = {}

    for i, p in enumerate(params):
        name = p.name if p.group is None else f'{p.name} ({p.group})'
        param_pos[name] = i

    # Split the parameters into groups (GRB physics, statistical, host)
    for p in params:
        name = p.name if p.group is None else f'{p.name} ({p.group})'
        lower = p.prior.lower
        upper = p.prior.upper
        valid_range = np.isfinite(lower) and np.isfinite(upper) and (lower < upper)

        if '_offset' in name or 'slop' in name:
            if valid_range:
                np_ranges.append((lower, upper))
                np_labels.append(latex(name))
                np_pos.append(param_pos[name])

        elif '_host' in name:
            if valid_range:
                h_ranges.append((lower, upper))
                h_labels.append(latex(name))
                h_pos.append(param_pos[name])

        else:
            if valid_range:
                ranges.append((lower, upper))
                labels.append(latex(name))
                pos.append(param_pos[name])

    fig = None
    np_fig = None
    h_fig = None

    def make_corner(data, labels, ranges=None):
        try:
            kwargs = {'bins': bins, 'labels': labels, **OPTIONS}
            if ranges is not None:
                kwargs['range'] = ranges
            return corner.corner(data, **kwargs)
        except ValueError:
            # Some runs have nuisance chains outside prior ranges; retry without
            # explicit ranges before giving up on that panel.
            if ranges is not None:
                try:
                    return corner.corner(data, bins=bins, labels=labels, **OPTIONS)
                except ValueError:
                    return None
            return None

    try:
        # Physical parameters
        if ranges:
            fig = make_corner(chain[:, pos], labels, ranges)
            if fig is not None:
                apply_plot_run_label(fig, x=0.99, ha='right')
                if out_dir:
                    fig.savefig(out_dir / 'corner.pdf', dpi=300)

        # Non-physical parameters
        if np_ranges:
            np_fig = make_corner(chain[:, np_pos], np_labels, np_ranges)
            if np_fig is not None:
                apply_plot_run_label(np_fig, x=0.99, ha='right')
                if out_dir:
                    np_fig.savefig(out_dir / 'corner_np.pdf', dpi=300)

        # Host galaxy parameters
        if h_ranges:
            h_fig = make_corner(chain[:, h_pos], h_labels, h_ranges)
            if h_fig is not None:
                apply_plot_run_label(h_fig, x=0.99, ha='right')
                if out_dir:
                    h_fig.savefig(out_dir / 'corner_host.pdf', dpi=300)
    finally:
        for f in (fig, np_fig, h_fig):
            if f is not None:
                plt.close(f)
