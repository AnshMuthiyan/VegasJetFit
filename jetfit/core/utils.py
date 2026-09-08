import math
import os
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd
import astropy.units as u
import matplotlib

matplotlib.use('Agg', force=True)
from matplotlib import pyplot as plt

from jetfit.core.structs import ScaleType


# TODO: validation for readers


def sec_to_days(x):
    """ Convert seconds to days. """
    return x / 86400


def days_to_sec(x):
    """ Convert days to seconds. """
    return x * 86400


def save_plot_unique(filename_base, ext, directory, dpi=None):
    """
    Save a matplotlib plot to disk, adding a suffix if the file exists.

    Parameters
    ----------
    filename_base: str
        The base name without extension.

    ext: str
        The file extension.

    directory: str
        The directory to save in.

    dpi : int, optional
        The dpi for the figure.
    """
    i = 0
    while True:
        filename = f"{filename_base}.{ext}" if i == 0 else f"{filename_base}_{i}.{ext}"
        filepath = os.path.join(directory, filename)
        if not os.path.exists(filepath):
            apply_plot_run_label(plt.gcf())
            plt.savefig(filepath, dpi=dpi)
            return
        i += 1


def get_plot_run_label():
    """
    Returns the optional run label to stamp onto plots.

    Label is sourced from environment variable:
      - JETFIT_PLOT_RUN_LABEL
    """
    label = os.environ.get('JETFIT_PLOT_RUN_LABEL', '').strip()
    return label or None


def get_plot_event_title(label=None):
    """
    Return the compact event title used for standard run products.

    Preferred source is ``JETFIT_PLOT_EVENT_TITLE``.  If that is absent, fall
    back to the leading segment of the run label, e.g. ``GRB 050525A`` from
    ``GRB 050525A | run_name``.
    """
    title = os.environ.get('JETFIT_PLOT_EVENT_TITLE', '').strip()
    if title:
        return title

    if label is None:
        label = get_plot_run_label()
    if not label:
        return None

    first = str(label).split('|', 1)[0].strip()
    return first or None


def apply_plot_title(fig=None, title=None, y=0.99, top=0.90, fontsize=12):
    """
    Add a standard GRB title while reserving top margin.

    ``title`` should describe the product; the GRB name is prepended from
    ``JETFIT_PLOT_EVENT_TITLE`` when available.  The small run/folder label is
    handled separately by ``apply_plot_run_label``.
    """
    if fig is None:
        fig = plt.gcf()
    if fig is None:
        return
    if getattr(fig, "_jetfit_plot_title_applied", False):
        return

    event_title = get_plot_event_title()
    if title and event_title:
        full_title = f"{event_title}: {title}"
    elif title:
        full_title = str(title)
    else:
        full_title = event_title
    if not full_title:
        return

    fig.suptitle(full_title, fontsize=fontsize, y=y)
    try:
        current_top = fig.subplotpars.top
        current_bottom = fig.subplotpars.bottom
        fig.subplots_adjust(top=min(current_top, top), bottom=max(current_bottom, 0.08))
    except Exception:
        pass
    fig._jetfit_plot_title_applied = True


def apply_plot_run_label(
    fig=None,
    label=None,
    x=0.5,
    y=0.006,
    ha='center',
    va='bottom',
    fontsize=5.5,
):
    """Optionally stamp internal run provenance onto a diagnostic plot.

    Published campaign figures keep provenance in their result directory,
    manifest, and machine-readable metadata instead of printing a run name or
    source filename on the artwork.  Set ``JETFIT_STAMP_PLOT_RUN_LABEL=1`` for
    an explicitly internal debugging export.
    """
    if fig is None:
        fig = plt.gcf()
    if fig is None:
        return

    if os.environ.get("JETFIT_STAMP_PLOT_RUN_LABEL", "").strip().lower() not in {
        "1", "true", "yes", "on",
    }:
        return

    if label is None:
        label = get_plot_run_label()
    if not label:
        return

    # Prevent duplicate overlays when save is retried with unique suffixes.
    if getattr(fig, "_jetfit_plot_label_applied", False):
        return

    fig.text(
        x,
        y,
        str(label),
        ha=ha,
        va=va,
        fontsize=fontsize,
        color='black',
        bbox={
            'facecolor': 'white',
            'alpha': 0.55,
            'edgecolor': 'none',
            'pad': 0.8,
        },
        zorder=1000,
    )
    fig._jetfit_plot_label_applied = True


