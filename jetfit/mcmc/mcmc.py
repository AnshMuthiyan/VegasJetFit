import copy
import os
import multiprocessing as mp
from contextlib import contextmanager, nullcontext
from pathlib import Path

import emcee
import numpy as np
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from jetfit.core import utils
from jetfit.mcmc.trotter_extinction import (
    trotter_dust_prior,
    trotter_source_attenuation,
)

# Compatibility shim for older ptemcee releases on modern NumPy.
if not hasattr(np, 'float'):
    np.float = float  # type: ignore[attr-defined]

try:
    import ptemcee
except ImportError:
    # ptemcee is required if using parallel tempering
    pass


"""
MCMC framework for modeling afterglow light curves.

This module provides two adapters for the parallel tempered
sampler from ``ptemcee`` [1]_ and the ensemble sampler from
``emcee`` [2]_. 

The ``MCMC`` class can be used directly, but it is strongly
recommended to use the ``Ampy`` class instead. 

Notes
-----
Multiprocessing vs. Multithreading:

    When running MCMC sampling, you can parallelize likelihood
    (or posterior) evaluations in two ways:

    1. Multithreading
       - Threads share the same memory space and interpreter instance.
       - Low overhead for spawning and switching threads (i.e., fast!).
       - Requires Python v3.13 with free-threading enabled
       - Most libraries do not support multithreading yet.

    2. Multiprocessing
        - Each process has its own Python interpreter and memory space.
        - Bypasses the GIL entirely, enabling true parallelism on multiple cores.
        - Higher overhead to start processes and to pass data (i.e., slow!).
        - Useful if likelihood takes > ~1s and has dependencies that require the GIL.

The implementation for both is built into the ``MCMC`` class. Simply
specify the executor and number of workers. However, it is up to the
user to determine whether parallelization will actually be beneficial.

References
----------
.. [1] https://arxiv.org/abs/1501.05823

.. [2] https://arxiv.org/abs/1202.3665
"""


def get_pool_context(workers=None, executor='process'):
    """
    If ``executor==process`` and ``workers>1``:
        Returns a multiprocessing-based pool context (preferred),
        with ``ProcessPoolExecutor`` as a fallback.

        Since processes need to load everything into memory, this
        should only be used if the likelihood calculation takes
        about one-second or more to calculate.

    If ``executor==thread`` and ``workers>1``:
        Returns ``ThreadPoolExecutor(max_workers=workers)``.

        Note that unless a free-threaded Python is installed,
        multithreading will not yield any benefits. Even if a
        no-GIL Python version is used, the performance increase
        depends  on the likelihood implementation.

        Pure Python implementations will see a large performance
        increase. If the likelihood uses Cython, then it depends
        on how the code is compiled and optimized.

    Parameters
    ----------
    workers : int, optional, default=None
        The max number of workers.

    executor : str, optional, default='process'
        See above docstring for details. Must be ``process``
        or ``thread``.

    Returns
    -------
    ``ProcessPoolExecutor`` or ``ThreadPoolExecutor`` or ``nullcontext``
        The pool context manager.
    """
    if workers and workers > 1:

        if executor == 'process':
            try:
                return _multiprocessing_pool_context(workers)
            except Exception as exc:
                print(
                    "[get_pool_context] Failed to create multiprocessing pool "
                    f"({type(exc).__name__}: {exc}). Trying ProcessPoolExecutor."
                )

            try:
                pool = ProcessPoolExecutor(max_workers=workers)
                _verify_pool_workers(pool, workers)
                return pool
            except Exception as exc:
                print(
                    "[get_pool_context] Failed to create process pool "
                    f"({type(exc).__name__}: {exc}). Falling back to serial."
                )
                return nullcontext(None)

        if executor == 'thread':
            return ThreadPoolExecutor(max_workers=workers)

    return nullcontext(None)


def _pool_pid(_):
    """Return worker PID; used to verify pool fan-out."""
    return os.getpid()


def _verify_pool_workers(pool, workers):
    """
    Probe a pool by mapping a trivial task and reporting unique worker PIDs.

    This provides a runtime sanity check that process-based parallelization
    is actually active.
    """
    if os.environ.get('JETFIT_POOL_PROBE', '1') != '1':
        return

    tasks = max(int(workers) * 2, 2)
    try:
        pids = list(pool.map(_pool_pid, range(tasks)))
        unique = sorted(set(int(pid) for pid in pids))
        print(
            f"[get_pool_context] Active worker processes: "
            f"{len(unique)}/{workers} (pids={unique})"
        )
    except Exception as exc:
        print(
            "[get_pool_context] Worker verification failed "
            f"({type(exc).__name__}: {exc})."
        )


@contextmanager
def _multiprocessing_pool_context(workers):
    """
    Build a multiprocessing pool using the configured start method.

    Compared to ProcessPoolExecutor, multiprocessing.Pool is more robust
    on some macOS/sandboxed environments.
    """
    ctx = mp.get_context()
    start_method = ctx.get_start_method()
    print(
        "[get_pool_context] Using multiprocessing.Pool "
        f"(workers={workers}, start_method={start_method})"
    )

    pool = ctx.Pool(processes=int(workers))
    try:
        _verify_pool_workers(pool, workers)
        yield pool
    finally:
        pool.close()
        pool.join()


