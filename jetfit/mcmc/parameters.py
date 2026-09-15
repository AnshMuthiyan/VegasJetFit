from pathlib import Path
import warnings

import numpy as np

from jetfit.core.structs import ScaleType
from jetfit.core import utils
from jetfit.mcmc import priors


DEFAULT_SOURCE_EXTINCTION_MODEL = 'trotter2011'
SOURCE_EXTINCTION_MODELS = ('trotter2011', 'ccm89')
SOURCE_EXTINCTION_REFERENCE_COMMENTS = (
    'Source-frame dust-law references:',
    'Trotter, A. S. 2011, UNC-Chapel Hill PhD thesis, DOI 10.17615/2gjp-g156.',
    'Cardelli, Clayton, and Mathis 1989, ApJ, 345, 245 (CCM89).',
    'Allowed: "trotter2011" (default for new configs) or "ccm89".',
)
_SOURCE_EXTINCTION_MODEL_ALIASES = {
    'trotter': 'trotter2011',
    'trotter2011': 'trotter2011',
    'ccm': 'ccm89',
    'ccm89': 'ccm89',
}

IGM_ABSORPTION_MODELS = ('none', 'inoue2014')
HOST_HI_ABSORPTION_MODELS = ('none', 'trotter2011')
HYDROGEN_ABSORPTION_REFERENCE_COMMENTS = (
    'Neutral-hydrogen absorption references (separate from dust extinction):',
    'Inoue et al. 2014, MNRAS, 442, 1805: mean intergalactic Lyman absorption.',
    'Trotter 2011 thesis, Section 3.4.1: host DLA and source Lyman limit.',
    'Totani et al. 2006, PASJ, 58(3), 485: host damped-Lyman-alpha profile.',
    'Allowed IGM models: "none" or "inoue2014".',
    'Allowed host H I models: "none" or "trotter2011" (requires nhi_host).',
)
_IGM_ABSORPTION_MODEL_ALIASES = {
    'none': 'none',
    'off': 'none',
    'inoue': 'inoue2014',
    'inoue14': 'inoue2014',
    'inoue2014': 'inoue2014',
}
_HOST_HI_ABSORPTION_MODEL_ALIASES = {
    'none': 'none',
    'off': 'none',
    'trotter': 'trotter2011',
    'trotter2011': 'trotter2011',
}


def normalize_source_extinction_model(value):
    """Return the canonical source-frame extinction model name."""
    if value is None:
        return DEFAULT_SOURCE_EXTINCTION_MODEL

    key = str(value).strip().lower().replace('-', '').replace('_', '')
    try:
        return _SOURCE_EXTINCTION_MODEL_ALIASES[key]
    except KeyError as exc:
        choices = ', '.join(SOURCE_EXTINCTION_MODELS)
        raise ValueError(
            f"Unknown source extinction model {value!r}; choose one of: {choices}."
        ) from exc


def _normalize_model_name(value, aliases, choices, label):
    if value is None:
        return 'none'
    key = str(value).strip().lower().replace('-', '').replace('_', '')
    try:
        return aliases[key]
    except KeyError as exc:
        allowed = ', '.join(choices)
        raise ValueError(
            f"Unknown {label} {value!r}; choose one of: {allowed}."
        ) from exc


def normalize_igm_absorption_model(value):
    """Return the canonical intergalactic H I absorption model name."""
    return _normalize_model_name(
        value,
        _IGM_ABSORPTION_MODEL_ALIASES,
        IGM_ABSORPTION_MODELS,
        'IGM absorption model',
    )


def normalize_host_hi_absorption_model(value):
    """Return the canonical host-galaxy H I absorption model name."""
    return _normalize_model_name(
        value,
        _HOST_HI_ABSORPTION_MODEL_ALIASES,
        HOST_HI_ABSORPTION_MODELS,
        'host H I absorption model',
    )


def source_extinction_model_from_config(config):
    """Resolve explicit selection or infer an unmarked legacy CCM block."""
    configured = config.get('source_extinction_model')
    if configured is not None:
        return normalize_source_extinction_model(configured)

    extinction = config.get('extinction') or []
    names = {
        entry.get('name') for entry in extinction if isinstance(entry, dict)
    }
    trotter_markers = {
        name for name in names
        if isinstance(name, str) and (
            name in {'av_source_frame', 'c2', 'c4'}
            or name.startswith('delta_')
        )
    }
    if 'ebv_source_frame' in names and not trotter_markers:
        return 'ccm89'
    return DEFAULT_SOURCE_EXTINCTION_MODEL


