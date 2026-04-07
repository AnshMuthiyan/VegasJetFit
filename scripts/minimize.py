import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy import optimize

from jetfit.ampy import Ampy
from jetfit.core import utils
from jetfit.mcmc.mcmc import log_posterior_fn
from jetfit.mcmc.priors import GaussianPrior


def safe_log_posterior_fn(theta, params, models):
    """Return log posterior with finite fallback for robust minimization."""
    lp = log_posterior_fn(theta, params, models)
    return lp if np.isfinite(lp) else -1e10


def run_minimizer(x0, func_args=(), bounds=(), minimizer="minimize"):
    """Run MAP refinement from initial point ``x0``."""
    nmap = lambda *lp_args: -safe_log_posterior_fn(*lp_args)

    if minimizer == "minimize":
        return optimize.minimize(nmap, x0, args=func_args, bounds=bounds)

    if minimizer == "basinhopping":
        return optimize.basinhopping(
            nmap,
            x0,
            minimizer_kwargs={"method": "L-BFGS-B", "args": func_args, "bounds": bounds},
        )

    raise ValueError(f"Unknown minimizer '{minimizer}'.")


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


def guess_obs_path(project_root: Path, event: str) -> Path | None:
    event_dir = project_root / "jetfit" / "resources" / "grbs" / event
    if not event_dir.exists():
        return None

    for name in (f"{event}clean.csv", f"{event}.csv"):
        candidate = event_dir / name
        if candidate.exists():
            return candidate

    candidates = sorted(event_dir.glob("*.csv"))
    return candidates[0] if candidates else None


def model_hint(best_fit: dict[str, Any], results_dir: Path) -> str:
    mcmc = best_fit.get("mcmc", {})
    if isinstance(mcmc, dict):
        model_name = mcmc.get("model")
        if isinstance(model_name, str) and model_name:
            return model_name

    lower = results_dir.name.lower()
    if "bubble" in lower:
        return "BubbleVegasModel"
    if "smoothbroken" in lower or "sbpl" in lower:
        return "StratifiedFireballModel"
    return "powerlawVegasModel"