class PTSampler:
    """
    Provides an API adapter that matches ``emcee``.

    Parallel tempering in ``emcee`` stopped receiving
    support and was removed from official releases.

    Using the latest version of ``emcee`` that supports
    the PTSampler forces users to use very old packages
    that the PTSampler depends on.

    There is a community developed version called ``ptemcee``.
    However, the authors stopped maintaining it years ago.

    This class aims to provide an API that matches ``emcee``.
    Methods are only added on an as-needed basis and are by
    no means complete.

    Parameters
    ----------
    ntemps : int
        The number of temperatures.

    nwalkers : int
        The number of walkers.

    ndim : int
        The number of fitting dimensions.

    log_like, log_prior
        The log likelihood and log prior methods.

    log_l_args, log_p_args : array_like, optional
        The log likelihood and log prior arguments.

    log_l_kwargs, log_p_kwargs : array_like, optional
        The log likelihood and log prior kwargs.

    pool : optional
        An object with a ``map`` method that follows the
        same calling sequence as emcee's built-in ``map``
        function. This is generally used to compute the
        log-probabilities in parallel.

    kwargs
        Any kwargs accepted by ``ptemcee.Sampler``.
    """
    name = 'parallel_tempered'

    def __init__(
        self, ntemps, nwalkers, ndim, log_like, log_prior,
        log_l_args=(), log_p_args=(), log_l_kwargs=(), log_p_kwargs=(),
        pool=None, **kwargs
    ):
        # Keep constructor state so reset() can rebuild robustly across ptemcee variants.
        self._ctor = {
            'ntemps': ntemps,
            'nwalkers': nwalkers,
            'ndim': ndim,
            'log_like': log_like,
            'log_prior': log_prior,
            'log_l_args': tuple(log_l_args),
            'log_p_args': tuple(log_p_args),
            'log_l_kwargs': dict(log_l_kwargs),
            'log_p_kwargs': dict(log_p_kwargs),
            'pool': pool,
            'kwargs': dict(kwargs),
        }

        # Initialize the sampler
        self._sampler = self._new_sampler()
        self._chain = None
        self._iteration = 0
        self._temp0_chain_override = None
        self._temp0_logprob_override = None

        self._ndim = ndim
        self._ntemps = ntemps
        self._nwalkers = nwalkers
        self._legacy_chain_api = callable(getattr(self._sampler, 'chain', None))

    def _new_sampler(self):
        """Create ptemcee sampler for either legacy or current API."""
        c = self._ctor

        # Newer ptemcee API (e.g. exposes default_beta_ladder).
        if hasattr(ptemcee, 'default_beta_ladder'):
            return ptemcee.Sampler(
                c['nwalkers'],
                c['ndim'],
                c['log_like'],
                c['log_prior'],
                ntemps=c['ntemps'],
                pool=c['pool'],
                loglargs=list(c['log_l_args']),
                logpargs=list(c['log_p_args']),
                loglkwargs=dict(c['log_l_kwargs']),
                logpkwargs=dict(c['log_p_kwargs']),
                **c['kwargs'],
            )

        # Legacy ptemcee API.
        mapper = c['pool'].map if c['pool'] is not None else map
        return ptemcee.Sampler(
            c['nwalkers'],
            c['ndim'],
            c['log_like'],
            c['log_prior'],
            c['log_l_args'],
            c['log_p_args'],
            c['log_l_kwargs'],
            c['log_p_kwargs'],
            ptemcee.make_ladder(c['ndim'], c['ntemps']),
            mapper=mapper,
            **c['kwargs'],
        )

    @property
    def sampler(self):
        return self._sampler

    @property
    def chain(self):
        return self._chain

    @property
    def iteration(self):
        return self._iteration

    @property
    def ntemps(self):
        return self._ntemps

    @property
    def nwalkers(self):
        return self._nwalkers

    @property
    def ndim(self):
        return self._ndim

    @property
    def acor(self):
        return self.get_autocorr_time()

    @property
    def acceptance_fraction(self):
        if self._legacy_chain_api:
            return self.chain.jump_acceptance_ratio[0]
        return self.sampler.acceptance_fraction[0]

    @property
    def swap_acceptance_fraction(self):
        if self._legacy_chain_api:
            return self.chain.swap_acceptance_ratio[0]
        return self.sampler.tswap_acceptance_fraction[0]

    @property
    def lnprobability(self):
        return self.get_log_prob()

    def run_mcmc(self, x0, iterations, **kwargs):
        """
        Perform MCMC sampling.

        Parameters
        ----------
        x0 : np.ndarray
            The initial position vector.

        iterations : int
            The number of steps to run.

        kwargs
            Any kwargs accepted by ``ptemcee.Chain``.

        Returns
        -------
        np.ndarray with shape [ntemps, nwalkers, ndim]
            The last samples.
        """
        if self._legacy_chain_api:
            self._chain = self.sampler.chain(x0, **kwargs)
            self._chain.run(iterations)
            self._iteration = self._chain.length
            return self.chain.x[-1]

        self.sampler.run_mcmc(x0, iterations=iterations, **kwargs)
        self._chain = self.sampler
        self._iteration = int(self.sampler.time)
        return self.sampler.chain[:, :, -1, :]

    def reset(self):
        """
        Overwrites the sampler with a new one.

        There's no reset method in ``ptemcee`` that I'm aware
        of. Overwriting with a new sampler is safer than
        attempting to reset attributes individually.
        """
        self._sampler = self._new_sampler()
        self._legacy_chain_api = callable(getattr(self._sampler, 'chain', None))
        self._chain = None
        self._iteration = 0
        self._temp0_chain_override = None
        self._temp0_logprob_override = None

    def save(self, path):
        """
        Saves the chain and log posterior to ``path``.

        To load the data, do: data = np.load(path)
        To access the chain, do: data['chain']

        Parameters
        ----------
        path : str
            The path to save the file.
        """
        chain = (
            self._temp0_chain_override
            if self._temp0_chain_override is not None
            else self.get_chain()
        )
        lnprob = (
            self._temp0_logprob_override
            if self._temp0_logprob_override is not None
            else self.get_log_prob()
        )
        np.savez(path, chain=chain, lnprob=lnprob, betas=self.sampler.betas)

    def set_temp0_overrides(self, chain, log_prob):
        """
        Override the temperature-0 chain/log-prob arrays.

        Used when resuming ``parallel_tempered`` from checkpoints so the final
        outputs include both pre-resume and post-resume samples.
        """
        if chain is None or log_prob is None:
            self._temp0_chain_override = None
            self._temp0_logprob_override = None
            return

        chain = np.asarray(chain)
        log_prob = np.asarray(log_prob)

        if chain.ndim != 3:
            raise ValueError('Temp-0 chain override must have shape [steps, walkers, ndim].')
        if log_prob.ndim != 2:
            raise ValueError('Temp-0 log-prob override must have shape [steps, walkers].')
        if chain.shape[:2] != log_prob.shape:
            raise ValueError('Temp-0 chain/log-prob override shapes are inconsistent.')

        self._temp0_chain_override = np.array(chain, copy=True)
        self._temp0_logprob_override = np.array(log_prob, copy=True)
        self._iteration = int(chain.shape[0])

    def save_resume_state(
        self, path, completed_iterations, target_iterations=None,
        chain=None, lnprob=None, phase='production',
        burn_completed_iterations=None, burn_target_iterations=None,
    ):
        """
        Save resume state for ``parallel_tempered``.

        The saved chain/log-prob are temperature-0 (the posterior chain used by
        current analysis/plotting), while ``last_pos`` retains all temperatures
        needed to continue sampling.
        """
        state_path = Path(path)
        state_path.parent.mkdir(parents=True, exist_ok=True)

        if chain is None:
            chain = (
                self._temp0_chain_override
                if self._temp0_chain_override is not None
                else self.get_chain()
            )
        if lnprob is None:
            lnprob = (
                self._temp0_logprob_override
                if self._temp0_logprob_override is not None
                else self.get_log_prob()
            )

        save_kw = {
            'chain': chain,
            'lnprob': lnprob,
            'last_pos': self.get_last_sample(),
            'completed_iterations': int(completed_iterations),
            'betas': self.sampler.betas,
            'phase': str(phase),
        }
        if target_iterations is not None:
            save_kw['target_iterations'] = int(target_iterations)
        if burn_completed_iterations is not None:
            save_kw['burn_completed_iterations'] = int(burn_completed_iterations)
        if burn_target_iterations is not None:
            save_kw['burn_target_iterations'] = int(burn_target_iterations)

        np.savez(state_path, **save_kw)

    @staticmethod
    def load_resume_state(path):
        """ Load ``parallel_tempered`` resume state from ``path``. """
        state_path = Path(path)
        with np.load(state_path, allow_pickle=False) as data:
            required = ('chain', 'lnprob', 'last_pos')
            missing = [k for k in required if k not in data.files]
            if missing:
                raise ValueError(
                    f'{state_path} is missing required resume keys: {missing}'
                )

            chain = np.array(data['chain'], copy=True)
            lnprob = np.array(data['lnprob'], copy=True)
            last_pos = np.array(data['last_pos'], copy=True)

            if chain.ndim != 3:
                raise ValueError(
                    f'{state_path} chain has unexpected shape {chain.shape}; '
                    'expected [steps, walkers, ndim].'
                )
            if lnprob.ndim != 2:
                raise ValueError(
                    f'{state_path} lnprob has unexpected shape {lnprob.shape}; '
                    'expected [steps, walkers].'
                )
            if chain.shape[:2] != lnprob.shape:
                raise ValueError(
                    f'{state_path} has inconsistent chain/log-prob shapes: '
                    f'{chain.shape} vs {lnprob.shape}.'
                )
            if last_pos.ndim != 3:
                raise ValueError(
                    f'{state_path} last_pos has unexpected shape {last_pos.shape}; '
                    'expected [ntemps, walkers, ndim].'
                )

            if 'completed_iterations' in data.files:
                completed_iterations = int(data['completed_iterations'])
            else:
                completed_iterations = int(chain.shape[0])

            target_iterations = None
            if 'target_iterations' in data.files:
                target_iterations = int(data['target_iterations'])
            phase = 'production'
            if 'phase' in data.files:
                phase = str(np.asarray(data['phase']).item())
            burn_completed_iterations = 0
            if 'burn_completed_iterations' in data.files:
                burn_completed_iterations = int(data['burn_completed_iterations'])
            burn_target_iterations = None
            if 'burn_target_iterations' in data.files:
                burn_target_iterations = int(data['burn_target_iterations'])

            return {
                'chain': chain,
                'lnprob': lnprob,
                'last_pos': last_pos,
                'completed_iterations': completed_iterations,
                'target_iterations': target_iterations,
                'phase': phase,
                'burn_completed_iterations': burn_completed_iterations,
                'burn_target_iterations': burn_target_iterations,
            }

    def draw_positions(self, params, models, initial_positions=None):
        """
        Draw the initial positions from the priors.

        PTSampler requires that the start positions be
        valid (i.e., log posterior is finite). To meet
        this, any invalid position is overwritten with
        the best position for that temperature.

        Parameters
        ----------
        params : Parameters
            The MCMC parameters.

        models : MCMCModel
            The MCMC models.

        Returns
        -------
        np.ndarray of float with shape [ntemps, nwalkers, ndim]
            The starting positions.
        """
        supplied = initial_positions is not None
        if supplied:
            pos = np.asarray(initial_positions, dtype=float).copy()
            expected = (self.ntemps, self.nwalkers, self.ndim)
            if pos.shape != expected:
                raise ValueError(f'Initial-position shape {pos.shape} does not match {expected}.')
            if not np.isfinite(pos).all():
                raise ValueError('Initial positions must all be finite.')
        else:
            pos = np.zeros((self.ntemps, self.nwalkers, self.ndim))
            for i in range(self.ntemps):
                for j, p in enumerate(params.fitting):
                    pos[i, :, j] = p.prior.draw(self.nwalkers)

        # Overwrite invalid positions (inf or NaN log-posterior) with each
        # temperature's best position. If no valid positions exist for a
        # temperature, resample up to max_tries before failing.
        log_p = np.full((self.ntemps, self.nwalkers), -np.inf)

        for i in range(self.ntemps):
            # evaluate log-posterior for each walker, treating NaN as -inf
            for j in range(self.nwalkers):
                lp = log_posterior_fn(pos[i, j], params, models)  # type: ignore
                if np.isnan(lp):
                    lp = -np.inf
                log_p[i, j] = lp

            valid = np.isfinite(log_p[i])
            print(f'Temperature {i}: {valid.sum()} valid walkers out of {self.nwalkers}')
            if supplied and not valid.all():
                raise ValueError(
                    f'Posterior-informed initial cloud has {(~valid).sum()} invalid walker(s) '
                    f'at temperature {i}.'
                )
            if valid.any():
            # replace invalid walkers with the best walker for this temp
                best = np.nanargmax(log_p[i])
                if not valid.all():
                    pos[i][~valid] = np.array(pos[i][best], copy=True)
            else:
            # no valid walkers: try to resample positions until at least one is valid
                max_tries = 1000
                for attempt in range(max_tries):
                    # resample all walkers from priors
                    for k, p in enumerate(params.fitting):
                        pos[i, :, k] = p.prior.draw(self.nwalkers)
                    for j in range(self.nwalkers):
                        lp = log_posterior_fn(pos[i, j], params, models)  # type: ignore
                        if np.isnan(lp):
                            lp = -np.inf
                        log_p[i, j] = lp
                    valid = np.isfinite(log_p[i])
                    if valid.any():
                        best = np.nanargmax(log_p[i])
                        pos[i][~valid] = np.array(pos[i][best], copy=True)
                        break
                else:
                    raise RuntimeError(
                        f'Failed to initialize any valid walker for temperature {i}'
                    )
            # replace any remaining invalids with the best
            best = np.nanargmax(log_p[i])
            pos[i][~np.isfinite(log_p[i])] = np.array(pos[i][best], copy=True)

        return pos

    def get_autocorr_time(self):
        """ Returns the autocorrelation time for the 0th temperature. """
        if self._legacy_chain_api:
            return self.chain.get_acts()[0]
        return self.sampler.get_autocorr_time()[0]

    def get_last_sample(self):
        """ Returns last samples with shape [ntemps, nwalkers, ndim]. """
        if self._legacy_chain_api:
            if self.chain is None:
                raise AttributeError(
                    'Tried to get the last sample, but there are no '
                    'samples. Have you called `run_mcmc` yet?'
                )
            return self.chain.x[-1]

        if self.sampler.chain is None:
            raise AttributeError(
                'Tried to get the last sample, but there are no '
                'samples. Have you called `run_mcmc` yet?'
            )
        return self.sampler.chain[:, :, -1, :]

    def get_value(self, name, flat=False, thin=1, discard=0, temp=0):
        """
        Get the attribute ``name``.

        Parameters
        ----------
        name : str
            Name of the attribute to retrieve.

        flat : bool, optional, default=False
            Flatten the chain across the ensemble.

        thin : int, optional, default=1
            Take only every ``thin`` steps from the
            chain.

        discard : int, optional, default=0
            Discard the first ``discard`` steps in the
            chain as burn-in.

        temp : int, optional, default=0
            Take only the ``temp`` attribute. Defaults to
            the temp at index ``0`` which is the highest
            probability temperature.

        Returns
        -------
        np.ndarray
        """
        if temp == 0:
            override = (
                self._temp0_chain_override
                if name == 'x'
                else self._temp0_logprob_override
                if name == 'logP'
                else None
            )
            if override is not None:
                v = override[discard + thin - 1::thin]
                if flat:
                    s = list(v.shape[1:])
                    s[0] = np.prod(v.shape[:2])
                    return v.reshape(s)
                return v

        if self._legacy_chain_api:
            if self.chain is None:
                raise AttributeError(
                    f'Tried to get {name}, but there '
                    f'are no chains. Have you called '
                    f'`run_mcmc` yet?'
                )

            try:
                v = getattr(self, name)
            except AttributeError:
                v = getattr(self.chain, name)
        else:
            # Map legacy names onto newer ptemcee properties.
            attr = {'x': 'chain', 'logP': 'logprobability'}.get(name, name)
            v = getattr(self.sampler, attr, None)
            if v is None:
                raise AttributeError(
                    f'Tried to get {name}, but there '
                    f'are no chains. Have you called '
                    f'`run_mcmc` yet?'
                )

            # New ptemcee stores shape as (ntemps, nwalkers, nsteps, ...).
            if len(v.shape) == 4:
                v = np.transpose(v, (2, 0, 1, 3))
            else:
                v = np.transpose(v, (2, 0, 1))

        if len(v.shape) == 4:
            # shape(iterations, ntemps, nwalkers, ndim)
            v = v[:, temp, :, :]
        else:
            # shape(iterations, ntemps, nwalkers)
            v = v[:, temp, :]

        # Discard and thin
        v = v[discard + thin - 1: self.iteration: thin]

        if flat:
            s = list(v.shape[1:])
            s[0] = np.prod(v.shape[:2])
            return v.reshape(s)
        return v

    def get_chain(self, **kwargs):
        """
        Get the stored chain of MCMC samples.

        Parameters
        ----------
        kwargs
            flat : bool, optional, default=False
                Flatten the chain across the ensemble.

            thin : int, optional, default=1
                Take only every ``thin`` steps from the
                chain.

            discard : int, optional, default=0
                Discard the first ``discard`` steps in the
                chain as burn-in.

            temp : int, optional, default=0
                Take only the ``temp`` chain. Defaults to
                the temp at the ``0``th index which corresponds
                to the highest probability temperature.

        Returns
        -------
        np.ndarray with shape [..., nwalkers, ndim]
            The samples contained in ``ptemcee.Chain.x``.
        """
        return self.get_value('x', **kwargs)

    def get_log_prob(self, **kwargs):
        """
        Get the chain of log probabilities evaluated at
        the MCMC samples.

        Parameters
        ----------
        kwargs
            flat : bool, optional, default=False
                Flatten the chain across the ensemble.

            thin : int, optional, default=1
                Take only every ``thin`` steps from the
                chain.

            discard : int, optional, default=0
                Discard the first ``discard`` steps in the
                chain as burn-in.

            temp : int, optional, default=0
                Take only the ``temp`` log prob. Defaults to
                the temp at the ``0``th index which corresponds
                to the highest probability temperature.

        Returns
        -------
        np.ndarray with shape [..., nwalkers]
            The chain of log probabilities.
        """
        return self.get_value("logP", **kwargs)


