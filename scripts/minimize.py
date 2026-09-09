import argparse
import csv
import inspect
import json
import multiprocessing as mp
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from scipy import optimize

# Allow direct script execution from any cwd without requiring PYTHONPATH.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jetfit.ampy import Ampy
from jetfit.core import utils
from jetfit.mcmc.mcmc import log_posterior_fn
from jetfit.mcmc.priors import GaussianPrior

SUPPORTED_SCIPY_METHODS = ("L-BFGS-B", "Powell", "Nelder-Mead")
DEFAULT_SCIPY_METHOD = "Powell"
DEFAULT_FALLBACK_SCIPY_METHOD = "Nelder-Mead"


def safe_log_posterior_fn(theta, params, models):
    """Return log posterior with finite fallback for robust minimization."""
    lp = log_posterior_fn(theta, params, models)
    return lp if np.isfinite(lp) else -1e10


def normalize_scipy_method(method: str | None, *, allow_none: bool = False) -> str | None:
    if method is None:
        return None if allow_none else DEFAULT_SCIPY_METHOD

    canonical = str(method).strip()
    key = canonical.lower().replace("_", "-").replace(" ", "-")
    if allow_none and key in {"", "none", "off", "null"}:
        return None

    for candidate in SUPPORTED_SCIPY_METHODS:
        candidate_key = candidate.lower().replace("_", "-").replace(" ", "-")
        if key == candidate_key:
            return candidate

    allowed = ", ".join(SUPPORTED_SCIPY_METHODS)
    if allow_none:
        allowed = f"{allowed}, none"
    raise ValueError(f"Unknown scipy method '{method}'. Allowed values: {allowed}.")


def run_backend_minimizer(
    x0,
    func_args=(),
    bounds=(),
    minimizer="minimize",
    scipy_method: str = DEFAULT_SCIPY_METHOD,
):
    """Run one MAP refinement attempt from initial point ``x0``."""
    nmap = lambda *lp_args: -safe_log_posterior_fn(*lp_args)

    if minimizer == "minimize":
        return optimize.minimize(
            nmap,
            x0,
            args=func_args,
            bounds=bounds,
            method=scipy_method,
        )

    if minimizer == "basinhopping":
        return optimize.basinhopping(
            nmap,
            x0,
            minimizer_kwargs={"method": scipy_method, "args": func_args, "bounds": bounds},
        )

    raise ValueError(f"Unknown minimizer '{minimizer}'.")


def plot_spectrum(ampy, params, out_dir, t_days=1.0):
    """
    Plot the best-fitting spectrum from the FireballModel at a fixed observer time.

    Parameters
    ----------
    ampy : Ampy
        The Ampy object (used for observed data overlay).

    params : dict
        The minimized parameters dict (output of samples_to_dict).

    out_dir : Path
        The output directory.

    t_days : float, optional, default=1.0
        Observer time [days] at which to evaluate the spectrum.
    """
    try:
        plt.style.use(['science', 'no-latex'])
    except OSError:
        pass

    # Filter model params to only those accepted by FireballModel
    valid_keys = set(inspect.signature(FireballModel.__init__).parameters) - {'self'}
    model_params = {k: v for k, v in params['model'].items() if k in valid_keys}
    model = FireballModel(**model_params)

    # Broad frequency grid: radio to hard X-ray
    nu = np.logspace(9, 19, 200)
    flux = model.spectral_flux(t_days, nu)  # mJy

    # Break frequencies from analytic spectrum
    spec = model.spectrum(t_days)
    break_freqs = {
        r'$\nu_a$': (float(np.atleast_1d(spec['nu_a'])[0]), 'C0'),
        r'$\nu_m$': (float(np.atleast_1d(spec['nu_m'])[0]), 'C1'),
        r'$\nu_c$': (float(np.atleast_1d(spec['nu_c'])[0]), 'C2'),
    }

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.loglog(nu, np.atleast_1d(flux).ravel(), color='black', linewidth=1.0,
              label=f't = {t_days} d')

    for label, (nu_break, color) in break_freqs.items():
        if np.isfinite(nu_break) and nu_break > 0:
            ax.axvline(nu_break, ls='--', color=color, linewidth=1.0, label=label)

    # Overlay observed data near t_days (within a factor of 2)
    obs = ampy.obs.as_arrays
    fmask = obs.flux_loc
    t_near = (obs.times[fmask] >= 0.5 * t_days) & (obs.times[fmask] <= 2.0 * t_days)
    if t_near.any():
        nu_obs = obs.frequencies[fmask][t_near]
        f_obs  = obs.values[fmask][t_near]
        e_obs  = obs.errors[fmask][t_near]
        bands  = obs.bands[fmask][t_near]
        for band in np.unique(bands):
            m = bands == band
            ax.errorbar(nu_obs[m], f_obs[m], yerr=e_obs[m],
                        fmt='.', markersize=4, elinewidth=0.5, label=band)

    ax.set_xlim(nu[0], nu[-1])
    ax.set_xlabel('Frequency [Hz]')
    ax.set_ylabel('Flux Density [mJy]')
    ax.set_title(f'Spectrum at t = {t_days} days')
    ax.grid(alpha=0.3)
    ax.legend(loc='best')

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    fig.savefig(Path(out_dir) / 'spectrum.pdf', bbox_inches='tight')
    plt.close(fig)


def result_hits_bounds(
    x: np.ndarray,
    bounds: np.ndarray,
    *,
    atol: float = 1e-6,
    rtol: float = 1e-4,
) -> bool:
    if bounds is None or len(bounds) == 0:
        return False

    x = np.asarray(x, dtype=float)
    lower = np.asarray(bounds[:, 0], dtype=float)
    upper = np.asarray(bounds[:, 1], dtype=float)

    return bool(
        np.any(np.isclose(x, lower, atol=atol, rtol=rtol))
        or np.any(np.isclose(x, upper, atol=atol, rtol=rtol))
    )