def _artist_points_in_axes(ax):
    """Return finite plotted artist coordinates transformed into axes space."""
    points = []
    to_axes = ax.transAxes.inverted()

    def add_xy(x, y):
        arr = np.column_stack([np.asarray(x, dtype=float).ravel(), np.asarray(y, dtype=float).ravel()])
        if arr.size == 0:
            return
        mask = np.isfinite(arr).all(axis=1)
        if not mask.any():
            return
        arr = arr[mask]
        if arr.shape[0] > 1200:
            arr = arr[np.linspace(0, arr.shape[0] - 1, 1200).astype(int)]
        try:
            points.append(to_axes.transform(ax.transData.transform(arr)))
        except Exception:
            pass

    for line in ax.lines:
        try:
            add_xy(line.get_xdata(orig=False), line.get_ydata(orig=False))
        except Exception:
            pass

    for collection in ax.collections:
        try:
            offsets = collection.get_offsets()
        except Exception:
            continue
        if offsets is None or len(offsets) == 0:
            continue
        arr = np.asarray(offsets, dtype=float)
        if arr.ndim == 2 and arr.shape[1] >= 2:
            add_xy(arr[:, 0], arr[:, 1])

    if not points:
        return np.empty((0, 2), dtype=float)
    pts = np.vstack(points)
    return pts[np.isfinite(pts).all(axis=1)]


def _label_box_axes(x, y, text, *, ha="left", va="top", fontsize=15):
    """Approximate a text box in axes coordinates for overlap checks."""
    width = min(0.46, max(0.16, 0.014 * fontsize * len(str(text)) / 10.0))
    height = min(0.16, max(0.055, 0.0043 * fontsize))

    if ha == "right":
        x0, x1 = x - width, x
    elif ha == "center":
        x0, x1 = x - width / 2.0, x + width / 2.0
    else:
        x0, x1 = x, x + width

    if va == "bottom":
        y0, y1 = y, y + height
    elif va == "center":
        y0, y1 = y - height / 2.0, y + height / 2.0
    else:
        y0, y1 = y - height, y

    return x0, x1, y0, y1


def choose_axes_label_position(
    ax,
    text,
    candidates,
    *,
    ha="left",
    va="top",
    fontsize=15,
    pad=0.018,
):
    """
    Pick the first axes-coordinate label position that avoids plotted data.

    This lightweight collision check samples line and scatter artists already on
    the axes and checks whether finite points fall inside an approximate text
    box. If every candidate overlaps, the least-bad candidate is returned.
    """
    points = _artist_points_in_axes(ax)
    if points.size == 0:
        return candidates[0]

    best = candidates[0]
    best_count = None
    for x, y in candidates:
        x0, x1, y0, y1 = _label_box_axes(x, y, text, ha=ha, va=va, fontsize=fontsize)
        x0 -= pad
        x1 += pad
        y0 -= pad
        y1 += pad
        in_box = (
            (points[:, 0] >= x0)
            & (points[:, 0] <= x1)
            & (points[:, 1] >= y0)
            & (points[:, 1] <= y1)
        )
        count = int(in_box.sum())
        if count == 0:
            return (x, y)
        if best_count is None or count < best_count:
            best = (x, y)
            best_count = count
    return best