class EnsembleSampler(emcee.EnsembleSampler):
    """
    Adapter for ``emcee.EnsembleSampler``.
    """
    name = 'ensemble'

    def __init__(self, nwalkers, ndim, log_prob_fn, args, **kw):
        super().__init__(nwalkers, ndim, log_prob_fn, args=args, **kw)

    def draw_positions(self, params, initial_positions=None, **kwargs) -> np.ndarray:
        """
        Draw the initial positions from the priors.

        Parameters
        ----------
        params : Parameters
            The MCMC parameters.

        kwargs :
            For compatability with ``PTSampler.draw_positions``.

        Returns
        -------
        np.ndarray of float with shape [nwalkers, ndim]
            The starting positions.
        """
        if initial_positions is not None:
            pos = np.asarray(initial_positions, dtype=float).copy()
            expected = (self.nwalkers, self.ndim)
            if pos.shape != expected or not np.isfinite(pos).all():
                raise ValueError(f'Initial positions must be finite with shape {expected}.')
            return pos

        pos = np.zeros((self.nwalkers, self.ndim))

        for i, p in enumerate(params.fitting):
            pos[:, i] = p.prior.draw(self.nwalkers)

        return pos


class MCMC:
    """
    Performs MCMC sampling.

    Parameters
    ----------
    model : MCMCModels
        The model wrapper.

    parameters : Parameters
        The model parameters.
    """
    def __init__(self, model, parameters):
        # Model
        self.models = model
        self.params = parameters
        self.observation = model.obs

        # Sampler
        self.sampler = None
        self.burn_chain = None

        self.start_burn_pos = None
        self.start_run_pos = None

    @property
    def ndim(self):
        """ The number of fitting dimensions. """
        return len(self.params.fitting)

    def get_best_params(self, as_dict=True, **kwargs):
        """
        Returns the sampled values from the chain with the
        highest likelihood.

        Parameters
        ----------
        as_dict : bool, optional, default=True
            Should the samples be returned as a dict? Where
            key = param name and value = param value.

        kwargs : dict
            Any kwargs accepted by ``Parameters.samples_to_dict``.

        Returns
        -------
        dict or np.ndarray
            The values from the highest likelihood chain.
        """
        params = utils.get_best_samples(self.sampler)

        if as_dict:
            return self.params.samples_to_dict(params, **kwargs)
        return params

    def set_sampler(self, sampler, nwalkers, pool, ntemps=None, **kwargs):
        """
        Sets the sampler. Duh.

        Parameters
        ----------
        sampler : str
            The sampler name. Must be ``ensemble`` or ``parallel_tempered``.

        nwalkers : int
            The number of walkers.

        pool : ``ProcessPoolExecutor`` or ``ThreadPoolExecutor`` or ``nullcontext``
            The pool to use for multithreading/processing.
            See ``get_pool_context()`` for details.

        ntemps : int, optional
            The number of temperatures for ``parallel_tempered``.

        kwargs
            Any kwargs accepted by the sampler.
        """
        if sampler == 'ensemble':
            self.sampler = EnsembleSampler(
                nwalkers, self.ndim, log_posterior_fn,
                args=(self.params, self.models), pool=pool, **kwargs # type: ignore
            )

        elif sampler == 'parallel_tempered':
            self.sampler = PTSampler(
                ntemps, nwalkers, self.ndim, log_likelihood_fn, log_prior_fn,
                log_l_args=(self.params, self.models), log_p_args=(self.params,),
                pool=pool, **kwargs
            )

    def start_positions(self, resume=False, initial_positions=None):
        """
        Determines the starting positions.

        Parameters
        ----------
        resume : bool, optional, default=False
            Use the end of a previous run to determine
            the starting positions?

        Returns
        -------
        np.ndarray or ``emcee.State``
            The starting positions.
        """
        if resume and isinstance(self.sampler, EnsembleSampler):
            # Use the backend to determine start positions
            return self.sampler.get_last_sample()

        # Use priors to determine start positions
        return self.sampler.draw_positions(
            params=self.params, models=self.models, initial_positions=initial_positions
        )

    def run(
        self, nwalkers, iterations, burn=0, sampler='ensemble',
        workers=None, ntemps=None, sampler_kw=None, run_kw=None,
        resume=False, checkpoint_path=None, checkpoint_interval=0,
        initial_positions=None
    ):
        """
        Runs the MCMC sampling routine.

        Parameters
        ----------
        nwalkers : int
            The number of walkers.

        iterations : int
            The number of iterations.

        burn : int, optional, default=0
            The number of iterations to burn. If ``burn>0``,
            stores the burn sampler to ``self.burn_sampler``
            before resetting it for the main run.

        sampler : str, optional, default='ensemble'
            Must be ``ensemble`` or ``parallel_tempered``.

        workers : int, optional, default=None
            The max number of workers to use.

        ntemps : int, optional, default=None
            The number of temperatures for ``PTSampler``.

        sampler_kw : dict, optional
            Any kwargs accepted by the sampler.

        run_kw : dict, optional
            Any kwargs accepted by ``run_mcmc``.

        resume : bool, optional, default=False
            Resume from a previous run?

        checkpoint_path : str or Path, optional, default=None
            Resume-state path for ``parallel_tempered`` runs.

        checkpoint_interval : int, optional, default=0
            Save resume-state every N production iterations for
            ``parallel_tempered``. Set ``0`` to disable periodic saves.
        """
        run_options = dict(run_kw or {})

        executor = os.environ.get('JETFIT_POOL_EXECUTOR', 'process').strip().lower()
        if executor not in ('process', 'thread'):
            executor = 'process'

        with get_pool_context(workers, executor=executor) as pool:
            self.set_sampler(
                sampler, nwalkers, pool, ntemps, **(sampler_kw or {})
            )

            is_pt = isinstance(self.sampler, PTSampler)
            checkpoint = (
                Path(checkpoint_path)
                if (is_pt and checkpoint_path is not None)
                else None
            )

            checkpoint_interval = int(checkpoint_interval or 0)
            if checkpoint_interval < 0:
                raise ValueError('checkpoint_interval must be >= 0.')

            resumed_chain = None
            resumed_log_prob = None
            completed_iterations = 0
            resumed_from_checkpoint = False
            target_iterations = int(iterations)
            burn_target_iterations = int(burn)
            burn_completed_offset = 0

            if is_pt and resume:
                if checkpoint is None:
                    raise ValueError(
                        'Resume for parallel_tempered requires a checkpoint_path.'
                    )
                if not checkpoint.exists():
                    raise FileNotFoundError(
                        f'Cannot resume parallel_tempered run; checkpoint not found: '
                        f'{checkpoint}'
                    )

                state = self.sampler.load_resume_state(checkpoint)
                phase = state.get('phase', 'production')
                if phase == 'burn':
                    self.start_burn_pos = state['last_pos']
                    burn_completed_offset = int(
                        state.get('burn_completed_iterations', 0)
                    )
                    burn = max(0, burn_target_iterations - burn_completed_offset)
                    resumed_from_checkpoint = False
                elif phase == 'production':
                    self.start_run_pos = state['last_pos']
                    resumed_chain = state['chain']
                    resumed_log_prob = state['lnprob']
                    completed_iterations = int(state['completed_iterations'])
                    resumed_from_checkpoint = True
                    burn = 0
                else:
                    raise ValueError(
                        f'Unsupported checkpoint phase {phase!r} in {checkpoint}'
                    )

            if not resumed_from_checkpoint:
                start_pos = (
                    self.start_burn_pos
                    if is_pt and resume and hasattr(self, 'start_burn_pos')
                    else self.start_positions(resume, initial_positions)
                )

                if burn < 1:
                    self.start_run_pos = start_pos

                else:
                    self.start_burn_pos = start_pos

                    if is_pt and checkpoint is not None and checkpoint_interval > 0:
                        current_pos = self.start_burn_pos
                        produced_burn = 0
                        while produced_burn < int(burn):
                            step = min(
                                checkpoint_interval,
                                int(burn) - produced_burn,
                            )
                            current_pos = self.sampler.run_mcmc(
                                current_pos, step, **run_options
                            )
                            produced_burn = int(self.sampler.iteration)
                            self.sampler.save_resume_state(
                                checkpoint,
                                completed_iterations=0,
                                target_iterations=target_iterations,
                                phase='burn',
                                burn_completed_iterations=(
                                    burn_completed_offset + produced_burn
                                ),
                                burn_target_iterations=burn_target_iterations,
                            )
                        self.start_run_pos = current_pos
                    else:
                        # Run burn in and save the last position
                        self.start_run_pos = (
                            self.sampler.run_mcmc(
                                self.start_burn_pos, burn, **run_options
                            )
                        )

                    # Save the chain if desired for diagnostics. Cannot
                    # save the entire sampler because deepcopy detaches
                    # the pool which prevents multiprocessing/threading
                    self.burn_chain = copy.deepcopy(self.sampler.get_chain())
                    self.sampler.reset()

            remaining_iterations = target_iterations - completed_iterations
            if remaining_iterations < 0:
                raise ValueError(
                    f'Resume checkpoint has {completed_iterations} iterations, '
                    f'but current run_length is only {target_iterations}.'
                )

            if remaining_iterations == 0:
                if (
                    is_pt
                    and resumed_chain is not None
                    and resumed_log_prob is not None
                ):
                    self.sampler.set_temp0_overrides(resumed_chain, resumed_log_prob)
                return

            if is_pt and checkpoint is not None and checkpoint_interval > 0:
                current_pos = self.start_run_pos
                produced_iterations = 0

                while produced_iterations < remaining_iterations:
                    step = min(
                        checkpoint_interval,
                        remaining_iterations - produced_iterations
                    )
                    current_pos = self.sampler.run_mcmc(
                        current_pos, step, **run_options
                    )
                    produced_iterations = int(self.sampler.iteration)

                    if (
                        resumed_chain is not None
                        and resumed_log_prob is not None
                    ):
                        combined_chain = np.concatenate(
                            (resumed_chain, self.sampler.get_chain()),
                            axis=0,
                        )
                        combined_log_prob = np.concatenate(
                            (resumed_log_prob, self.sampler.get_log_prob()),
                            axis=0,
                        )
                    else:
                        combined_chain = None
                        combined_log_prob = None

                    self.sampler.save_resume_state(
                        checkpoint,
                        completed_iterations=completed_iterations + produced_iterations,
                        target_iterations=target_iterations,
                        chain=combined_chain,
                        lnprob=combined_log_prob,
                    )
            else:
                # Run production
                self.sampler.run_mcmc(
                    self.start_run_pos, remaining_iterations, **run_options
                )

            if is_pt and resumed_chain is not None and resumed_log_prob is not None:
                combined_chain = np.concatenate(
                    (resumed_chain, self.sampler.get_chain()),
                    axis=0,
                )
                combined_log_prob = np.concatenate(
                    (resumed_log_prob, self.sampler.get_log_prob()),
                    axis=0,
                )
                self.sampler.set_temp0_overrides(combined_chain, combined_log_prob)

            if is_pt and checkpoint is not None:
                self.sampler.save_resume_state(
                    checkpoint,
                    completed_iterations=int(self.sampler.get_chain().shape[0]),
                    target_iterations=target_iterations,
                )


