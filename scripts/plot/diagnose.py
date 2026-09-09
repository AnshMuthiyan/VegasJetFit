import numpy as np
import matplotlib

from jetfit.core.utils import save_plot_unique, apply_plot_run_label, apply_plot_title
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

REDUCED_CORNER_GROUPS = {
    "corner_csm": {
        "title": "CSM / Spectral / Geometry Posterior",
        "parameters": (
            "n017", "k", "k1", "k2", "sn",
            "nt", "nism", "rt",
            "p", "ebv_source_frame", "rv_milky_way",
            "theta_c", "theta_v",
        ),
    },
}

ENERGY_CORNER_PARAMETERS = (
    "E_j_core_52",
    "E_iso_52",
    "theta_c",
    "Omega_2j_pct_4pi",
)

CORE_CORNER_PARAMETERS = (
    ("derived_log10", "E_j_core_52", "log10_E_j_core_52"),
    ("derived_log10", "Gamma_0_core_avg", "log10_Gamma_0_core_avg"),
    ("derived_log10", "M_j_core_msun", "log10_M_j_core_msun"),
    ("raw", "n017", None),
    ("raw", "eps_e", None),
    ("raw_first", ("eps_b", "eps_B"), None),
)


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
    fig = plt.gcf()
    apply_plot_title(fig, "MCMC Trace", y=0.995, top=0.965, fontsize=11)
    apply_plot_run_label(fig)
    save_plot_unique('trace', 'png', out_dir)
    save_plot_unique('trace', 'pdf', out_dir)
    plt.close()


def _parameter_plot_name(param):
    return param.name if param.group is None else f'{param.name} ({param.group})'


def _parameter_plot_label(param):
    """Label raw chain coordinates; log-scaled parameters are in log10 space."""
    if (
        getattr(param, "name", None) in {"E_j_52", "E_j_core_52"}
        and str(param.scale.value) == "log"
    ):
        if param.name == "E_j_core_52":
            return r"$\log_{10}E_{j,c,52}$"
        return r"$\log_{10}E_{j,52}$"
    if (
        getattr(param, "name", None) == "Gamma_0_core_avg"
        and str(param.scale.value) == "log"
    ):
        return r"$\log_{10}\bar{\Gamma}_{0,c}$"
    if (
        getattr(param, "name", None) in {"theta_c", "theta_v"}
        and str(param.scale.value) == "log"
    ):
        symbol = r"\theta_c" if param.name == "theta_c" else r"\theta_v"
        return rf"$\log_{{10}}({symbol}/\mathrm{{rad}})$"
    return latex(_parameter_plot_name(param))


def _corner_range(param):
    lower = param.prior.lower
    upper = param.prior.upper
    if np.isfinite(lower) and np.isfinite(upper) and (lower < upper):
        return lower, upper
    return None


def _make_corner(data, labels, ranges=None, bins=50, allow_range_fallback=True):
    try:
        kwargs = {'bins': bins, 'labels': labels, **OPTIONS}
        if ranges is not None:
            kwargs['range'] = ranges
        return corner.corner(data, **kwargs)
    except ValueError:
        plt.close(plt.gcf())
        # The posterior-focused diagnostic can still be useful when a derived
        # coordinate has an imperfect requested range.  Prior-bound plots must
        # never silently fall back, because that would hide boundary contact.
        if ranges is not None and allow_range_fallback:
            try:
                return corner.corner(data, bins=bins, labels=labels, **OPTIONS)
            except ValueError:
                plt.close(plt.gcf())
                return None
        return None


def _derived_log10_column(derived, source_name, plot_name):
    """Return a log10 derived column, compact label, and robust plot range."""
    values = np.asarray(derived.get(source_name, []), dtype=float)
    values = np.where(values > 0.0, np.log10(values), np.nan)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return None
    lo, hi = np.nanpercentile(finite, [0.1, 99.9])
    if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
        center = float(np.nanmedian(finite))
        pad = max(1.0e-3, 0.05 * abs(center), 0.05)
        lo, hi = center - pad, center + pad
    else:
        pad = 0.05 * (hi - lo)
        lo, hi = lo - pad, hi + pad
    return values, latex(plot_name), (lo, hi)


def _posterior_zoom_range(values):
    """Return a compact, finite plotting range for a posterior coordinate."""
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return None
    lo, hi = np.nanpercentile(finite, [0.1, 99.9])
    if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
        center = float(np.nanmedian(finite))
        pad = max(1.0e-3, 0.05 * abs(center), 0.05)
        return center - pad, center + pad
    pad = 0.05 * (hi - lo)
    return lo - pad, hi + pad