def add_collision_aware_grb_label(
    ax,
    text,
    *,
    corner="upper left",
    candidates=None,
    fontsize=15,
    fontweight="semibold",
    zorder=1000,
):
    """Add a GRB panel label and nudge it away from existing plotted data."""
    if not text:
        return None
    label = str(text)
    if not label.upper().startswith("GRB "):
        label = f"GRB {label}"

    if candidates is None:
        if corner == "upper right":
            ha = "right"
            candidates = [
                (0.965, 0.96),
                (0.965, 0.875),
                (0.965, 0.79),
                (0.965, 0.705),
                (0.90, 0.96),
                (0.90, 0.875),
            ]
        else:
            ha = "left"
            candidates = [
                (0.02, 0.96),
                (0.02, 0.875),
                (0.02, 0.79),
                (0.02, 0.705),
                (0.08, 0.96),
                (0.08, 0.875),
            ]
    else:
        ha = "right" if "right" in corner else "left"

    x, y = choose_axes_label_position(ax, label, candidates, ha=ha, va="top", fontsize=fontsize)
    return ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        ha=ha,
        va="top",
        fontsize=fontsize,
        fontweight=fontweight,
        zorder=zorder,
    )


def get_best_index(sampler):
    """ Returns the index with the highest log posterior. """
    return np.nanargmax(sampler.get_log_prob(flat=True))


def get_best_samples(sampler):
    """ Returns the MCMC samples with the highest log posterior. """
    return sampler.get_chain(flat=True)[get_best_index(sampler)]


def crosses(x, y):
    """
    Do ``x`` and ``y`` cross?

    Parameters
    ----------
    x, y : np.ndarray
        Arrays of same shape.

    Returns
    -------
    int
        The first index of crossing. If no crossing was
        found, returns -1.
    """
    cross_idx = np.where(np.diff(np.sign(x - y)))[0]
    return -1 if len(cross_idx) == 0 else cross_idx[0]


class CSVReader:
    """
    Reads an input CSV.

    Parameters
    ----------
    path : str | Path
        Location to the csv file.

    Attributes
    ----------
    df : pd.DataFrame
        Pandas representation of the CSV file.
    """
    _req_headers = (
        'Time', 'TimeUnits', 'Value', 'ValueType',
        'ValueLower', 'ValueUpper', 'ValueUnits'
    )

    def __init__(self, path: str | Path, sort=True):
        df = pd.read_csv(path)
        if sort:
            self.df = self._sort(df)
        else:
            self.df = df

    @staticmethod
    def _sort(df):
        """ Sort the dataframe object. """
        quantities = [t * u.Unit(unit) for t, unit in zip(df["Time"], df["TimeUnits"])]
        times_in_seconds = [q.to(u.s).value for q in quantities]
        df["Time_sec"] = times_in_seconds
        return df.sort_values("Time_sec").reset_index(drop=True)

    def rows(self):
        """ Return the rows of the CSV file. """
        return self.df.itertuples(name='Observation')


class TOMLReader:
    """
    Reads an input TOML.

    Parameters
    ----------
    path : str | Path
        The path to the TOML file.

    Attributes
    ----------
    data : dict
        The file data.
    """
    def __init__(self, path: str | Path):
        self.path = path
        self.data = self.read()

    def read(self) -> dict:
        """
        Opens the TOML file at ``path``.

        Returns
        -------
        dict
            A dictionary of TOML data.
        """
        with open(self.path, "rb") as f:
            return tomllib.load(f)

    @staticmethod
    def validate_value(name: str, value, expected_type) -> None:
        """

        Raises
        ------
        TypeError
            If encounters unexpected value.
        """
        if not isinstance(value, expected_type):
            raise TypeError(f'Received unexpected value for {name}.')

    def get_section(self, section: str, optional: bool = False) -> dict | None:
        """
        Checks that the section exists and returns it if it does.

        Parameters
        ----------
        section : str
            The TOML section name.

        optional : bool, optional, default=False
            If ``True``, does not raise an exception if section does not
            exist. Instead, returns ``None``.

        Returns
        -------
        dict
            The section dictionary.

        Raises
        ------
        ValueError
            If the section does not exist and optional is ``False``.
        """
        if (data := self.data.get(section, None)) is None and not optional:
            raise ValueError(
                f'{self.path} does not contain a {section} section.'
            )

        return data