class MCMCModels:
    """
    Container for MCMC models used during fitting.

    Parameters
    ----------
    obs : Observation
        The observational data.

    afg_model :
        The afterglow model.

    afg_kw : dict, optional
        Any kwargs needed to instantiate the model.

    ext_model : optional
        The dust extinction model.

    ext_mw_pc : np.ndarray, optional
        The pre-computed Milky Way extinction values.

    ext_sf_pc : np.ndarray, optional
        The pre-computed source-frame extinction values.
    """
    def __init__(
        self, obs, afg_model,
        afg_kw=None, ext_model=None, ext_mw_pc=None, ext_sf_pc=None
    ):
        # Afterglow
        self.afg_model = afg_model
        self.afg_kw = afg_kw if afg_kw else {}

        # Extinction
        self.ext_model = ext_model
        self.ext_mw_pc = ext_mw_pc
        self.ext_sf_pc = ext_sf_pc

        # Observation
        self.obs = obs

    def model(self, params):
        """
        Models the observed GRB afterglow flux.

        Parameters
        ----------
        params : dict
            The dict returned from `Parameters.samples_to_dict`.

        Returns
        -------
        np.ndarray of float
            The modeled observed GRB afterglow flux.
        """
        # Model the GRB afterglow data
        try:
            modeled = self.model_afterglow(params)
        except Exception as e:
            if os.environ.get('JETFIT_DEBUG_MODEL_EXCEPTIONS', '0') == '1':
                print(e)
            return np.array([np.nan])

        if np.isnan(modeled.min()):
            return np.array([np.nan])

        # Correct for dust and host then return
        return self.model_extinction(modeled, params)

    def model_afterglow(self, params):
        """
        Models the unextinguished GRB afterglow flux.

        Parameters
        ----------
        params : dict
            The dict returned from `Parameters.samples_to_dict`.

        Returns
        -------
        np.ndarray of float
            The modeled GRB afterglow flux.
        """
        return self.afg_model(
            **params.get('model'), **self.afg_kw).model(self.obs)

    def model_extinction(self, modeled, params):
        """
        Corrects the afterglow flux, ``modeled``, for
        dust extinction and host galaxy contributions.

        Applies the corrections in the order:
            1. Source-frame dust extinction.
            2. Host galaxy contribution.
            3. Milky Way dust extinction.

        Parameters
        ----------
        modeled : np.array
            The modeled flux.

        params : dict
            The dict returned from `Parameters.samples_to_dict`.

        Returns
        -------
        np.ndarray of float
            The extinguished and host galaxy corrected flux.
        """
        pos = self.obs.extinguishable
        wn = self.obs.as_arrays.wave_numbers[pos]

        # Extinction params TEMP!
        z = params.get('model').get('z')
        ext = params.get('extinction')
        ebv_sf = ext.get('ebv_source_frame')
        ebv_mw = ext.get('ebv_milky_way')

        # Apply source-frame extinction
        if ext.get('av_source_frame') is not None:
            modeled[pos] *= trotter_source_attenuation((1 + z) * wn, ext)
        elif ebv_sf is not None:
            p = {'init': {'Rv': ext.get('rv_source_frame') or 3.1}, 'eval': {'Ebv': ebv_sf}}
            modeled[pos] *= self._model_extinction(p, (1 + z) * wn, self.ext_sf_pc)

        # Apply host galaxy correction
        if params.get('host') is not None and self.obs.hosts is not None:
            for name, corr in params.get('host').items():
                modeled[self.obs.hosts[name]] += corr

        # Apply Milky Way extinction
        if ebv_mw is not None:
            p = {'init': {'Rv': ext.get('rv_milky_way') or 3.1}, 'eval': {'Ebv': ebv_mw}}
            modeled[pos] *= self._model_extinction(p, wn, self.ext_mw_pc)

        # return corrected flux.
        return modeled

    def _model_extinction(self, p, wn, pc=None):
        """ Internal use only. """
        # Return the pre-computed extinction
        if pc is not None: return pc

        # Calculate the extinction and return
        return self.ext_model(
            **p.get('init')).extinguish(wn, **p.get('eval'))


