import argparse
import json
import os
from pathlib import Path

import emcee

from jetfit.ampy import Ampy
from jetfit.core import utils
from scripts.plot import diagnose
from scripts.plot import visualize
from scripts.plot import histogram


def parse_args():
    """ Optional command line arguments. """
    parser = argparse.ArgumentParser(description="AMPy Parameters")
    parser.add_argument('--event',   help='Event directory name.')
    parser.add_argument('--mcmc',    help='Path to the MCMC TOML file.')
    parser.add_argument('--model',   help='Path to the model TOML file.')
    parser.add_argument('--obs',     help='Path to the input observation file.')
    parser.add_argument('--results', help='Path the the results directory.')
    parser.add_argument('--resume',  help='Continue from previous run?')
    return parser.parse_args()


def log(ampy, out_dir):
    """
    Write the best parameters and sampler metadata
    to a JSON file.

    Parameters
    ----------
    ampy : Ampy
        The Ampy object.

    out_dir : str or Path
        The path to the result's directory.
    """
    nmap = -2 * ampy.mcmc.sampler.get_log_prob(flat=True).max()

    out_params = ampy.get_best_params()
    
    # Compute physical dust parameters if Trotter model is active
    if 'extinction' in out_params and 'c2' in out_params['extinction']:
        from jetfit.mcmc.mcmc import trotter_dust_prior
        ext = out_params['extinction']
        c1, rv, bh, x0, gamma = trotter_dust_prior.get_physical_dust_params(ext['c2'], ext)
        ext['c1_physical'] = float(c1)
        ext['rv_physical'] = float(rv)
        ext['bh_physical'] = float(bh)
        ext['x0_physical'] = float(x0)
        ext['gamma_physical'] = float(gamma)

    out_params['nmap'] = nmap
    out_params['mcmc'] = {
        'sampler': ampy.mcmc.sampler.name,
        'prod_len': int(ampy.mcmc.sampler.iteration),
        'burn_len': int(ampy.mcmc.sampler.iteration),
        'nwalkers': ampy.mcmc.sampler.nwalkers,
        'model': ampy.mcmc.params.model,
    }

    with open(out_dir / 'best_fit.json', "w") as f:
        json.dump(out_params, f, indent=4)  # type: ignore


def plot_results(ampy, results_dir, event):
    """
    Plot the results of the MCMC run.

    This includes trace plots, corner plot, characteristic
    frequencies, light curve, jet-corrected parameters,
    spectral indices, and density profiles.

    Parameters
    ----------
    ampy : Ampy
        The completed Ampy object.

    results_dir : Path
        The path to the result's directory.

    event : str
        The event name.
    """
    params = ampy.mcmc.params

    # Plot the lines!
    visualize.plot_frequencies_ampy(ampy, out_dir=results_dir)
    visualize.plot_light_curve_ampy(ampy, title=f'{event} LC', out_dir=results_dir)
    visualize.plot_density_profile_ampy(ampy, out_dir=results_dir)

    # Plot the histograms!
    histogram.plot_spectral_indices_ampy(ampy, out_dir=results_dir)
    histogram.plot_jet_correction_ampy(ampy, out_dir=results_dir)

    # Plot the MCMC diagnostics!
    diagnose.plot_corner(ampy.mcmc.sampler.get_chain(flat=True), params.fitting, out_dir=results_dir)

    if ampy.mcmc.burn_chain is not None:
        diagnose.plot_trace(params, out_dir=results_dir, chain=ampy.mcmc.burn_chain)

    diagnose.plot_trace(params, out_dir=results_dir, sampler=ampy.mcmc.sampler)


def main(obs_path, params_path, mcmc_path, results_dir, event, resume=False):
    """
    Run MCMC using AMPy.

    Parameters
    ----------
    obs_path : Path
        The path to the observation CSV file.

    params_path : Path
        The path to the model parameters TOML file.

    mcmc_path : Path
        The path to the MCMC TOML file.

    results_dir : Path
        The path to the result's directory.

    event : str
        The name of the event to model.

    resume : bool, optional, default=False
        Resume from a previous run? Only supported for
        ``EnsembleSampler`` since ``PTSampler`` does not
        use a ``backend``.

    Returns
    -------
    Ampy
        The finished Ampy object.
    """
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    # Create the AMPy object
    # print(f"DEBUG: Creating Ampy object...")
    # print(f"  obs_path: {obs_path}")
    # print(f"  params_path: {params_path}")
    ampy = Ampy(obs_path, params_path)
    # print(f"DEBUG: Ampy object created successfully!")

    # Prepare the MCMC run
    # print(f"DEBUG: Preparing MCMC run...")
    mcmc_params = utils.MCMCSettingsReader(mcmc_path)
    sampler_name = mcmc_params.data['sampler']['name']
    # print(f"DEBUG: Sampler: {sampler_name}")

    sampler_kw, run_kw = {}, {}

    # Output progress bar and save samples in real-time
    if sampler_name == 'ensemble':
        run_kw['progress'] = True

        backend = emcee.backends.HDFBackend(str(results_dir / f'{event}_chain.h5'))
        if not resume:
            backend.reset(mcmc_params.num_walkers, len(ampy.mcmc.params.fitting))
        sampler_kw['backend'] = backend

    # Run the MCMC routine
    # print(f"DEBUG: Starting MCMC run...")
    # print(f"  nwalkers: {mcmc_params.num_walkers}")
    # print(f"  iterations: {mcmc_params.run_length}")
    # print(f"  burn: {mcmc_params.burn_length}")
    try:
        ampy.run_mcmc(
            nwalkers=mcmc_params.num_walkers,
            iterations=mcmc_params.run_length,
            burn=mcmc_params.burn_length,
            sampler=sampler_name,
            workers=mcmc_params.workers,
            ntemps=mcmc_params.ntemps,
            run_kw=run_kw,
            sampler_kw=sampler_kw,
        )
        print(f"DEBUG: MCMC run completed!")
    except Exception as e:
        print(f"DEBUG: MCMC run FAILED with error:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise

    # ptemcee does not support backend like emcee
    if sampler_name == 'parallel_tempered':
        ampy.mcmc.sampler.save(results_dir / 'chain.npz')

    # Log the best fitr results and some metadata
    log(ampy, results_dir)

    # Plot some things
    plot_results(ampy, results_dir, event)
    print(f"DEBUG: Results plotted!")
    print(results_dir)

    return ampy


if __name__ == "__main__":
    args = parse_args()

    sub_dir = 'grbs'

    # Specify the event to run
    if args.event is None:
        event_name = '221009A'  # Default event
    else:
        event_name = args.event

    # Run AMPy
    print( utils.get_event_path(sub_dir, event_name) / 'parameters.toml')
    main(
        **{
            'event':
                event_name,

            'mcmc_path':
                Path(args.mcmc)
                if args.mcmc is not None
                else utils.get_mcmc_settings_path(),

            'params_path':
                Path(args.model)
                if args.model is not None
                else utils.get_event_path(sub_dir, event_name) / 'parameters.toml',
                

            'obs_path':
                Path(args.obs)
                if args.obs is not None
                else utils.get_input_csv_path(sub_dir, event_name),

            'results_dir':
                Path(args.results)
                if args.results is not None
                else utils.get_results_path() / event_name,

            'resume':
                args.resume
                if args.resume is not None
                else False,
        }
    )