class MCMCSettingsReader(TOMLReader):
    """
    Reader for MCMC Settings TOML config file.

    Attributes
    ----------
    num_walkers : float
        The number of walkers.

    burn_length : float
        The number of iterations to burn.

    run_length : float
        The number of iterations to run.
    """
    def __init__(self, path: str | Path, live_dangerously: bool = False):
        """
        Parameters
        ----------
        live_dangerously : bool, optional
            If ``True``, skips the validation process.
        """
        super().__init__(path)

        if not live_dangerously:
            self.validate()

        sampler = self.data.get('sampler')
        self.name = sampler.get('Name')
        self.num_walkers = sampler.get('num_walkers')
        self.burn_length = sampler.get('burn_length')
        self.run_length = sampler.get('run_length')
        self.ntemps = sampler.get('ntemps')
        self.workers = sampler.get('workers')
        self.checkpoint_interval = sampler.get('checkpoint_interval', 0)

    def validate(self) -> None:
        """ Validates that the MCMC settings file is valid. """
        self.validate_sampler()

    def validate_sampler(self) -> None:
        """ Validates that the sampler section is valid. """
        sampler = self.get_section('sampler')

        self.validate_value('burn_length', sampler.get('burn_length'), int)
        self.validate_value('run_length',  sampler.get('run_length'),  int)
        self.validate_value('num_walkers', sampler.get('num_walkers'), int)

        checkpoint_interval = sampler.get('checkpoint_interval', 0)
        self.validate_value('checkpoint_interval', checkpoint_interval, int)
        if checkpoint_interval < 0:
            raise ValueError('checkpoint_interval must be >= 0.')


# <editor-fold desc="Math">
def hill(x1, x2, w):
    """ Decreasing hill function. """
    return w * x1 + (1.0 - w) * x2

def chi_squared(
    f: np.ndarray[float],
    y: np.ndarray[float],
    e: np.ndarray[float],
    s = None,
) -> float:
    """
    Calculates the chi-squared value.

    Parameters
    ----------
    f : np.ndarray of float
        The predicted values.

    y : np.ndarray of float
        The observed values.

    e : np.ndarray of float
        The uncertainty in the observed values.

    s : float or np.ndarray of float, optional
        The slop parameter.

    Returns
    -------
    float or Quantity
        The chi-squared value.
    """
    if s is None:
        return np.sum(((y - f) / e) ** 2)

    return chi_squared_eff(f, y, e, s)


def chi_squared_eff(
    f: np.ndarray[float],
    y: np.ndarray[float],
    e: np.ndarray[float],
    s,
) -> float:
    """
    When the slop parameter, `s`, is provided, the
    chi-squared calculation accounts for additional
    unknown variances. When `s > 0`, the effective
    uncertainties increase, decreasing the penalty
    for model-data mismatches but adding a penalty
    for increasing `s` through the normalization term.

    Parameters
    ----------
    f : np.ndarray of float
        The modeled values.

    y : np.ndarray of float
        The observed values.

    e : np.ndarray of float
        The uncertainty in the observed values.

    s : float or np.ndarray of float
        The log slop parameter.

    Returns
    -------
    float
        The effective chi-squared value.
    """
    # Convert slop to linear space
    s_lin_avg = f * (10**s - 10**-s) / 2

    # Combine the slop and data uncertainties
    sig = np.sqrt(s_lin_avg ** 2 + e ** 2)

    # return chi-squared effective
    return np.sum(2 * np.log(sig) + ((y - f) / sig) ** 2)


def to_scale(
    value: float,
    from_s: str | ScaleType,
    to_s: str | ScaleType
) -> float:
    """
    Converts ``value`` from ``from_s`` to ``to_s``.

    Parameters
    ----------
    value : float
        The value to convert.

    from_s : str or ScaleType
        The scale of ``value``.

    to_s : str or ScaleType
        The new scale type.

    Returns
    -------
    float
        The converted value.
    """
    if isinstance(from_s, str):
        from_s = ScaleType(from_s)

    if isinstance(to_s, str):
        to_s = ScaleType(to_s)

    if from_s == to_s:
        return value

    match to_s:
        case ScaleType.LOG:
            return to_log(value, from_s)
        case ScaleType.LN:
            return to_ln(value, from_s)
        case ScaleType.LINEAR:
            return to_linear(value, from_s)