def log_prior_fn(theta, params) -> float:
    """
    Evaluates the natural log of the priors.

    Parameters
    ----------
    theta : np.ndarray of float, with length of ``params.fitting``
        The sampled MCMC parameter values.

    params : Parameters
        MCMC parameter container.

    Returns
    -------
    float
        The log of the evaluated priors.
    """
    lp = 0

    for i, p in enumerate(params.fitting):
        if np.isinf(prior := p.prior.evaluate(theta[i])):
            return -np.inf

        if prior != 0:
            lp += np.log(prior)

    p_dict = params.samples_to_dict(theta)
    ext = p_dict.get('extinction')
    if ext is not None and 'c2' in ext:
        dust_prior = trotter_dust_prior.log_prior(ext)
        if not np.isfinite(dust_prior):
            return -np.inf
        lp += dust_prior

    return lp


def log_likelihood_fn(theta, params, models) -> float:
    """
    Calculates the natural log of the likelihood.

    Parameters
    ----------
    theta : np.ndarray of float, with length of ``params.fitting``
        The MCMC sampled values.

    params : Parameters
        The MCMC parameter container.

    models : MCMCModels
        The MCMC models container.

    Returns
    -------
    float or -np.inf
        The log of the likelihood if the parameters were valid.
        Else, -np.inf.
    """
    p = params.samples_to_dict(theta)
    m = p.get('model') or {}

    # Cheap physical guards to avoid expensive model calls for clearly
    # invalid proposals (important for long PT runs).
    eps_e = m.get('eps_e')
    eps_b = m.get('eps_b')
    if (
        eps_e is not None
        and eps_b is not None
        and np.isfinite(eps_e)
        and np.isfinite(eps_b)
        and (eps_e + eps_b) >= 1.0
    ):
        return -np.inf

    p_idx = m.get('p')
    if p_idx is not None and np.isfinite(p_idx) and p_idx < 2.0:
        return -np.inf

    theta_c = m.get('theta_c')
    if theta_c is not None and np.isfinite(theta_c) and theta_c <= 0.0:
        return -np.inf

    lf0 = m.get('lf0')
    if lf0 is not None and np.isfinite(lf0) and lf0 <= 1.0:
        return -np.inf
    gamma0_core_avg = m.get('Gamma_0_core_avg')
    if (
        gamma0_core_avg is not None
        and np.isfinite(gamma0_core_avg)
        and gamma0_core_avg <= 1.0
    ):
        return -np.inf

    # Model the observed afterglow
    modeled = models.model(p)

    # Reject any non-finite model evaluation before downstream transforms.
    if not np.all(np.isfinite(modeled)):
        if os.environ.get('JETFIT_DEBUG_NAN_MODELED', '0') == '1':
            print("Non-finite modeled flux encountered.")
        return -np.inf

    # Apply calibration offsets
    modeled = calibration_offsets(
        modeled, p.get('offsets'), models.obs.offsets
    )

    # Format the slop (if using)
    s = slop(p.get('slop'), models.obs)

    chi2 = chi_squared(modeled, models.obs, s)  # type: ignore
    if not np.isfinite(chi2):
        if os.environ.get('JETFIT_DEBUG_NAN_MODELED', '0') == '1':
            print("Non-finite chi-squared encountered.")
        return -np.inf

    # return log likelihood
    return -0.5 * chi2


