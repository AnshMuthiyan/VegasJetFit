import argparse
import json
import os
import shutil
import sys
import multiprocessing as mp
from pathlib import Path

import numpy as np

# Use a non-interactive matplotlib backend for batch runs.
os.environ.setdefault('MPLBACKEND', 'Agg')

import emcee

from jetfit.ampy import Ampy
from jetfit.core import utils


def parse_args():
    """ Optional command line arguments. """
    parser = argparse.ArgumentParser(description="AMPy Parameters")
    parser.add_argument('--event',   help='Event directory name.')
    parser.add_argument('--mcmc',    help='Path to the MCMC TOML file.')
    parser.add_argument('--model',   help='Path to the model TOML file.')
    parser.add_argument('--obs',     help='Path to the input observation file.')
    parser.add_argument('--results', help='Path the the results directory.')
    parser.add_argument('--resume',  action='store_true', help='Continue from previous run?')
    parser.add_argument('--initial-positions', help='NPZ with positions and parameter_names.')
    parser.add_argument(
        '--skip-plots',
        action='store_true',
        help='Skip all plotting outputs (useful for short preflight checks).',
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Override worker count from mcmc settings (1 disables multiprocessing).',
    )
    parser.add_argument(
        '--start-method',
        default=os.environ.get('JETFIT_MP_START_METHOD', 'auto'),
        choices=('auto', 'fork', 'spawn', 'forkserver'),
        help='Multiprocessing start method. Default comes from JETFIT_MP_START_METHOD or auto.',
    )
    return parser.parse_args()


def _resolve_start_method(requested):
    """Resolve start method with macOS-friendly defaults."""
    methods = mp.get_all_start_methods()

    if requested and requested != 'auto':
        if requested not in methods:
            raise ValueError(
                f'Unsupported multiprocessing start method: {requested}. '
                f'Available: {methods}'
            )
        return requested

    if sys.platform == 'darwin':
        if 'fork' in methods:
            return 'fork'
        if 'spawn' in methods:
            return 'spawn'

    return methods[0]


def configure_multiprocessing(start_method):
    """Configure multiprocessing start method once at process startup."""
    method = _resolve_start_method(start_method)
    current = mp.get_start_method(allow_none=True)

    if current is None:
        mp.set_start_method(method)
        current = method
    elif current != method:
        print(
            f"WARNING: multiprocessing start method already set to '{current}', "
            f"requested '{method}'. Using '{current}'."
        )

    print(f"Multiprocessing start method: {current}")
    return current


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
    # Import plotting modules lazily so no plotting/network deps are loaded
    # during compute-only runs (e.g., preflight with --skip-plots).
    from scripts.plot import diagnose
    from scripts.plot import visualize
    from scripts.plot import histogram
    from scripts.generate_postfit_products import derive_jet_energy_posterior

    params = ampy.mcmc.params

    # Plot the lines!
    visualize.plot_frequencies_ampy(ampy, out_dir=results_dir)
    visualize.plot_spectrum_timeseries_ampy(
        ampy,
        out_dir=results_dir,
        output_path=results_dir / 'spectrum_timeseries.pdf',
    )
    # frequencies.pdf is the standard frequency diagnostic for the final
    # Share_Folder products. Do not alias or regenerate spectral_plot.* here.
    visualize.plot_light_curve_ampy(ampy, title=f'GRB {event}', out_dir=results_dir)
    visualize.plot_density_profile_ampy(ampy, out_dir=results_dir)

    # Plot the histograms!
    histogram.plot_spectral_indices_ampy(ampy, out_dir=results_dir)
    histogram.plot_jet_correction_ampy(ampy, out_dir=results_dir)

    # Plot the MCMC diagnostics!
    flat_chain = ampy.mcmc.sampler.get_chain(flat=True)
    derived, _ = derive_jet_energy_posterior(flat_chain, params, str(params.model))
    diagnose.plot_corner(
        flat_chain,
        params.fitting,
        derived=derived,
        out_dir=results_dir,
    )

    if ampy.mcmc.burn_chain is not None:
        diagnose.plot_trace(params, out_dir=results_dir, chain=ampy.mcmc.burn_chain)

    diagnose.plot_trace(params, out_dir=results_dir, sampler=ampy.mcmc.sampler)