def guess_params_path(project_root: Path, event: str, model_name: str) -> tuple[Path | None, list[Path]]:
    logs = project_root / "logs"
    ansh = project_root / "Ansh_Run"
    grb_params = project_root / "jetfit" / "resources" / "grbs" / event / "parameters.toml"

    tried: list[Path] = []
    candidates: list[Path] = []

    if model_name == "BubbleVegasModel":
        candidates.extend(
            [
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
        results_obs = results_dir / "obs.csv"
        if results_obs.exists():
            obs_path = results_obs
        else:
            event = event_from_results_dir(results_dir)
            if event is None:
                raise ValueError("Could not infer event name from results directory. Please pass --obs.")
            inferred_obs = guess_obs_path(project_root, event)
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
) -> optimize.OptimizeResult:
    func_args = (ampy.mcmc.params, ampy.mcmc.models)
    return run_minimizer(x0=x0, func_args=func_args, bounds=bounds, minimizer=minimizer_name)


def pack_result(result: optimize.OptimizeResult, ampy: Ampy, seed_info: dict[str, Any]) -> dict[str, Any]:
    func_args = (ampy.mcmc.params, ampy.mcmc.models)
    params_linear = ampy.mcmc.params.samples_to_dict(result.x)
    nmap = -2.0 * float(log_posterior_fn(result.x, *func_args))

    payload: dict[str, Any] = dict(seed_info)
    payload["success"] = bool(result.success)
    payload["message"] = str(result.message)
    payload["nmap"] = float(nmap)
    payload["params"] = params_linear
    payload["x"] = [float(val) for val in np.asarray(result.x).ravel()]
    return payload


def run_single_mode(
    ampy: Ampy,
    bounds: np.ndarray,
    initial_path: Path,
    results_out: Path,
    minimizer_name: str,
) -> dict[str, Any]:
    best_fit = load_json(initial_path)
    x0 = initial_from_best_fit(ampy, best_fit)
    result = minimize_once(x0, ampy, bounds, minimizer_name)
    payload = pack_result(result, ampy, {"mode": "single", "initial_path": str(initial_path)})
    write_json(results_out / "minimized.json", payload)
    return payload


def run_walker_mode(
    ampy: Ampy,
    bounds: np.ndarray,
    chain_path: Path,
    results_out: Path,
    minimizer_name: str,
    max_walkers: int | None,
) -> dict[str, Any]:
    seeds = walker_seeds_from_chain(chain_path, max_walkers=max_walkers)
    if not seeds:
        raise RuntimeError(f"No valid walker seeds found in {chain_path}.")

    all_results: list[dict[str, Any]] = []
    for seed in seeds:
        result = minimize_once(seed["x0"], ampy, bounds, minimizer_name)
        packed = pack_result(
            result,
            ampy,
            {
                "mode": "walker",
                "walker": int(seed["walker"]),
                "step": int(seed["step"]),
                "seed_logprob": float(seed["seed_logprob"]),
            },
        )
        all_results.append(packed)

    all_results.sort(key=lambda row: row["nmap"])
    best = best_result(all_results)

    write_json(results_out / "minimized_walkers.json", all_results)
    write_json(results_out / "minimized.json", best)

    with (results_out / "minimized_walkers.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["walker", "step", "seed_logprob", "nmap", "success", "message"],
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
) -> dict[str, Any]:
    if not seeds:
        raise RuntimeError("No seeds available for minimization.")

    all_results: list[dict[str, Any]] = []
    for seed in seeds:
        result = minimize_once(seed["x0"], ampy, bounds, minimizer_name)
        seed_info = {k: v for k, v in seed.items() if k != "x0"}
        seed_info["mode"] = mode_label
        packed = pack_result(result, ampy, seed_info)
        all_results.append(packed)

    all_results.sort(key=lambda row: row["nmap"])
    best = best_result(all_results)

    write_json(results_out / "minimized_walkers.json", all_results)
    write_json(results_out / "minimized.json", best)

    with (results_out / "minimized_walkers.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["walker", "step", "seed_logprob", "nmap", "success", "message"],
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
        "--minimizer",
        default="minimize",
        choices=("minimize", "basinhopping"),
        help="Scipy optimizer backend.",
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

    if args.output:
        output_dir = Path(args.output).expanduser().resolve()
    elif args.mode == "rerun_failed":
        output_dir = results_dir / "minimized_rerun_failed"
    else:
        output_dir = results_dir / "minimized"
    output_dir.mkdir(parents=True, exist_ok=True)

    ampy = Ampy(obs_path, params_path)
    bounds = build_bounds(ampy)

    if args.mode == "single":
        initial_path = Path(args.initial).expanduser().resolve() if args.initial else best_fit_path
        payload = run_single_mode(
            ampy=ampy,
            bounds=bounds,
            initial_path=initial_path,
            results_out=output_dir,
            minimizer_name=args.minimizer,
        )
        print("single minimize complete")
        print(f"results: {output_dir / 'minimized.json'}")
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
        )
    else:
        payload = run_walker_mode(
            ampy=ampy,
            bounds=bounds,
            chain_path=chain_path,
            results_out=output_dir,
            minimizer_name=args.minimizer,
            max_walkers=args.max_walkers,
        )
    best = payload["best"]
    if args.mode == "rerun_failed":
        print("rerun_failed minimization complete")
    else:
        print("walker minimization complete")
    print(f"processed_walkers: {payload['count']}")
    print(f"best: {output_dir / 'minimized.json'}")
    print(f"all: {output_dir / 'minimized_walkers.json'}")
    print(f"success: {best['success']} nmap={best['nmap']:.6f}")


if __name__ == "__main__":
    main()