def log_posterior_fn(theta, params, models) -> float:
    """
    Calculates the natural log of the posterior
    probability.

    The posterior probability is the probability of
    the parameters, ``theta``, given the evidence X
    denoted by p(theta | X).

    Parameters
    ----------
    theta : np.ndarray of float, with length of ``params.fitting``
        The MCMC sampled values.

    params : Parameters
        The MCMC parameter container.

    models : MCMCModels
        The MCMC models container.

    Returns
    -------
    float
        The natural log of the posterior.
    """
    if np.isfinite(lp := log_prior_fn(theta, params)):
        ll = log_likelihood_fn(theta, params, models)

        if np.isfinite(ll):
            return lp + ll

    return -np.inf


def calibration_offsets(modeled, offsets, pos) -> np.ndarray:
    """
    Applies calibration offsets to the modeled values.

    Parameters
    ----------
    modeled : np.ndarray of float
        The modeled values.

    offsets : dict
        Key value pairs of ``CalGroup`` and offset values [mag].

    pos : dict
        The calibration positions.

    Returns
    -------
    np.ndarray
        The modeled values with applied offsets.
    """
    if offsets is not None:
        for name, offset in offsets.items():
            modeled[pos[name]] *= 10.0 ** -(0.4 * offset)
    return modeled