def summarize_attempt(
    result: optimize.OptimizeResult,
    *,
    func_args,
    bounds: np.ndarray,
    minimizer_name: str,
    scipy_method: str,
    retry_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "optimizer_backend": minimizer_name,
        "scipy_method": scipy_method,
        "success": bool(result.success),
        "message": str(result.message),
        "nmap": -2.0 * float(log_posterior_fn(result.x, *func_args)),
        "hit_bounds": result_hits_bounds(result.x, bounds),
        "retry_reason": retry_reason,
    }


def retry_reason_for_attempt(
    attempt: dict[str, Any],
    *,
    retry_on_failure: bool,
    retry_on_edge: bool,
) -> str | None:
    reasons: list[str] = []
    if retry_on_failure and not bool(attempt["success"]):
        reasons.append("optimizer returned success=false")
    if retry_on_edge and bool(attempt["hit_bounds"]):
        reasons.append("solution landed on a prior boundary")
    if reasons:
        return "; ".join(reasons)
    return None


def select_attempt_index(attempts: list[tuple[optimize.OptimizeResult, dict[str, Any]]]) -> int:
    """
    Pick the attempt with the best objective value (lowest nmap), regardless
    of optimizer success flags.

    Some SciPy backends return success=False even when they reach a better MAP
    point than a fallback method. We preserve the numerically best objective
    and carry success/message metadata so callers can judge optimizer health.
    """
    return min(range(len(attempts)), key=lambda idx: float(attempts[idx][1]["nmap"]))


def run_minimizer(
    x0,
    func_args=(),
    bounds=(),
    minimizer="minimize",
    scipy_method: str = DEFAULT_SCIPY_METHOD,
    fallback_scipy_method: str | None = DEFAULT_FALLBACK_SCIPY_METHOD,
    retry_on_failure: bool = True,
    retry_on_edge: bool = True,
):
    """Run MAP refinement from initial point ``x0`` with optional method fallback."""
    primary_method = normalize_scipy_method(scipy_method)
    fallback_method = normalize_scipy_method(fallback_scipy_method, allow_none=True)

    attempts: list[tuple[optimize.OptimizeResult, dict[str, Any]]] = []
    primary_result = run_backend_minimizer(
        x0=x0,
        func_args=func_args,
        bounds=bounds,
        minimizer=minimizer,
        scipy_method=primary_method,
    )
    primary_summary = summarize_attempt(
        primary_result,
        func_args=func_args,
        bounds=np.asarray(bounds, dtype=float),
        minimizer_name=minimizer,
        scipy_method=primary_method,
    )
    attempts.append((primary_result, primary_summary))

    retry_reason = retry_reason_for_attempt(
        primary_summary,
        retry_on_failure=retry_on_failure,
        retry_on_edge=retry_on_edge,
    )
    fallback_attempted = False
    if retry_reason and fallback_method and fallback_method != primary_method:
        fallback_attempted = True
        fallback_result = run_backend_minimizer(
            x0=x0,
            func_args=func_args,
            bounds=bounds,
            minimizer=minimizer,
            scipy_method=fallback_method,
        )
        fallback_summary = summarize_attempt(
            fallback_result,
            func_args=func_args,
            bounds=np.asarray(bounds, dtype=float),
            minimizer_name=minimizer,
            scipy_method=fallback_method,
            retry_reason=retry_reason,
        )
        attempts.append((fallback_result, fallback_summary))

    selected_index = select_attempt_index(attempts)
    for idx, (_, summary) in enumerate(attempts):
        summary["selected"] = idx == selected_index

    selected_result, selected_summary = attempts[selected_index]
    metadata = {
        "optimizer_backend": minimizer,
        "scipy_method": selected_summary["scipy_method"],
        "primary_scipy_method": primary_method,
        "fallback_scipy_method": fallback_method,
        "fallback_attempted": fallback_attempted,
        "retry_reason": retry_reason,
        "attempts": [summary for _, summary in attempts],
    }
    return selected_result, metadata


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)