def _save_corner(
    data,
    labels,
    ranges,
    title,
    path,
    bins=50,
    allow_range_fallback=True,
):
    """Build and save one corner after jointly filtering invalid rows."""
    data = np.asarray(data, dtype=float)
    data = data[np.all(np.isfinite(data), axis=1)]
    if data.shape[0] < 2 or data.shape[1] < 2:
        return None
    fig = _make_corner(
        data,
        labels,
        ranges,
        bins=bins,
        allow_range_fallback=allow_range_fallback,
    )
    if fig is None:
        return None
    apply_plot_title(fig, title, y=0.995, top=0.965, fontsize=11)
    apply_plot_run_label(fig, x=0.99, ha='right')
    if path is not None:
        path = Path(path)
        fig.savefig(path, dpi=300)
        fig.savefig(path.with_suffix('.png'), dpi=220)
    return fig


def plot_reduced_corners(chain, params, derived=None, out_dir=None):
    """
    Create reduced corner plots for the most useful physical correlations.

    Outputs
    -------
    corner_core.pdf
        Core E_j, core-averaged Gamma0, core ejecta mass, n17,
        epsilon_e, and epsilon_B, in that order.

    corner_csm.pdf
        Density-profile, spectral, extinction, and geometry parameters when fitted.
    """
    param_lookup = {}
    for i, p in enumerate(params):
        # Prefer the first occurrence. Requested groups intentionally avoid
        # grouped calibration/nuisance parameters.
        param_lookup.setdefault(p.name, (i, p))

    derived = {} if derived is None else derived
    figures = []
    try:
        core_arrays, core_labels, core_ranges = [], [], []
        for kind, source, plot_name in CORE_CORNER_PARAMETERS:
            if kind == "derived_log10":
                column = _derived_log10_column(derived, source, plot_name)
                if column is None:
                    continue
                values, label, value_range = column
            else:
                names = source if kind == "raw_first" else (source,)
                match = next((param_lookup[name] for name in names if name in param_lookup), None)
                if match is None:
                    continue
                idx, param = match
                value_range = _corner_range(param)
                if value_range is None:
                    continue
                values = np.asarray(chain[:, idx], dtype=float)
                label = _parameter_plot_label(param)
            core_arrays.append(values)
            core_labels.append(label)
            core_ranges.append(value_range)

        if len(core_arrays) >= 2:
            n = min(values.size for values in core_arrays)
            core_data = np.column_stack([values[:n] for values in core_arrays])
            fig = _save_corner(
                core_data,
                core_labels,
                core_ranges,
                "Core Physical / Microphysical Posterior",
                None if out_dir is None else Path(out_dir) / "corner_core.pdf",
            )
            if fig is not None:
                figures.append(fig)

        for stem, config in REDUCED_CORNER_GROUPS.items():
            pos, labels, ranges = [], [], []
            for name in config["parameters"]:
                if name not in param_lookup:
                    continue
                idx, param = param_lookup[name]
                param_range = _corner_range(param)
                if param_range is None:
                    continue
                pos.append(idx)
                labels.append(_parameter_plot_label(param))
                ranges.append(param_range)

            # A 1-parameter "corner" is usually less useful than the existing
            # summary/trace products, so only write true correlation plots.
            if len(pos) < 2:
                continue

            fig = _save_corner(
                chain[:, pos],
                labels,
                ranges,
                config["title"],
                None if out_dir is None else Path(out_dir) / f"{stem}.pdf",
            )
            if fig is None:
                continue
            figures.append(fig)
    finally:
        for fig in figures:
            plt.close(fig)


def plot_energy_corner(derived, out_dir=None):
    """
    Create the beaming-corrected energy corner plot from derived samples.

    Parameters
    ----------
    derived : dict[str, np.ndarray]
        Derived posterior samples keyed by parameter name.

    out_dir : Path, optional
        Directory for `corner_energy.pdf`.
    """
    labels, arrays, ranges = [], [], []
    for name in ENERGY_CORNER_PARAMETERS:
        values = np.asarray(derived.get(name, []), dtype=float)
        if values.size == 0:
            continue
        plot_name = name
        if name == "E_j_core_52":
            values = np.where(values > 0.0, np.log10(values), np.nan)
            plot_name = "log10_E_j_core_52"
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            continue
        lo, hi = np.nanpercentile(finite, [0.1, 99.9])
        if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
            center = float(np.nanmedian(finite))
            pad = max(1.0e-6, 0.05 * abs(center), 0.05)
            lo, hi = center - pad, center + pad
        else:
            pad = 0.05 * (hi - lo)
            lo, hi = lo - pad, hi + pad
        arrays.append(values)
        labels.append(latex(plot_name))
        ranges.append((lo, hi))

    if len(arrays) < 2:
        return None

    n = min(values.size for values in arrays)
    data = np.column_stack([values[:n] for values in arrays])
    data = data[np.all(np.isfinite(data), axis=1)]
    if data.shape[0] < 2:
        return None
    fig = _make_corner(data, labels, ranges=ranges)
    if fig is None:
        return None
    apply_plot_title(fig, "Core Jet Energy / Geometry Posterior", y=0.995, top=0.965, fontsize=11)
    apply_plot_run_label(fig, x=0.99, ha='right')
    if out_dir:
        path = Path(out_dir) / 'corner_energy.pdf'
        fig.savefig(path, dpi=300)
        fig.savefig(path.with_suffix('.png'), dpi=220)
    plt.close(fig)
    return fig


