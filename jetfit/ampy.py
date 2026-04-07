from pathlib import Path

from dust_extinction.parameter_averages import CCM89

from jetfit.core.input import Observation
from jetfit.mcmc.mcmc import MCMC, MCMCModels
from jetfit.mcmc.parameters import Parameters
from jetfit.models.boosted import BoostedFireballModel
from jetfit.models.fireball import FireballModel, StratifiedFireballModel
from jetfit.models.jetsim import JetSimpy
from jetfit.models.vegasafterglow import VegasAfterglowModel
from jetfit.models.powerlawVegas import powerlawVegasModel
from jetfit.models.powerlawVegasDylanSpectrum import powerlawVegasDylanSpectrumModel
from jetfit.models.bubbleVegas import BubbleVegasModel
            

def model_factory(name: str):
    """
    Returns the class of the given model name.

    Parameters
    ----------
    name : str
        The afterglow model.
    """
    match name:
        case 'FireballModel':
            return FireballModel
        case 'StratifiedFireballModel':
            return StratifiedFireballModel
        case 'BoostedFireballModel':
            return BoostedFireballModel
        case 'JetSimpy':
            return JetSimpy
        case 'VegasAfterglowModel':
            return VegasAfterglowModel
        case 'powerlawVegasModel':
            return powerlawVegasModel
        case 'powerlawVegasDylanSpectrumModel':
            return powerlawVegasDylanSpectrumModel
        case 'BubbleVegasModel':
            return BubbleVegasModel
        case _:
            raise ValueError(
                f'Unknown model {name}.'
            )


class Ampy:
    """
    Afterglow Modeling in Python (AMPy).

    AMPy is a MCMC framework for fitting afterglow light curves.

    Parameters
    ----------
    obs : str or Path or Observation
        The observational data.

    params : str or Path or Parameters
        The afterglow model parameters.

    model_kw : dict, optional, default=None
        Any kwargs passed to the model constructor.
    """
    def __init__(self, obs, params, model_kw=None):

        if isinstance(obs, (str, Path)):
            obs = Observation.from_csv(obs)

        if isinstance(params, (str, Path)):
            params = Parameters.from_toml(params)

        # Pre-compute Milky Way extinction (temporary implementation)
        ext_mw_pc = None
        for p in params.fixed:
            if not params.has('rv_milky_way'):
                if p.name == 'ebv_milky_way':
                    ext_mw_pc = CCM89(Rv=3.1).extinguish(
                        obs.as_arrays.wave_numbers[obs.extinguishable],
                        Ebv=p.value
                    )

        # MCMC model wrapper
        model = model_factory(params.model)

        wrapper = MCMCModels(
            obs, model, (model_kw or {}), CCM89, ext_mw_pc=ext_mw_pc
        )

        self.mcmc = MCMC(wrapper, params)

    @property
    def obs(self):
        return self.mcmc.observation

    @property
    def afterglow_model(self):
        return self.mcmc.models.afg_model

    @property
    def extinction_model(self):
        return self.mcmc.models.ext_model

    def run_mcmc(
        self, nwalkers, iterations, burn=0, sampler='ensemble',
        workers=None, ntemps=None, sampler_kw=None, run_kw=None,
        resume=False, checkpoint_path=None, checkpoint_interval=0
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
            Any kwargs to pass to the sampler.

        run_kw : dict, optional
            Any kwargs to pass to the ``run_mcmc`` method.

        resume : bool, optional, default=False
            Resume from a previous run?

        checkpoint_path : str or Path, optional, default=None
            Checkpoint path used by ``parallel_tempered`` resume workflow.

        checkpoint_interval : int, optional, default=0
            Save checkpoint every N production iterations for
            ``parallel_tempered``. Set ``0`` to disable.
        """
        self.mcmc.run(
            nwalkers, iterations, burn, sampler,
            workers, ntemps, sampler_kw, run_kw,
            resume, checkpoint_path, checkpoint_interval
        )
        return self.mcmc

    def get_best_params(self, as_dict=True, **kwargs):
        """
        Returns the sampled values from the chain with the
        highest log probability.

        Parameters
        ----------
        as_dict : bool, optional, default=True
            Should the sample be returned as a dict or
            a numpy array?

        kwargs : dict
            cat : str, optional
                Limit the params to the ``cat`` categories.

            scale : str, optional, default='linear'
                The scale to return the parameters in.

        Returns
        -------
        dict or np.ndarray
            The values from the highest likelihood chain.
        """
        return self.mcmc.get_best_params(as_dict, **kwargs)