def slop(s, obs) -> float | np.ndarray | None:
    """
    Formats for slop to the modeled data.

    Parameters
    ----------
    s : float or dict
        The slop value or grouped slop values.

    obs : Observation
        The observational data.

    Returns
    -------
    float or np.ndarray or None
        The slop value(s).
    """
    if isinstance(s, (int, float)):
        return s

    elif isinstance(s, dict):
        res = np.empty(obs.length)

        for name, val in s.items():
            res[obs.slops[name]] = val

        return res


def chi_squared(modeled, obs, slops=None) -> float:
    """
    Calculates the combined chi-squared between
    the modeled and observational data for both
    the flux and spectral indices.

    The flux chi-squared calculation uses a so-
    called chi-squared effective which utilizes
    a slop parameter. Spectral indices use the
    standard chi-squared formulation.

    Parameters
    ----------
    modeled : np.ndarray of float
        The modeled or predicted values.

    obs : Observation
        The observational data.

    slops : float or np.ndarray of float, optional
        The slop value(s).

    Returns
    -------
    float
        The combined chi-squared value.
    """

    # Handle flux and indices the same
    if slops is None:
        return utils.chi_squared(
            modeled,
            obs.as_arrays.values,
            obs.as_arrays.errors,
        )

    # Chi-squared for flux (uses slop)
    flux_mask = obs.flux_loc

    cs_flux = utils.chi_squared(
        modeled[flux_mask],
        obs.as_arrays.values[flux_mask],
        obs.as_arrays.errors[flux_mask],
        slops if isinstance(slops, float) else slops[flux_mask]
    )

    # Chi-squared for spectral indices (does not use slop)
    index_mask = obs.sindex_loc

    if not index_mask.any():
        return cs_flux

    cs_indices = utils.chi_squared(
        modeled[index_mask],
        obs.as_arrays.values[index_mask],
        obs.as_arrays.errors[index_mask],
    )

    # return combined chi-squared
    return cs_flux + cs_indices