def to_log(value: float, scale: ScaleType) -> float:
    """
    Converts ``value`` from ``scale`` to log10.

    Parameters
    ----------
    value : float
        The value to convert.

    scale : ScaleType
        The scale of ``value``.

    Returns
    -------
    float
        The converted value.
    """
    match scale:
        case ScaleType.LOG:
            return value
        case ScaleType.LN:
            return value / math.log(10)
        case ScaleType.LINEAR:
            return math.log10(value)


def to_ln(value: float, scale: ScaleType) -> float:
    """
    Converts ``value`` from ``scale`` to log.

    Parameters
    ----------
    value : float
        The value to convert.

    scale : ScaleType
        The scale of ``value``.

    Returns
    -------
    float
        The converted value.
    """
    match scale:
        case ScaleType.LN:
            return value
        case ScaleType.LOG:
            return value * math.log(10)
        case ScaleType.LINEAR:
            return math.log(value)


def to_linear(value: float, scale: ScaleType) -> float:
    """
    Converts ``value`` from ``scale`` to linear.

    Parameters
    ----------
    value : float
        The value to convert.

    scale : ScaleType
        The scale of ``value``.

    Returns
    -------
    float
        The converted value.
    """
    match scale:
        case ScaleType.LINEAR:
            return value
        case ScaleType.LOG:
            return 10 ** value
        case ScaleType.LN:
            return math.exp(value)
# </editor-fold>


# <editor-fold desc="Project Navigation">
def get_project_parent_path() -> Path:
    """
    Returns the project's parent directory.

    Returns
    -------
    Path
        The project's parent directory.
    """
    return get_project_root().parent


def get_project_root() -> Path:
    """
    Returns the project root directory.

    Returns
    -------
    Path
        The project root directory.
    """
    return Path(__file__).parent.parent.parent


def get_models_path() -> Path:
    """
    Returns the project models directory.

    Returns
    -------
    Path
        The project models directory.
    """
    return get_project_root() / 'jetfit' / 'models'


def get_results_path() -> Path:
    """
    Returns the project results directory.

    Returns
    -------
    Path
        The project results directory.
    """
    return get_project_root() / 'jetfit' / 'results' /'Vegastesting' / 'test1'


def get_resource_path() -> Path:
    """
    Returns the project resource directory.

    Returns
    -------
    Path
        The project resource directory.
    """
    return get_project_root() / 'jetfit' / 'resources'


def get_event_path(category: str, event: str) -> Path:
    """
    Returns the path to the event's resource directory.

    Parameters
    ----------
    category : str

    event : str
        Name of event directory in resources

    Returns
    -------
    Path
        The event resource path.
    """
    return get_resource_path() / category / event


def get_input_csv_path(category: str, event: str) -> Path:
    """
    Returns the path to the input csv file.

    Parameters
    ----------
    category : str

    event : str
        Name of event directory in resources

    Notes
    -----
    The input CSV file should be named the same as the event directory.

    Returns
    -------
    Path
        The input CSV file path.
    """
    return get_event_path(category, event) / f'{event}.csv'


def get_mcmc_settings_path() -> Path:
    """ Returns the path to the MCMC settings. """
    return get_project_root() / 'jetfit' / 'mcmc' / 'settings.toml'


def get_boosted_fireball_path():
    """ Returns the path to the boosted fireball root directory. """
    return get_models_path() / 'boosted'


def get_hydro_sim_table_path() -> Path:
    """
    Returns the path to the hydrodynamic simulation table.

    Returns
    -------
    Path
        The input hydrodynamic simulation table.
    """
    return get_project_root() / 'rsrcs' / 'hydro_sim_new.h5'
#</editor-fold>