def source_extinction_toml_lines(value):
    """Return a referenced TOML model-selection block."""
    model = normalize_source_extinction_model(value)
    return [
        *(f'# {line}' for line in SOURCE_EXTINCTION_REFERENCE_COMMENTS),
        f"source_extinction_model = '{model}'",
    ]


def hydrogen_absorption_toml_lines(igm_model='none', host_model='none'):
    """Return a referenced TOML block selecting the two gas components."""
    igm = normalize_igm_absorption_model(igm_model)
    host = normalize_host_hi_absorption_model(host_model)
    return [
        *(f'# {line}' for line in HYDROGEN_ABSORPTION_REFERENCE_COMMENTS),
        f"igm_absorption_model = '{igm}'",
        f"host_hi_absorption_model = '{host}'",
    ]


def hydrogen_absorption_models_from_config(config):
    """Resolve both gas-model selections from a configuration mapping."""
    return (
        normalize_igm_absorption_model(config.get('igm_absorption_model')),
        normalize_host_hi_absorption_model(
            config.get('host_hi_absorption_model')
        ),
    )


def add_hydrogen_absorption_toml_comments(text):
    """Add standard gas references before explicit TOML selection keys."""
    marker = '# Neutral-hydrogen absorption references'
    if marker in text:
        return text

    lines = text.splitlines()
    selection_indices = [
        index for index, line in enumerate(lines)
        if line.strip().startswith((
            'igm_absorption_model', 'host_hi_absorption_model'
        ))
    ]
    if not selection_indices:
        return text

    configured = {}
    for index in selection_indices:
        key, value = lines[index].split('=', 1)
        configured[key.strip()] = value.strip().strip('"\'')
    first = selection_indices[0]
    lines = [
        line for index, line in enumerate(lines)
        if index not in set(selection_indices)
    ]
    block = hydrogen_absorption_toml_lines(
        configured.get('igm_absorption_model', 'none'),
        configured.get('host_hi_absorption_model', 'none'),
    )
    lines[first:first] = block
    suffix = '\n' if text.endswith('\n') else ''
    return '\n'.join(lines) + suffix


def add_source_extinction_toml_comments(text):
    """Add the standard references before an existing TOML selection key."""
    marker = '# Source-frame dust-law references:'
    if marker in text:
        return text

    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip().startswith('source_extinction_model'):
            value = line.split('=', 1)[1].strip().strip('"\'')
            lines[index:index + 1] = source_extinction_toml_lines(value)
            suffix = '\n' if text.endswith('\n') else ''
            return '\n'.join(lines) + suffix
    return text


def factory(d: dict):
    """
    Instantiates a MCMCParameter from the dict ``d``.

    Parameters
    ----------
    d : dict
        The parameter values.

    Returns
    -------
    MCMCFixedParameter or MCMCFittingParameter
        Instantiated from the dict ``d``.
    """
    return MCMCFittingParameter.from_dict(d) if 'prior' in d \
        else MCMCFixedParameter.from_dict(d)