def plot_jet_mass_corner(derived, out_dir=None):
    """Plot matched core energy, core-averaged Lorentz factor, and core mass."""
    transforms = (
        ("E_j_core_52", "log10_E_j_core_52"),
        ("Gamma_0_core_avg", "log10_Gamma_0_core_avg"),
        ("M_j_core_msun", "log10_M_j_core_msun"),
    )
    labels, arrays, ranges = [], [], []
    for source_name, plot_name in transforms:
        values = np.asarray(derived.get(source_name, []), dtype=float)
        values = np.where(values > 0.0, np.log10(values), np.nan)
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            continue
        lo, hi = np.nanpercentile(finite, [0.1, 99.9])
        if not np.isfinite(lo) or not np.isfinite(hi) or lo == hi:
            center = float(np.nanmedian(finite))
            pad = max(1.0e-3, 0.05 * abs(center), 0.05)
            lo, hi = center - pad, center + pad
        else:
            pad = 0.05 * (hi - lo)
            lo, hi = lo - pad, hi + pad
        arrays.append(values)
        labels.append(latex(plot_name))
        ranges.append((lo, hi))

    if len(arrays) < 2:
        return None
    n = min(values.size for values in arrays)
    data = np.column_stack([values[:n] for values in arrays])
    data = data[np.all(np.isfinite(data), axis=1)]
    if data.shape[0] < 2:
        return None
    fig = _make_corner(data, labels, ranges=ranges)
    if fig is None:
        return None
    apply_plot_title(fig, "Core Jet Energy / Mean Lorentz Factor / Mass Posterior", y=0.995, top=0.965, fontsize=11)
    apply_plot_run_label(fig, x=0.99, ha='right')
    if out_dir:
        path = Path(out_dir) / 'corner_jet_mass.pdf'
        fig.savefig(path, dpi=300)
        fig.savefig(path.with_suffix('.png'), dpi=220)
    plt.close(fig)
    return fig


