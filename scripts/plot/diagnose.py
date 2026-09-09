import numpy as np

from jetfit.core.utils import save_plot_unique
from scripts.plot.base import latex

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
    d_ranges, d_labels, d_pos = [], [], []
    param_pos = {}

    c2_index = None
    for i, p in enumerate(params):
        name = p.name if p.group is None else f'{p.name} ({p.group})'
        param_pos[name] = i
        if p.name == 'c2':
            c2_index = i

    if c2_index is not None:
        from jetfit.mcmc.mcmc import trotter_dust_prior
        custom_params = trotter_dust_prior.get_custom_param_names()
        
        params_dict = {}
        for i, p in enumerate(params):
            params_dict[p.name] = chain[:, i]
            
        c1, rv, bh, x0, gamma = trotter_dust_prior.get_physical_dust_params(chain[:, c2_index], params_dict)
        
        phys_arr = np.column_stack((c1, rv, bh, x0, gamma))
        start_idx = chain.shape[1]
        chain = np.hstack((chain, phys_arr))
        
        phys_names = ['c1_phys', 'rv_phys', 'bh_phys', 'x0_phys', 'gamma_phys']
        for i, pname in enumerate(phys_names):
            param_pos[pname] = start_idx + i
            # Estimate range dynamically from chain values
            p_min, p_max = np.min(phys_arr[:, i]), np.max(phys_arr[:, i])
            # Add tiny padding to prevent corner plot errors if perfectly flat
            if p_min == p_max: p_min -= 0.1; p_max += 0.1
            ranges.append((p_min, p_max))
            labels.append(latex(pname))
            pos.append(start_idx + i)
    else:
        custom_params = set()

    # Split the parameters into groups (GRB physics, statistical, host)
    for p in params:
        name = p.name if p.group is None else f'{p.name} ({p.group})'

        if name == 'lf0':
            continue

        if p.name == 'c2' or p.name in custom_params:
            d_ranges.append((p.prior.lower, p.prior.upper))
            d_labels.append(latex(name))
            d_pos.append(param_pos[name])

        elif '_offset' in name or 'slop' in name:
            np_ranges.append((p.prior.lower, p.prior.upper))
            np_labels.append(latex(name))
            np_pos.append(param_pos[name])

        elif '_host' in name:
            h_ranges.append((p.prior.lower, p.prior.upper))
            h_labels.append(latex(name))
            h_pos.append(param_pos[name])

        else:
            ranges.append((p.prior.lower, p.prior.upper))
            labels.append(latex(name))
            pos.append(param_pos[name])

    # Physical parameters
    if ranges:
        fig = corner.corner(chain[:, pos], bins=bins, labels=labels, **OPTIONS,)
        if out_dir: fig.savefig(out_dir / 'corner.pdf', dpi=300)

    # Dust Scatter & Hyper parameters
    if d_ranges:
        d_fig = corner.corner(chain[:, d_pos], bins=bins, labels=d_labels, range=d_ranges, **OPTIONS)
        if out_dir: d_fig.savefig(out_dir / 'corner_dust.pdf', dpi=300)

    # Non-physical parameters
    if np_ranges:
        np_fig = corner.corner(
            chain[:, np_pos], bins=bins,
            labels=np_labels, range=np_ranges, **OPTIONS
        )
        if out_dir:
            np_fig.savefig(out_dir / 'corner_np.pdf', dpi=300)

    # Host galaxy parameters
    if h_ranges:
        h_fig = corner.corner(chain[:, h_pos], bins=bins, labels=h_labels, **OPTIONS)
        if out_dir: h_fig.savefig(out_dir / 'corner_host.pdf', dpi=300)

    plt.close()