# noinspection PyUnresolvedReferences
class Parameters:
    """
    Container class for afterglow parameters.

    Parameters
    ----------
    params : array_like
        The fixed and fitting MCMC parameters.

    model : str
        The name of the model that the parameters belong to.

    Attributes
    ----------
    all : np.ndarray
        All MCMC parameters.

    fixed : np.ndarray
        The fixed MCMC parameters.

    fitting : np.ndarray
        The fitting MCMC parameters.

    pos : dict
        The positions of the parameters and their
        categories.
    """
    # Nyaa :3
    _valid_cats = (
        'model', 'extinction', 'absorption', 'host', 'offsets', 'slop'
    )

    def __init__(
        self, params, model, source_extinction_model=None,
        source_extinction_model_origin='default',
        igm_absorption_model=None, host_hi_absorption_model=None,
        igm_absorption_model_origin='legacy_default_off',
        host_hi_absorption_model_origin='legacy_default_off',
    ):
        self.model = model
        self.source_extinction_model = normalize_source_extinction_model(
            source_extinction_model
        )
        self.source_extinction_model_origin = source_extinction_model_origin
        self.igm_absorption_model = normalize_igm_absorption_model(
            igm_absorption_model
        )
        self.host_hi_absorption_model = normalize_host_hi_absorption_model(
            host_hi_absorption_model
        )
        self.igm_absorption_model_origin = igm_absorption_model_origin
        self.host_hi_absorption_model_origin = host_hi_absorption_model_origin

        if not isinstance(params, np.ndarray):
            params = np.asarray(params)

        init_arr = np.full(params.size, False)

        # Initialize positions for each cat
        self.pos = {
            cat : np.array(init_arr, copy=True)
            for cat in self._valid_cats
        }

        # Initialize positions for additional useful locators
        self.pos['fixed'] = np.array(init_arr, copy=True)
        self.pos['fitting'] = np.array(init_arr, copy=True)

        # Determine positions of the categories
        # Stored once here instead of in a prop
        # to speed up MCMC as much as possible.
        for i, p in enumerate(params):
            self.pos['fixed'][i] = p.fixed
            self.pos['fitting'][i] = not p.fixed
            self.pos[p.category][i] = True

        self.all = params
        self.fixed = params[self.pos['fixed']]
        self.fitting = params[self.pos['fitting']]
        self.validate_source_extinction_model()
        self.validate_hydrogen_absorption_models()

    @classmethod
    def from_toml(cls, d):
        """
        Instantiate ``Parameters`` from a dict.

        Parameters
        ----------
        d : dict or str or Path
            Either a path to the toml file or a dict
            representing the TOML file.

        Returns
        -------
        Parameters
            Instantiated from ``d``.
        """
        if isinstance(d, (str, Path)):
            d = utils.TOMLReader(d).read()

        # Do not mutate a caller-owned dictionary while removing TOML metadata.
        d = dict(d)
        model = d.pop('name')
        configured_source_model = d.pop('source_extinction_model', None)
        configured_igm_model = d.pop('igm_absorption_model', None)
        configured_host_hi_model = d.pop('host_hi_absorption_model', None)

        params = []
        for cat, vals in d.items():
            for val in vals:
                params.append(
                    factory(val | {'category': cat})
                )

        source_model_origin = 'config'
        if configured_source_model is None:
            inferred_config = {'extinction': [
                {'name': p.name}
                for p in params if p.category == 'extinction'
            ]}
            configured_source_model = source_extinction_model_from_config(
                inferred_config
            )
            if configured_source_model == 'ccm89':
                source_model_origin = 'legacy_parameter_inference'
                warnings.warn(
                    "Model TOML has no 'source_extinction_model'; inferred "
                    "'ccm89' from legacy 'ebv_source_frame'. Add "
                    "source_extinction_model = 'ccm89' near the top of the file.",
                    UserWarning,
                    stacklevel=2,
                )
            else:
                source_model_origin = 'default'

        return cls(
            np.asarray(params, dtype=object),
            model,
            source_extinction_model=configured_source_model,
            source_extinction_model_origin=source_model_origin,
            igm_absorption_model=configured_igm_model,
            host_hi_absorption_model=configured_host_hi_model,
            igm_absorption_model_origin=(
                'config' if configured_igm_model is not None
                else 'legacy_default_off'
            ),
            host_hi_absorption_model_origin=(
                'config' if configured_host_hi_model is not None
                else 'legacy_default_off'
            ),
        )

    def set_source_extinction_model(self, value, origin='override'):
        """Apply and validate an explicit source-frame extinction-model override."""
        old_model = self.source_extinction_model
        old_origin = self.source_extinction_model_origin
        self.source_extinction_model = normalize_source_extinction_model(value)
        self.source_extinction_model_origin = origin
        try:
            self.validate_source_extinction_model()
        except Exception:
            self.source_extinction_model = old_model
            self.source_extinction_model_origin = old_origin
            raise

    def validate_source_extinction_model(self):
        """Reject mixed or incomplete source-frame extinction configurations."""
        names = {
            p.name for p in self.all if p.category == 'extinction'
        }
        ccm_names = {'ebv_source_frame', 'rv_source_frame'}
        trotter_names = {
            name for name in names
            if name in {'av_source_frame', 'c2', 'c4'}
            or name.startswith('delta_')
        }
        source_names = (names & ccm_names) | trotter_names
        if not source_names:
            return

        if self.source_extinction_model == 'ccm89':
            if trotter_names:
                found = ', '.join(sorted(trotter_names))
                raise ValueError(
                    "source_extinction_model='ccm89' cannot be used with "
                    f"Trotter parameters: {found}."
                )
            if 'ebv_source_frame' not in names:
                raise ValueError(
                    "source_extinction_model='ccm89' requires "
                    "'ebv_source_frame' when source-frame dust is configured."
                )
            return

        forbidden = names & ccm_names
        if forbidden:
            found = ', '.join(sorted(forbidden))
            raise ValueError(
                "source_extinction_model='trotter2011' cannot be used with "
                f"CCM parameters: {found}."
            )
        required = {'av_source_frame', 'c2', 'c4'}
        missing = required - names
        if missing:
            found = ', '.join(sorted(missing))
            raise ValueError(
                "source_extinction_model='trotter2011' requires "
                f"these parameters when source-frame dust is configured: {found}."
            )

    def set_hydrogen_absorption_models(
        self, *, igm_model=None, host_model=None, origin='override'
    ):
        """Atomically override either gas model and validate the combination."""
        old = (
            self.igm_absorption_model,
            self.host_hi_absorption_model,
            self.igm_absorption_model_origin,
            self.host_hi_absorption_model_origin,
        )
        if igm_model is not None:
            self.igm_absorption_model = normalize_igm_absorption_model(igm_model)
            self.igm_absorption_model_origin = origin
        if host_model is not None:
            self.host_hi_absorption_model = normalize_host_hi_absorption_model(
                host_model
            )
            self.host_hi_absorption_model_origin = origin
        try:
            self.validate_hydrogen_absorption_models()
        except Exception:
            (
                self.igm_absorption_model,
                self.host_hi_absorption_model,
                self.igm_absorption_model_origin,
                self.host_hi_absorption_model_origin,
            ) = old
            raise

    def validate_hydrogen_absorption_models(self):
        """Reject gas configurations without a fixed, known source redshift."""
        absorption = [
            p for p in self.all if p.category == 'absorption'
        ]
        names = {p.name for p in absorption}
        unknown = names - {'nhi_host'}
        if unknown:
            found = ', '.join(sorted(unknown))
            raise ValueError(f'Unknown absorption parameters: {found}.')

        enabled = (
            self.igm_absorption_model != 'none'
            or self.host_hi_absorption_model != 'none'
        )
        if enabled:
            redshift = [
                p for p in self.all
                if p.category == 'model' and p.name == 'z'
            ]
            if len(redshift) != 1 or not redshift[0].fixed:
                raise ValueError(
                    'Hydrogen absorption requires one fixed, known model redshift z.'
                )
            if redshift[0].scale != ScaleType.LINEAR:
                raise ValueError(
                    'Hydrogen absorption requires fixed redshift z on a linear scale.'
                )
            if not np.isfinite(redshift[0].value) or redshift[0].value < 0.0:
                raise ValueError(
                    'Hydrogen absorption requires a finite, non-negative redshift.'
                )

        if self.host_hi_absorption_model == 'trotter2011':
            if 'nhi_host' not in names:
                raise ValueError(
                    "host_hi_absorption_model='trotter2011' requires an "
                    "[[absorption]] parameter named 'nhi_host'."
                )
        elif names:
            raise ValueError(
                "Absorption parameters are configured while "
                "host_hi_absorption_model='none'."
            )

    def has(self, name):
        """
        Determines if ``name`` is in the parameter list.

        Parameters
        ----------
        name : str
            The name of the parameter to check.

        Returns
        -------
            True if ``name`` is in the parameter list.
        """
        return True if name in [p.name for p in self.all] else False

    def samples_to_dict(self, theta, cat=None, scale='linear'):
        """
        Maps MCMC samples to a dictionary.

        Parameters
        ----------
        theta : np.array of float
            The MCMC samples.

        cat : str, optional
            Limit the dictionary to the ``cat`` categories.

        scale : str, optional, default='linear'
            The scale to return the parameters in.

        Returns
        -------
        dict
            The parameters in dict form.
        """
        if theta.size != len(self.fitting):
            raise ValueError(
                f'Size mismatch: theta[{theta.size}] != params'
                f'[{len(self.fitting)}].'
            )

        # Define the categories to return ~Nyaa :3
        cats = [cat] if cat else self._valid_cats

        # Initialize the result with cats
        params = {cat: {} for cat in cats}

        # Needs to be in order of fitting then fixed (to match theta)
        for i, p in enumerate(np.concatenate([self.fitting, self.fixed])):
            if p.category in cats:
                val = utils.to_scale(
                    theta[i] if i < theta.size else p.value, p.scale, scale
                )
                params[p.category][p.name] = val

        return params