def plot_corner(chain, params, derived=None, out_dir=None):
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
    derived = {} if derived is None else derived
    ranges, labels, physical_arrays = [], [], []
    prior_ranges, prior_labels, prior_arrays = [], [], []
    h_ranges, h_labels, h_pos = [], [], []
    np_ranges, np_labels, np_pos = [], [], []
    d_ranges, d_labels, d_pos = [], [], []
    param_pos = {}

    c2_index = None
    for i, p in enumerate(params):
        name = _parameter_plot_name(p)
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

    # Split the parameters into groups (GRB physics, statistical, host).
    # Replace the fitted jet normalization and on-axis Gamma0 with matched
    # core quantities from the same posterior rows.
    core_energy_added = False
    core_gamma_added = False
    core_mass_added = False
    for p in params:
        name = _parameter_plot_name(p)
        param_range = _corner_range(p)
        valid_range = param_range is not None

        if p.name == 'c2' or p.name in custom_params:
            d_ranges.append((p.prior.lower, p.prior.upper))
            d_labels.append(latex(name))
            d_pos.append(param_pos[name])

        elif '_offset' in name or 'slop' in name:
            if valid_range:
                np_ranges.append(param_range)
                np_labels.append(_parameter_plot_label(p))
                np_pos.append(param_pos[name])

        elif '_host' in name:
            if valid_range:
                h_ranges.append(param_range)
                h_labels.append(_parameter_plot_label(p))
                h_pos.append(param_pos[name])

        else:
            # This companion plot remains in native fitted coordinates.  Its
            # axes are exactly the explicit prior bounds, making posterior
            # contact with a hard fit limit immediately visible.
            if valid_range:
                prior_ranges.append(param_range)
                prior_labels.append(_parameter_plot_label(p))
                prior_arrays.append(np.asarray(chain[:, param_pos[name]], dtype=float))

            if p.name in {"E_j_52", "E_j_core_52", "E52"} and "E_j_core_52" in derived:
                if not core_energy_added:
                    column = _derived_log10_column(
                        derived, "E_j_core_52", "log10_E_j_core_52"
                    )
                    if column is not None:
                        values, label, value_range = column
                        physical_arrays.append(values)
                        labels.append(label)
                        ranges.append(value_range)
                        core_energy_added = True
            elif p.name in {"lf0", "Gamma_0_core_avg"} and "Gamma_0_core_avg" in derived:
                if not core_gamma_added:
                    column = _derived_log10_column(
                        derived, "Gamma_0_core_avg", "log10_Gamma_0_core_avg"
                    )
                    if column is not None:
                        values, label, value_range = column
                        physical_arrays.append(values)
                        labels.append(label)
                        ranges.append(value_range)
                        core_gamma_added = True
                if not core_mass_added and "M_j_core_msun" in derived:
                    column = _derived_log10_column(
                        derived, "M_j_core_msun", "log10_M_j_core_msun"
                    )
                    if column is not None:
                        values, label, value_range = column
                        physical_arrays.append(values)
                        labels.append(label)
                        ranges.append(value_range)
                        core_mass_added = True
            elif valid_range:
                ranges.append(param_range)
                labels.append(_parameter_plot_label(p))
                physical_arrays.append(np.asarray(chain[:, param_pos[name]], dtype=float))

    fig = None
    np_fig = None
    h_fig = None

    try:
        plot_reduced_corners(chain, params, derived=derived, out_dir=out_dir)

        # Full physical parameters on their native fit-prior bounds.  Do not
        # fall back to auto-ranging here: that would defeat this diagnostic.
        if prior_ranges and prior_arrays:
            n = min(values.size for values in prior_arrays)
            prior_data = np.column_stack([values[:n] for values in prior_arrays])
            prior_fig = _save_corner(
                prior_data,
                prior_labels,
                prior_ranges,
                "Physical-Parameter Posterior (Fit Prior Bounds)",
                (out_dir / "corner_prior.pdf") if out_dir else None,
                bins=bins,
                allow_range_fallback=False,
            )
            if prior_fig is not None:
                plt.close(prior_fig)

        # The familiar derived-core diagnostic stays deliberately tight so
        # posterior structure remains readable alongside the boundary plot.
        if ranges and physical_arrays:
            n = min(values.size for values in physical_arrays)
            physical_data = np.column_stack([values[:n] for values in physical_arrays])
            physical_data = physical_data[np.all(np.isfinite(physical_data), axis=1)]
            zoom_ranges = [_posterior_zoom_range(physical_data[:, i]) for i in range(physical_data.shape[1])]
            fig = _make_corner(physical_data, labels, zoom_ranges, bins=bins)
            if fig is not None:
                apply_plot_title(fig, "Physical-Parameter Posterior (Zoomed)", y=0.995, top=0.965, fontsize=11)
                apply_plot_run_label(fig, x=0.99, ha='right')
                if out_dir:
                    path = out_dir / 'corner.pdf'
                    fig.savefig(path, dpi=300)
                    fig.savefig(path.with_suffix('.png'), dpi=220)

        # Dust Scatter & Hyper parameters
    if d_ranges:
        d_fig = corner.corner(chain[:, d_pos], bins=bins, labels=d_labels, range=d_ranges, **OPTIONS)
        if out_dir: d_fig.savefig(out_dir / 'corner_dust.pdf', dpi=300)

    # Non-physical parameters
        if np_ranges:
            np_fig = _make_corner(chain[:, np_pos], np_labels, np_ranges, bins=bins)
            if np_fig is not None:
                apply_plot_title(np_fig, "Nuisance-Parameter Posterior", y=0.995, top=0.965, fontsize=11)
                apply_plot_run_label(np_fig, x=0.99, ha='right')
                if out_dir:
                    path = out_dir / 'corner_np.pdf'
                    np_fig.savefig(path, dpi=300)
                    np_fig.savefig(path.with_suffix('.png'), dpi=220)

        # Host galaxy parameters
        if h_ranges:
            h_fig = _make_corner(chain[:, h_pos], h_labels, h_ranges, bins=bins)
            if h_fig is not None:
                apply_plot_title(h_fig, "Host-Parameter Posterior", y=0.995, top=0.965, fontsize=11)
                apply_plot_run_label(h_fig, x=0.99, ha='right')
                if out_dir:
                    path = out_dir / 'corner_host.pdf'
                    h_fig.savefig(path, dpi=300)
                    h_fig.savefig(path.with_suffix('.png'), dpi=220)
    finally:
        for f in (fig, np_fig, h_fig):
            if f is not None:
                plt.close(f)