def main(
    obs_path, params_path, mcmc_path, results_dir, event,
    resume=False, workers_override=None, skip_plots=False,
    initial_positions_path=None
):
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
        Resume from a previous run.

    Returns
    -------
    Ampy
        The finished Ampy object.
    """
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    # Stamp all generated figures with event + run folder for easy identification.
    run_folder = Path(results_dir).name
    os.environ['JETFIT_PLOT_EVENT_TITLE'] = f'GRB {event}'
    os.environ['JETFIT_PLOT_RUN_LABEL'] = f'GRB {event} | {run_folder}'
    print(f"DEBUG: Plot label: {os.environ['JETFIT_PLOT_RUN_LABEL']}")

    print(f"DEBUG: Multiprocessing method: {mp.get_start_method(allow_none=True)}")
    print(f"DEBUG: Number of CPUs: {mp.cpu_count()}")

    # Create the AMPy object
    print(f"DEBUG: Creating Ampy object...")
    print(f"  obs_path: {obs_path}")
    print(f"  params_path: {params_path}")
    ampy = Ampy(obs_path, params_path)
    print(f"DEBUG: Ampy object created successfully!")

    initial_positions = None
    if initial_positions_path is not None:
        seed_path = Path(initial_positions_path)
        with np.load(seed_path, allow_pickle=False) as data:
            initial_positions = np.asarray(data['positions'], dtype=float)
            seed_names = [str(name) for name in data['parameter_names']]
        fitting_names = [param.name for param in ampy.mcmc.params.fitting]
        if seed_names != fitting_names:
            raise ValueError(f'Initial-position parameters do not match: {seed_names} != {fitting_names}')
        shutil.copy2(seed_path, results_dir / 'initial_positions.npz')
        print(f"DEBUG: Using posterior-informed initial positions: {seed_path}")

    # Prepare the MCMC run
    print(f"DEBUG: Preparing MCMC run...")
    mcmc_params = utils.MCMCSettingsReader(mcmc_path)
    sampler_name = mcmc_params.data['sampler']['name']
    print(f"DEBUG: Sampler: {sampler_name}")
    workers = (
        mcmc_params.workers
        if workers_override is None
        else max(1, int(workers_override))
    )

    sampler_kw, run_kw = {}, {}
    checkpoint_path = None
    checkpoint_interval = int(getattr(mcmc_params, 'checkpoint_interval', 0) or 0)

    # Output progress bar and save samples in real-time
    if sampler_name == 'ensemble':
        run_kw['progress'] = True

        backend = emcee.backends.HDFBackend(str(results_dir / f'{event}_chain.h5'))
        if not resume:
            backend.reset(mcmc_params.num_walkers, len(ampy.mcmc.params.fitting))
        sampler_kw['backend'] = backend
    elif sampler_name == 'parallel_tempered':
        checkpoint_path = results_dir / 'pt_resume_state.npz'

    # Run the MCMC routine
    print(f"DEBUG: Starting MCMC run...")
    print(f"  nwalkers: {mcmc_params.num_walkers}")
    print(f"  iterations: {mcmc_params.run_length}")
    print(f"  burn: {mcmc_params.burn_length}")
    print(f"  workers: {workers}")
    if checkpoint_path is not None:
        print(f"  checkpoint: {checkpoint_path}")
        print(f"  checkpoint interval: {checkpoint_interval}")
    
    try:
        ampy.run_mcmc(
            nwalkers=mcmc_params.num_walkers,
            iterations=mcmc_params.run_length,
            burn=mcmc_params.burn_length,
            sampler=sampler_name,
            workers=workers,
            ntemps=mcmc_params.ntemps,
            run_kw=run_kw,
            sampler_kw=sampler_kw,
            resume=resume,
            checkpoint_path=checkpoint_path,
            checkpoint_interval=checkpoint_interval,
            initial_positions=initial_positions,
        )
        print(f"DEBUG: MCMC run completed successfully!")
    except Exception as e:
        print(f"DEBUG: MCMC run FAILED with error:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise

    # ptemcee does not support backend like emcee
    if sampler_name == 'parallel_tempered':
        ampy.mcmc.sampler.save(results_dir / 'chain.npz')

    # Log the best fit results and some metadata
    log(ampy, results_dir)

    # Plot some things
    if not skip_plots:
        plot_results(ampy, results_dir, event)

    return ampy


if __name__ == "__main__":
    args = parse_args()
    configure_multiprocessing(args.start_method)

    sub_dir = 'grbs'

    # Specify the event to run
    if args.event is None:
        event_name = '080413B'
    else:
        event_name = args.event

    results_path = (
        Path(args.results)
        if args.results is not None
        else utils.get_results_path() / event_name
    )

    # Run AMPy
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
                results_path,

            'resume':
                bool(args.resume),

            'workers_override':
                args.workers,

            'skip_plots':
                bool(args.skip_plots),

            'initial_positions_path':
                Path(args.initial_positions) if args.initial_positions is not None else None,
        }
    )
    print(results_path)