class MCMCParameter:
    """
    A parameter to be used with MCMC.

    Attributes
    ----------
    name : str
        The name of the parameter.

    scale : `jetfit.core.structs.ScaleType`
        The scale of the parameter.

    category : str
        One of: `model`, `extinction`, `absorption`, `host`,
        `offsets`, or `slop`

    group : str, optional
        The data group of the parameter.
    """
    def __init__(
        self,
        name: str,
        scale: ScaleType,
        category: str,
        group: str = None
    ):
        self.name = name
        self.scale = scale
        self.group = group
        self.category = category

    @classmethod
    def from_dict(cls, d: dict):
        """ Placeholder. """
        raise NotImplementedError(
            '`from_dict` method is not implemented.'
        )


class MCMCFixedParameter(MCMCParameter):
    """
    A fixed parameter to be used within a model for MCMC.

    Attributes
    ----------
    value : float
        The fixed value of the parameter.
    """
    def __init__(
            self,
            name: str,
            value: float,
            scale: ScaleType,
            category: str,
            group: str = None
    ):
        super().__init__(name, scale, category, group)
        self.value = value

    def __repr__(self) -> str:
        """ Human-readable string. """
        return (
            f'MCMCFixedParameter(name={self.name}, '
            f'cat={self.category}, '
            f'val={self.value})'
        )

    @classmethod
    def from_dict(cls, d: dict):
        """
        Instantiates the class from a dictionary.

        Parameters
        ----------
        d : dict
            The class attributes and values.

        Returns
        -------
        MCMCFixedParameter
            Instantiated from ``d``.
        """
        if not isinstance(d.get('value'), (int, float)):
            raise TypeError(
                f"Expected a number for value in `{d.get('name')}`. "
                f"Received `{type(d.get("value"))}` instead."
            )

        if not isinstance(d.get('scale'), str):
            raise TypeError(
                f'Expected type `str` for scale in `{d.get('name')}`. '
                f'Received `{type(d.get("scale"))}` instead.'
            )

        return cls(
            d.get('name'),
            d.get('value'),
            ScaleType(d.get('scale')),
            d.get('category'),
            d.get('group')
        )

    @property
    def fixed(self) -> bool:
        return True