def best_result(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Prefer successful minimizations; fall back to the lowest nMAP otherwise."""
    successful = [row for row in results if bool(row.get("success"))]
    pool = successful if successful else results
    return min(pool, key=lambda row: float(row["nmap"]))


def flatten_best_fit(best_fit: dict[str, Any]) -> dict[str, float]:
    """Flatten sectioned best-fit JSON into a single name->value map."""
    flat: dict[str, float] = {}

    for section in ("model", "extinction", "host", "offsets", "slop"):
        values = best_fit.get(section, {})
        if isinstance(values, dict):
            for key, val in values.items():
                if isinstance(val, (int, float)):
                    flat[key] = float(val)

    for key, val in best_fit.items():
        if isinstance(val, (int, float)):
            flat[key] = float(val)

    return flat


def event_from_results_dir(results_dir: Path) -> str | None:
    parts = results_dir.name.split("_")
    if not parts:
        return None
    event = parts[0].strip()
    return event or None


def event_csv_candidates(event_dir: Path) -> list[Path]:
    return sorted(path for path in event_dir.glob("*.csv") if path.is_file())


def guess_curated_obs_path(project_root: Path, event: str) -> Path | None:
    event_dir = project_root / "jetfit" / "resources" / "grbs" / event
    if not event_dir.exists():
        return None

    for name in (f"{event}clean.csv", f"{event}.csv"):
        candidate = event_dir / name
        if candidate.exists():
            return candidate

    candidates = event_csv_candidates(event_dir)
    return candidates[0] if candidates else None


def guess_full_obs_path(project_root: Path, event: str) -> Path | None:
    event_dir = project_root / "jetfit" / "resources" / "grbs" / event
    if not event_dir.exists():
        return None

    preferred: list[Path] = []
    explicit_all = event_dir / f"{event}_all_data.csv"
    explicit_plain = event_dir / f"{event}.csv"
    explicit_clean = event_dir / f"{event}clean.csv"

    preferred.append(explicit_all)
    preferred.extend(
        path
        for path in event_csv_candidates(event_dir)
        if "full" in path.stem.lower() and path not in {explicit_all, explicit_clean}
    )
    preferred.append(explicit_plain)
    preferred.append(explicit_clean)

    for candidate in preferred:
        if candidate.exists():
            return candidate

    candidates = event_csv_candidates(event_dir)
    return candidates[0] if candidates else None


def model_hint(best_fit: dict[str, Any], results_dir: Path) -> str:
    mcmc = best_fit.get("mcmc", {})
    if isinstance(mcmc, dict):
        model_name = mcmc.get("model")
        if isinstance(model_name, str) and model_name:
            return model_name

    lower = results_dir.name.lower()
    if "empirical_bubble" in lower:
        return "EmpiricalBubbleVegasDylanSpectrumModel"
    if "bubble" in lower:
        return "BubbleVegasDylanSpectrumModel"
    if "smoothbroken" in lower or "sbpl" in lower:
        return "StratifiedFireballModel"
    return "powerlawVegasDylanSpectrumModel"


def guess_params_path(project_root: Path, event: str, model_name: str) -> tuple[Path | None, list[Path]]:
    logs = project_root / "logs"
    ansh = project_root / "Ansh_Run"
    grb_params = project_root / "jetfit" / "resources" / "grbs" / event / "parameters.toml"

    tried: list[Path] = []
    candidates: list[Path] = []

    if model_name in {
        "BubbleVegasModel",
        "BubbleVegasDylanSpectrumModel",
        "EmpiricalBubbleVegasModel",
        "EmpiricalBubbleVegasDylanSpectrumModel",
    }:
        candidates.extend(
            [
                logs / f"{event}.parameters_empirical_bubble_theta1.0.synced.toml",
                logs / f"{event}.parameters_bubble_theta1.0.synced.toml",
                logs / f"{event}.parameters_bubble.synced.toml",
                ansh / "parameters_bubble.toml",
            ]
        )
    elif model_name == "StratifiedFireballModel":
        candidates.extend(
            [
                logs / f"{event}.parameters_sbpl_like.toml",
                grb_params,
            ]
        )
    else:
        candidates.extend(
            [
                logs / f"{event}.parameters_tophat_theta1.0.toml",
                logs / f"{event}.parameters_powerlaw.toml",
                ansh / "parameters_powerlaw.toml",
                grb_params,
            ]
        )

    for candidate in candidates:
        tried.append(candidate)
        if candidate.exists():
            return candidate, tried

    return None, tried


def resolve_obs_and_params(args, project_root: Path, results_dir: Path, best_fit: dict[str, Any]) -> tuple[Path, Path]:
    if args.obs:
        obs_path = Path(args.obs).expanduser().resolve()
    else:
        event = event_from_results_dir(results_dir)
        inferred_obs = guess_full_obs_path(project_root, event) if event else None
        if inferred_obs is not None:
            obs_path = inferred_obs
        else:
            results_obs = results_dir / "obs.csv"
            if results_obs.exists():
                obs_path = results_obs
            else:
                if event is None:
                    raise ValueError("Could not infer event name from results directory. Please pass --obs.")
                inferred_obs = guess_curated_obs_path(project_root, event)
                if inferred_obs is None:
                    raise FileNotFoundError(f"Could not infer obs CSV for event '{event}'. Please pass --obs.")
                obs_path = inferred_obs

    if args.params:
        params_path = Path(args.params).expanduser().resolve()
    else:
        results_model = results_dir / "model.toml"
        if results_model.exists():
            params_path = results_model
        else:
            event = event_from_results_dir(results_dir)
            if event is None:
                raise ValueError("Could not infer event name from results directory. Please pass --params.")
            hint = model_hint(best_fit, results_dir)
            inferred_params, tried = guess_params_path(project_root, event, hint)
            if inferred_params is None:
                tried_text = "\n".join(str(path) for path in tried)
                raise FileNotFoundError(
                    "Could not infer model TOML for minimization. Tried:\n"
                    f"{tried_text}\nPlease pass --params explicitly."
                )
            params_path = inferred_params

    if not obs_path.exists():
        raise FileNotFoundError(f"Observation CSV not found: {obs_path}")
    if not params_path.exists():
        raise FileNotFoundError(f"Params TOML not found: {params_path}")

    return obs_path, params_path


def chain_parameter_dim(chain_path: Path) -> int:
    with np.load(chain_path) as data:
        if "chain" not in data:
            raise KeyError(f"{chain_path} must contain 'chain'.")
        chain = np.asarray(data["chain"])

    if chain.ndim == 4:
        chain = chain[:, 0, :, :]
    if chain.ndim != 3:
        raise ValueError(f"Unexpected chain shape {chain.shape}; expected [steps, walkers, ndim].")

    return int(chain.shape[-1])


def candidate_param_paths_for_dim_recovery(
    project_root: Path,
    results_dir: Path,
    current_params_path: Path,
) -> list[Path]:
    candidates: list[Path] = []

    # Highest-priority source: exact run-sidecar model copied at launch time.
    results_model = results_dir / "model.toml"
    if results_model.exists():
        candidates.append(results_model.resolve())

    logs_dir = project_root / "logs"
    if logs_dir.exists():
        # Prefer run-specific sidecar TOMLs (same basename as results dir).
        candidates.extend(sorted(path.resolve() for path in logs_dir.glob(f"{results_dir.name}.parameters*.toml")))

        # Then fall back to event-level sidecars.
        event = event_from_results_dir(results_dir)
        if event:
            candidates.extend(sorted(path.resolve() for path in logs_dir.glob(f"{event}.parameters*.toml")))
            # Legacy recovery: discover event TOMLs from top-level config packs
            # (e.g., *_configs_active, *_configs_v1). This supports older runs
            # that predate sidecar model.toml copies in results directories.
            for top in sorted(project_root.iterdir()):
                if not top.is_dir():
                    continue
                name = top.name.lower()
                if "config" not in name:
                    continue
                event_toml = top / f"{event}.toml"
                if event_toml.exists():
                    candidates.append(event_toml.resolve())

    # Keep current path in the candidate set for diagnostics de-dup, but place
    # it at the end so we try alternatives first when recovering.
    if current_params_path.exists():
        candidates.append(current_params_path.resolve())

    # De-duplicate while preserving order.
    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)

    return deduped


def recover_params_path_for_target_dim(
    *,
    project_root: Path,
    results_dir: Path,
    obs_path: Path,
    params_path: Path,
    target_dim: int | None,
) -> tuple[Path, str | None]:
    if target_dim is None:
        return params_path, None

    tried_rows: list[tuple[Path, str]] = []
    candidates = candidate_param_paths_for_dim_recovery(project_root, results_dir, params_path)
    if not candidates:
        return params_path, None

    for candidate in candidates:
        try:
            ampy_candidate = Ampy(obs_path, candidate)
            dim = len(ampy_candidate.mcmc.params.fitting)
            tried_rows.append((candidate, f"dim={dim}"))
            if dim == target_dim:
                if candidate.resolve() == params_path.resolve():
                    return params_path, None
                return candidate, (
                    f"auto-switched params TOML to dimension-compatible file "
                    f"({target_dim}): {candidate}"
                )
        except Exception as exc:  # pragma: no cover - best-effort diagnostics
            tried_rows.append((candidate, f"error={exc}"))

    tried_text = "\n".join(f"  - {path} ({status})" for path, status in tried_rows)
    raise ValueError(
        "No dimension-compatible parameter TOML found for minimization.\n"
        f"Expected ndim from chain: {target_dim}\n"
        f"Current params path: {params_path}\n"
        "Tried candidates:\n"
        f"{tried_text}\n"
        "Recommendation: ensure <results>/model.toml exists and matches the run that produced chain.npz."
    )


def build_bounds(ampy: Ampy) -> np.ndarray:
    bounds: list[tuple[float, float]] = []
    for param in ampy.mcmc.params.fitting:
        if isinstance(param.prior, GaussianPrior):
            bounds.append((param.prior.lower * 3, param.prior.upper * 3))
        else:
            bounds.append((param.prior.lower, param.prior.upper))
    return np.asarray(bounds)


def initial_from_best_fit(ampy: Ampy, best_fit: dict[str, Any]) -> np.ndarray:
    flat = flatten_best_fit(best_fit)
    initial: list[float] = []
    missing: list[str] = []

    for param in ampy.mcmc.params.fitting:
        if param.name not in flat:
            missing.append(param.name)
            continue
        initial.append(utils.to_scale(flat[param.name], from_s="linear", to_s=param.scale))

    if missing:
        raise KeyError(
            "Initial best_fit JSON is missing fitting parameters: "
            + ", ".join(missing)
        )

    return np.asarray(initial, dtype=float)


def walker_seeds_from_chain(chain_path: Path, max_walkers: int | None) -> list[dict[str, Any]]:
    with np.load(chain_path) as data:
        if "chain" not in data or "lnprob" not in data:
            raise KeyError(f"{chain_path} must contain 'chain' and 'lnprob'.")
        chain = np.asarray(data["chain"])
        lnprob = np.asarray(data["lnprob"])

    # Support both [steps, walkers, ndim] and [steps, temps, walkers, ndim]
    if chain.ndim == 4:
        chain = chain[:, 0, :, :]
    if lnprob.ndim == 3:
        lnprob = lnprob[:, 0, :]

    if chain.ndim != 3:
        raise ValueError(f"Unexpected chain shape {chain.shape}; expected [steps, walkers, ndim].")
    if lnprob.ndim != 2:
        raise ValueError(f"Unexpected lnprob shape {lnprob.shape}; expected [steps, walkers].")
    if chain.shape[:2] != lnprob.shape:
        raise ValueError(
            f"Shape mismatch between chain and lnprob: {chain.shape[:2]} vs {lnprob.shape}."
        )

    seeds: list[dict[str, Any]] = []
    steps, walkers, _ = chain.shape
    _ = steps
    for walker in range(walkers):
        scores = lnprob[:, walker]
        finite = np.isfinite(scores)
        if not finite.any():
            continue
        best_step = int(np.argmax(np.where(finite, scores, -np.inf)))
        seeds.append(
            {
                "walker": walker,
                "step": best_step,
                "seed_logprob": float(scores[best_step]),
                "x0": np.asarray(chain[best_step, walker, :], dtype=float),
            }
        )

    seeds.sort(key=lambda row: row["seed_logprob"], reverse=True)
    if max_walkers is not None and max_walkers > 0:
        seeds = seeds[:max_walkers]

    return seeds


def minimize_once(
    x0: np.ndarray,
    ampy: Ampy,
    bounds: np.ndarray,
    minimizer_name: str,
    scipy_method: str,
    fallback_scipy_method: str | None,
    retry_on_failure: bool,
    retry_on_edge: bool,
) -> tuple[optimize.OptimizeResult, dict[str, Any]]:
    func_args = (ampy.mcmc.params, ampy.mcmc.models)
    return run_minimizer(
        x0=x0,
        func_args=func_args,
        bounds=bounds,
        minimizer=minimizer_name,
        scipy_method=scipy_method,
        fallback_scipy_method=fallback_scipy_method,
        retry_on_failure=retry_on_failure,
        retry_on_edge=retry_on_edge,
    )


def pack_result(
    result: optimize.OptimizeResult,
    ampy: Ampy,
    seed_info: dict[str, Any],
    minimizer_meta: dict[str, Any],
) -> dict[str, Any]:
    func_args = (ampy.mcmc.params, ampy.mcmc.models)
    params_linear = ampy.mcmc.params.samples_to_dict(result.x)
    nmap = -2.0 * float(log_posterior_fn(result.x, *func_args))

    payload: dict[str, Any] = dict(seed_info)
    payload["success"] = bool(result.success)
    payload["message"] = str(result.message)
    payload["nmap"] = float(nmap)
    payload["params"] = params_linear
    payload["x"] = [float(val) for val in np.asarray(result.x).ravel()]
    payload.update(minimizer_meta)
    return payload


def seed_nmap(
    x0: np.ndarray,
    ampy: Ampy,
) -> float:
    func_args = (ampy.mcmc.params, ampy.mcmc.models)
    return -2.0 * float(log_posterior_fn(x0, *func_args))


def preserve_seed_payload(
    x0: np.ndarray,
    ampy: Ampy,
    seed_info: dict[str, Any],
    minimizer_meta: dict[str, Any],
    optimizer_payload: dict[str, Any],
    *,
    reason: str,
    seed_nmap_override: float | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = dict(seed_info)
    payload["success"] = True
    payload["message"] = reason
    if seed_nmap_override is not None and np.isfinite(seed_nmap_override):
        payload["nmap"] = float(seed_nmap_override)
    else:
        payload["nmap"] = float(seed_nmap(x0, ampy))
    payload["params"] = ampy.mcmc.params.samples_to_dict(x0)
    payload["x"] = [float(val) for val in np.asarray(x0).ravel()]
    payload.update(minimizer_meta)
    payload["optimizer_backend"] = "seed_preserved"
    payload["scipy_method"] = "seed_preserved"
    payload["seed_preserved"] = True
    payload["optimizer_nmap"] = float(optimizer_payload["nmap"])
    return payload


def choose_seed_or_optimizer(
    x0: np.ndarray,
    ampy: Ampy,
    seed_info: dict[str, Any],
    minimizer_meta: dict[str, Any],
    optimizer_payload: dict[str, Any],
) -> dict[str, Any]:
    start_nmap = seed_nmap(x0, ampy)
    optimizer_payload["seed_nmap"] = float(start_nmap)
    seed_file_nmap = seed_info.get("seed_nmap_file")
    if (
        np.isfinite(start_nmap)
        and isinstance(seed_file_nmap, (int, float))
        and np.isfinite(float(seed_file_nmap))
    ):
        delta = abs(float(start_nmap) - float(seed_file_nmap))
        optimizer_payload["seed_nmap_delta_vs_file"] = float(delta)
        # If the recomputed seed objective diverges strongly from the value
        # saved at MCMC completion, the runtime/model path has drifted and
        # minimization is no longer apples-to-apples.
        if delta > 10.0:
            return preserve_seed_payload(
                x0,
                ampy,
                seed_info,
                minimizer_meta,
                optimizer_payload,
                reason=(
                    "Preserved seed because recomputed seed objective differs "
                    "strongly from saved MCMC nmap (runtime mismatch guard)."
                ),
                seed_nmap_override=float(seed_file_nmap),
            )
    if not np.isfinite(start_nmap):
        if isinstance(seed_file_nmap, (int, float)) and np.isfinite(float(seed_file_nmap)):
            return preserve_seed_payload(
                x0,
                ampy,
                seed_info,
                minimizer_meta,
                optimizer_payload,
                reason="Preserved seed because recomputed seed objective is non-finite in current runtime.",
                seed_nmap_override=float(seed_file_nmap),
            )
        return optimizer_payload
    if np.isfinite(start_nmap) and float(optimizer_payload["nmap"]) > float(start_nmap):
        return preserve_seed_payload(
            x0,
            ampy,
            seed_info,
            minimizer_meta,
            optimizer_payload,
            reason="Preserved walker seed because optimizer worsened the objective.",
        )
    return optimizer_payload


_PARALLEL_STATE: dict[str, Any] = {}


def normalize_parallel_workers(parallel_workers: int | None, seed_count: int) -> int:
    if parallel_workers is None:
        return 1
    return max(1, min(int(parallel_workers), seed_count))


def _parallel_context():
    try:
        return mp.get_context("fork")
    except ValueError:
        return mp.get_context()


def _parallel_init_worker(
    obs_path: str,
    params_path: str,
    bounds: np.ndarray,
    minimizer_name: str,
    scipy_method: str,
    fallback_scipy_method: str | None,
    retry_on_failure: bool,
    retry_on_edge: bool,
) -> None:
    global _PARALLEL_STATE
    _PARALLEL_STATE = {
        "ampy": Ampy(Path(obs_path), Path(params_path)),
        "bounds": np.asarray(bounds, dtype=float),
        "minimizer_name": minimizer_name,
        "scipy_method": scipy_method,
        "fallback_scipy_method": fallback_scipy_method,
        "retry_on_failure": bool(retry_on_failure),
        "retry_on_edge": bool(retry_on_edge),
    }


def _parallel_minimize_seed(seed: dict[str, Any]) -> dict[str, Any]:
    if not _PARALLEL_STATE:
        raise RuntimeError("Parallel minimizer worker state was not initialized.")

    ampy = _PARALLEL_STATE["ampy"]
    bounds = _PARALLEL_STATE["bounds"]
    minimizer_name = _PARALLEL_STATE["minimizer_name"]
    scipy_method = _PARALLEL_STATE["scipy_method"]
    fallback_scipy_method = _PARALLEL_STATE["fallback_scipy_method"]
    retry_on_failure = _PARALLEL_STATE["retry_on_failure"]
    retry_on_edge = _PARALLEL_STATE["retry_on_edge"]
    x0 = np.asarray(seed["x0"], dtype=float)
    seed_info = {key: value for key, value in seed.items() if key != "x0"}
    try:
        result, minimizer_meta = minimize_once(
            x0=x0,
            ampy=ampy,
            bounds=bounds,
            minimizer_name=minimizer_name,
            scipy_method=scipy_method,
            fallback_scipy_method=fallback_scipy_method,
            retry_on_failure=retry_on_failure,
            retry_on_edge=retry_on_edge,
        )
        optimizer_payload = pack_result(result, ampy, seed_info, minimizer_meta)
        return choose_seed_or_optimizer(x0, ampy, seed_info, minimizer_meta, optimizer_payload)
    except Exception as exc:  # pragma: no cover - defensive queue hardening
        minimizer_meta = {
            "optimizer_backend": minimizer_name,
            "scipy_method": "seed_preserved",
            "fallback_attempted": False,
            "retry_reason": f"minimizer_exception: {exc}",
            "attempts": [],
        }
        return preserve_seed_payload(
            x0,
            ampy,
            seed_info,
            minimizer_meta,
            {"nmap": float("nan")},
            reason=f"Preserved walker seed after minimizer exception: {exc}",
        )


def minimize_seed_collection(
    seeds: list[dict[str, Any]],
    *,
    ampy: Ampy,
    bounds: np.ndarray,
    minimizer_name: str,
    scipy_method: str,
    fallback_scipy_method: str | None,
    retry_on_failure: bool,
    retry_on_edge: bool,
    parallel_workers: int | None,
    obs_path: Path,
    params_path: Path,
) -> list[dict[str, Any]]:
    worker_count = normalize_parallel_workers(parallel_workers, len(seeds))
    if worker_count == 1:
        results: list[dict[str, Any]] = []
        for seed in seeds:
            x0 = np.asarray(seed["x0"], dtype=float)
            seed_info = {key: value for key, value in seed.items() if key != "x0"}
            try:
                result, minimizer_meta = minimize_once(
                    x0=x0,
                    ampy=ampy,
                    bounds=bounds,
                    minimizer_name=minimizer_name,
                    scipy_method=scipy_method,
                    fallback_scipy_method=fallback_scipy_method,
                    retry_on_failure=retry_on_failure,
                    retry_on_edge=retry_on_edge,
                )
                optimizer_payload = pack_result(result, ampy, seed_info, minimizer_meta)
                results.append(choose_seed_or_optimizer(x0, ampy, seed_info, minimizer_meta, optimizer_payload))
            except Exception as exc:  # pragma: no cover - defensive queue hardening
                minimizer_meta = {
                    "optimizer_backend": minimizer_name,
                    "scipy_method": "seed_preserved",
                    "fallback_attempted": False,
                    "retry_reason": f"minimizer_exception: {exc}",
                    "attempts": [],
                }
                results.append(
                    preserve_seed_payload(
                        x0,
                        ampy,
                        seed_info,
                        minimizer_meta,
                        {"nmap": float("nan")},
                        reason=f"Preserved walker seed after minimizer exception: {exc}",
                    )
                )
        return results

    with ProcessPoolExecutor(
        max_workers=worker_count,
        mp_context=_parallel_context(),
        initializer=_parallel_init_worker,
        initargs=(
            str(obs_path),
            str(params_path),
            bounds,
            minimizer_name,
            scipy_method,
            fallback_scipy_method,
            retry_on_failure,
            retry_on_edge,
        ),
    ) as executor:
        return list(executor.map(_parallel_minimize_seed, seeds))


def run_single_mode(
    ampy: Ampy,
    bounds: np.ndarray,
    initial_path: Path,
    results_out: Path,
    minimizer_name: str,
    scipy_method: str,
    fallback_scipy_method: str | None,
    retry_on_failure: bool,
    retry_on_edge: bool,
) -> dict[str, Any]:
    best_fit = load_json(initial_path)
    x0 = initial_from_best_fit(ampy, best_fit)
    seed_file_nmap = best_fit.get("nmap")
    recomputed_seed_nmap = seed_nmap(x0, ampy)
    if (
        np.isfinite(recomputed_seed_nmap)
        and isinstance(seed_file_nmap, (int, float))
        and np.isfinite(float(seed_file_nmap))
        and abs(float(recomputed_seed_nmap) - float(seed_file_nmap)) > 10.0
    ):
        payload = preserve_seed_payload(
            x0,
            ampy,
            {
                "mode": "single",
                "initial_path": str(initial_path),
                "seed_nmap_file": seed_file_nmap,
            },
            {"optimizer_backend": minimizer_name},
            {"nmap": float("nan")},
            reason=(
                "Preserved seed because recomputed seed objective differs "
                "strongly from saved MCMC nmap (runtime mismatch guard)."
            ),
            seed_nmap_override=float(seed_file_nmap),
        )
        write_json(results_out / "minimized.json", payload)
        return payload

    result, minimizer_meta = minimize_once(
        x0,
        ampy,
        bounds,
        minimizer_name,
        scipy_method,
        fallback_scipy_method,
        retry_on_failure,
        retry_on_edge,
    )
    payload = pack_result(
        result,
        ampy,
        {
            "mode": "single",
            "initial_path": str(initial_path),
            "seed_nmap_file": seed_file_nmap,
        },
        minimizer_meta,
    )
    payload = choose_seed_or_optimizer(
        x0,
        ampy,
        {
            "mode": "single",
            "initial_path": str(initial_path),
            "seed_nmap_file": seed_file_nmap,
        },
        minimizer_meta,
        payload,
    )
    write_json(results_out / "minimized.json", payload)
    return payload


def run_walker_mode(
    ampy: Ampy,
    bounds: np.ndarray,
    chain_path: Path,
    results_out: Path,
    minimizer_name: str,
    scipy_method: str,
    fallback_scipy_method: str | None,
    retry_on_failure: bool,
    retry_on_edge: bool,
    max_walkers: int | None,
    parallel_workers: int | None,
    obs_path: Path,
    params_path: Path,
) -> dict[str, Any]:
    seeds = walker_seeds_from_chain(chain_path, max_walkers=max_walkers)
    if not seeds:
        raise RuntimeError(f"No valid walker seeds found in {chain_path}.")

    tagged_seeds = [
        {
            "mode": "walker",
            "walker": int(seed["walker"]),
            "step": int(seed["step"]),
            "seed_logprob": float(seed["seed_logprob"]),
            "x0": np.asarray(seed["x0"], dtype=float),
        }
        for seed in seeds
    ]
    all_results = minimize_seed_collection(
        tagged_seeds,
        ampy=ampy,
        bounds=bounds,
        minimizer_name=minimizer_name,
        scipy_method=scipy_method,
        fallback_scipy_method=fallback_scipy_method,
        retry_on_failure=retry_on_failure,
        retry_on_edge=retry_on_edge,
        parallel_workers=parallel_workers,
        obs_path=obs_path,
        params_path=params_path,
    )

    all_results.sort(key=lambda row: row["nmap"])
    best = best_result(all_results)

    write_json(results_out / "minimized_walkers.json", all_results)
    write_json(results_out / "minimized.json", best)

    with (results_out / "minimized_walkers.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "walker",
                "step",
                "seed_logprob",
                "nmap",
                "success",
                "scipy_method",
                "fallback_attempted",
                "message",
            ],
        )
        writer.writeheader()
        for row in all_results:
            writer.writerow(
                {
                    "walker": row.get("walker"),
                    "step": row.get("step"),
                    "seed_logprob": row.get("seed_logprob"),
                    "nmap": row.get("nmap"),
                    "success": row.get("success"),
                    "scipy_method": row.get("scipy_method"),
                    "fallback_attempted": row.get("fallback_attempted"),
                    "message": row.get("message"),
                }
            )

    return {
        "best": best,
        "count": len(all_results),
    }


def failed_seeds_from_previous(
    previous_path: Path,
    chain_path: Path,
    max_walkers: int | None,
) -> list[dict[str, Any]]:
    previous = load_json(previous_path)
    if not isinstance(previous, list):
        raise ValueError(f"{previous_path} must contain a JSON list.")

    failed_rows: list[dict[str, Any]] = []
    for row in previous:
        if not isinstance(row, dict):
            continue
        if bool(row.get("success")):
            continue
        if "walker" not in row or "step" not in row:
            continue
        failed_rows.append(row)

    if not failed_rows:
        return []

    failed_rows.sort(key=lambda row: float(row.get("nmap", np.inf)))
    if max_walkers is not None and max_walkers > 0:
        failed_rows = failed_rows[:max_walkers]

    with np.load(chain_path) as data:
        if "chain" not in data:
            raise KeyError(f"{chain_path} must contain 'chain'.")
        chain = np.asarray(data["chain"])

    if chain.ndim == 4:
        chain = chain[:, 0, :, :]
    if chain.ndim != 3:
        raise ValueError(f"Unexpected chain shape {chain.shape}; expected [steps, walkers, ndim].")

    n_steps, n_walkers, _ = chain.shape
    seeds: list[dict[str, Any]] = []
    for row in failed_rows:
        walker = int(row["walker"])
        step = int(row["step"])
        if walker < 0 or walker >= n_walkers:
            continue
        if step < 0 or step >= n_steps:
            continue
        seeds.append(
            {
                "walker": walker,
                "step": step,
                "seed_logprob": float(row.get("seed_logprob", np.nan)),
                "prev_nmap": float(row.get("nmap", np.nan)),
                "prev_success": bool(row.get("success")),
                "prev_message": str(row.get("message", "")),
                "x0": np.asarray(chain[step, walker, :], dtype=float),
            }
        )

    return seeds


def run_seed_mode(
    ampy: Ampy,
    bounds: np.ndarray,
    seeds: list[dict[str, Any]],
    results_out: Path,
    minimizer_name: str,
    mode_label: str,
    scipy_method: str,
    fallback_scipy_method: str | None,
    retry_on_failure: bool,
    retry_on_edge: bool,
    parallel_workers: int | None,
    obs_path: Path,
    params_path: Path,
) -> dict[str, Any]:
    if not seeds:
        raise RuntimeError("No seeds available for minimization.")

    tagged_seeds = []
    for seed in seeds:
        seed_info = {key: value for key, value in seed.items() if key != "x0"}
        seed_info["mode"] = mode_label
        seed_info["x0"] = np.asarray(seed["x0"], dtype=float)
        tagged_seeds.append(seed_info)

    all_results = minimize_seed_collection(
        tagged_seeds,
        ampy=ampy,
        bounds=bounds,
        minimizer_name=minimizer_name,
        scipy_method=scipy_method,
        fallback_scipy_method=fallback_scipy_method,
        retry_on_failure=retry_on_failure,
        retry_on_edge=retry_on_edge,
        parallel_workers=parallel_workers,
        obs_path=obs_path,
        params_path=params_path,
    )

    all_results.sort(key=lambda row: row["nmap"])
    best = best_result(all_results)

    write_json(results_out / "minimized_walkers.json", all_results)
    write_json(results_out / "minimized.json", best)

    with (results_out / "minimized_walkers.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "walker",
                "step",
                "seed_logprob",
                "nmap",
                "success",
                "scipy_method",
                "fallback_attempted",
                "message",
            ],
        )
        writer.writeheader()
        for row in all_results:
            writer.writerow(
                {
                    "walker": row.get("walker"),
                    "step": row.get("step"),
                    "seed_logprob": row.get("seed_logprob"),
                    "nmap": row.get("nmap"),
                    "success": row.get("success"),
                    "scipy_method": row.get("scipy_method"),
                    "fallback_attempted": row.get("fallback_attempted"),
                    "message": row.get("message"),
                }
            )

    return {
        "best": best,
        "count": len(all_results),
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Run local MAP minimization from finished MCMC outputs.")
    parser.add_argument("--results", required=True, help="Result directory containing chain.npz and best_fit.json.")
    parser.add_argument("--obs", help="Observation CSV path. If omitted, inferred from event.")
    parser.add_argument("--params", help="Model TOML path. If omitted, inferred from event/model.")
    parser.add_argument(
        "--mode",
        default="walkers",
        choices=("walkers", "single", "rerun_failed"),
        help="single: refine from best_fit.json. walkers: refine from each walker's local optimum.",
    )
    parser.add_argument(
        "--initial",
        help="Initial best-fit JSON for --mode single. Defaults to <results>/best_fit.json.",
    )
    parser.add_argument(
        "--max-walkers",
        type=int,
        default=None,
        help="Optional cap on walkers processed in --mode walkers (uses highest seed logprob first).",
    )
    parser.add_argument(
        "--parallel-workers",
        type=int,
        default=1,
        help="Number of walker seeds to minimize in parallel.",
    )
    parser.add_argument(
        "--minimizer",
        default="minimize",
        choices=("minimize", "basinhopping"),
        help="Scipy optimizer backend.",
    )
    parser.add_argument(
        "--scipy-method",
        default=DEFAULT_SCIPY_METHOD,
        help=(
            "SciPy local minimization method to use first. "
            f"Supported: {', '.join(SUPPORTED_SCIPY_METHODS)}."
        ),
    )
    parser.add_argument(
        "--fallback-scipy-method",
        default=DEFAULT_FALLBACK_SCIPY_METHOD,
        help=(
            "Optional fallback SciPy method for failed or edge-hugging first attempts. "
            f"Supported: {', '.join(SUPPORTED_SCIPY_METHODS)}, none."
        ),
    )
    parser.add_argument(
        "--retry-on-failure",
        type=int,
        choices=(0, 1),
        default=1,
        help="Retry with the fallback method when the first attempt returns success=false.",
    )
    parser.add_argument(
        "--retry-on-edge",
        type=int,
        choices=(0, 1),
        default=1,
        help="Retry with the fallback method when the first attempt lands on a prior boundary.",
    )
    parser.add_argument(
        "--output",
        help="Output directory for minimized products. Defaults to <results>/minimized.",
    )
    parser.add_argument(
        "--previous-walkers",
        help=(
            "For --mode rerun_failed, JSON list of prior walker minimizations to filter by "
            "success=false. Defaults to <results>/minimized/minimized_walkers.json."
        ),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    results_dir = Path(args.results).expanduser().resolve()
    if not results_dir.exists():
        raise FileNotFoundError(f"Results directory does not exist: {results_dir}")

    best_fit_path = results_dir / "best_fit.json"
    chain_path = results_dir / "chain.npz"
    if not best_fit_path.exists():
        raise FileNotFoundError(f"Missing best_fit.json in results directory: {best_fit_path}")
    if not chain_path.exists() and args.mode == "walkers":
        raise FileNotFoundError(f"Missing chain.npz for walker minimization: {chain_path}")

    best_fit = load_json(best_fit_path)
    project_root = Path(__file__).resolve().parents[1]
    obs_path, params_path = resolve_obs_and_params(args, project_root, results_dir, best_fit)
    scipy_method = normalize_scipy_method(args.scipy_method)
    fallback_scipy_method = normalize_scipy_method(args.fallback_scipy_method, allow_none=True)
    retry_on_failure = bool(args.retry_on_failure)
    retry_on_edge = bool(args.retry_on_edge)

    if args.output:
        output_dir = Path(args.output).expanduser().resolve()
    elif args.mode == "rerun_failed":
        output_dir = results_dir / "minimized_rerun_failed"
    else:
        output_dir = results_dir / "minimized"
    output_dir.mkdir(parents=True, exist_ok=True)

    dim_recovery_note: str | None = None
    if args.mode in {"walkers", "rerun_failed"}:
        target_dim = chain_parameter_dim(chain_path)
        params_path, dim_recovery_note = recover_params_path_for_target_dim(
            project_root=project_root,
            results_dir=results_dir,
            obs_path=obs_path,
            params_path=params_path,
            target_dim=target_dim,
        )

    ampy = Ampy(obs_path, params_path)
    bounds = build_bounds(ampy)
    print(f"obs: {obs_path}")
    print(f"params: {params_path}")
    if dim_recovery_note:
        print(f"params_recovery: {dim_recovery_note}")

    if args.mode == "single":
        initial_path = Path(args.initial).expanduser().resolve() if args.initial else best_fit_path
        payload = run_single_mode(
            ampy=ampy,
            bounds=bounds,
            initial_path=initial_path,
            results_out=output_dir,
            minimizer_name=args.minimizer,
            scipy_method=scipy_method,
            fallback_scipy_method=fallback_scipy_method,
            retry_on_failure=retry_on_failure,
            retry_on_edge=retry_on_edge,
        )
        print("single minimize complete")
        print(f"results: {output_dir / 'minimized.json'}")
        primary_method = payload.get("primary_scipy_method", "n/a")
        fallback_method = payload.get("fallback_scipy_method", "n/a")
        print(
            "method: "
            f"{payload.get('scipy_method', 'n/a')} "
            f"(primary={primary_method} fallback={fallback_method})"
        )
        print(f"success: {payload['success']} nmap={payload['nmap']:.6f}")
        return

    if args.mode == "rerun_failed":
        previous_path = (
            Path(args.previous_walkers).expanduser().resolve()
            if args.previous_walkers
            else (results_dir / "minimized" / "minimized_walkers.json")
        )
        if not previous_path.exists():
            raise FileNotFoundError(
                f"Missing previous walker minimizations for rerun_failed: {previous_path}"
            )
        seeds = failed_seeds_from_previous(
            previous_path=previous_path,
            chain_path=chain_path,
            max_walkers=args.max_walkers,
        )
        payload = run_seed_mode(
            ampy=ampy,
            bounds=bounds,
            seeds=seeds,
            results_out=output_dir,
            minimizer_name=args.minimizer,
            mode_label="rerun_failed",
            scipy_method=scipy_method,
            fallback_scipy_method=fallback_scipy_method,
            retry_on_failure=retry_on_failure,
            retry_on_edge=retry_on_edge,
            parallel_workers=args.parallel_workers,
            obs_path=obs_path,
            params_path=params_path,
        )
    else:
        payload = run_walker_mode(
            ampy=ampy,
            bounds=bounds,
            chain_path=chain_path,
            results_out=output_dir,
            minimizer_name=args.minimizer,
            scipy_method=scipy_method,
            fallback_scipy_method=fallback_scipy_method,
            retry_on_failure=retry_on_failure,
            retry_on_edge=retry_on_edge,
            max_walkers=args.max_walkers,
            parallel_workers=args.parallel_workers,
            obs_path=obs_path,
            params_path=params_path,
        )
    best = payload["best"]
    if args.mode == "rerun_failed":
        print("rerun_failed minimization complete")
    else:
        print("walker minimization complete")
    print(f"processed_walkers: {payload['count']}")
    print(f"best: {output_dir / 'minimized.json'}")
    print(f"all: {output_dir / 'minimized_walkers.json'}")
    print(
        "method: "
        f"{best['scipy_method']} "
        f"(primary={best['primary_scipy_method']} fallback={best['fallback_scipy_method']})"
    )
    print(f"success: {best['success']} nmap={best['nmap']:.6f}")


if __name__ == "__main__":
    main()