class MCMCFittingParameter(MCMCParameter):
    """
    A free parameter to be sampled with the MCMC routine.

    Attributes
    ----------
    prior : `jetfit.core.enums.Prior`
        The prior probability distribution.
    """
    def __init__(
        self,
        name: str,
        scale: ScaleType,
        prior,
        category: str,
        group: str = None
    ):
        MCMCParameter.__init__(self, name, scale, category, group)
        self.prior = prior

    def __repr__(self) -> str:
        """ Human-readable string. """
        return (
            f'MCMCFittingParameter('
            f'name={self.name}, '
            f'cat={self.category})'
        )

    @classmethod
    def from_dict(cls, d: dict):
        """
        Instantiates the class from a dictionary.

        Parameters
        ----------
        d : dict
            The class attributes and values.

        Returns
        -------
        MCMCFittingParameter
            Instantiated from `d`.
        """
        if not isinstance(d.get('prior'), dict):
            raise TypeError(
                f'Expected type `dict` for prior in {d.get('name')}. '
                f'Received `{type(d.get("prior"))}` instead.'
            )

        if not isinstance(d.get('scale'), str):
            raise TypeError(
                f'Expected type `str` for scale in {d.get('name')}. '
                f'Received `{type(d.get("scale"))}` instead.'
            )

        return cls(
            d.get('name'),
            ScaleType(d.get('scale')),
            priors.prior_factory(d.get('prior')),
            d.get('category'),
            d.get('group')
        )

    @property
    def fixed(self) -> bool:
        return False
