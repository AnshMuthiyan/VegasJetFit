#!/usr/bin/env python3
"""Create a self-contained posterior-branch run folder from filtered samples."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jetfit.mcmc.parameters import Parameters


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, type=Path, help="Source finished run directory.")
    parser.add_argument("--out", required=True, type=Path, help="Output branch run directory.")
    parser.add_argument("--parameter", required=True, help="Fitted parameter name to filter.")
    parser.add_argument("--lt", type=float, default=None, help="Keep samples with parameter < value.")
    parser.add_argument("--gt", type=float, default=None, help="Keep samples with parameter > value.")
    parser.add_argument("--nwalkers", type=int, default=10, help="Walker count for the repacked branch chain.")
    parser.add_argument("--event", default=None, help="Event label for README/provenance.")
    parser.add_argument("--note", default="", help="Human-readable scientific rationale.")
    return parser.parse_args()


def finite_summary(values: np.ndarray) -> dict[str, float | int]:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {
            "n_samples": 0,
            "mean": float("nan"),
            "sd": float("nan"),
            "q02_5": float("nan"),
            "q16": float("nan"),
            "median": float("nan"),
            "q84": float("nan"),
            "q97_5": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
        }
    qs = np.quantile(arr, [0.025, 0.16, 0.5, 0.84, 0.975])
    return {
        "n_samples": int(arr.size),
        "mean": float(np.mean(arr)),
        "sd": float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0,
        "q02_5": float(qs[0]),
        "q16": float(qs[1]),
        "median": float(qs[2]),
        "q84": float(qs[3]),
        "q97_5": float(qs[4]),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def write_parameter_summary(out: Path, names: list[str], samples: np.ndarray) -> None:
    fields = ["parameter", "n_samples", "mean", "sd", "q02_5", "q16", "median", "q84", "q97_5", "min", "max"]
    with (out / "posterior_summary_filtered.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, name in enumerate(names):
            writer.writerow({"parameter": name, **finite_summary(samples[:, index])})


def build_mask(values: np.ndarray, *, lt: float | None, gt: float | None) -> np.ndarray:
    if lt is None and gt is None:
        raise ValueError("At least one of --lt or --gt is required.")
    mask = np.isfinite(values)
    if lt is not None:
        mask &= values < lt
    if gt is not None:
        mask &= values > gt
    return mask


def filter_label(parameter: str, lt: float | None, gt: float | None) -> str:
    pieces: list[str] = []
    if gt is not None:
        pieces.append(f"{parameter} > {gt:g}")
    if lt is not None:
        pieces.append(f"{parameter} < {lt:g}")
    return " and ".join(pieces)


def repack_selected_chain(
    samples: np.ndarray,
    lnprob: np.ndarray,
    *,
    nwalkers: int,
) -> tuple[np.ndarray, np.ndarray]:
    if nwalkers <= 0:
        raise ValueError("--nwalkers must be positive.")
    usable = (samples.shape[0] // nwalkers) * nwalkers
    if usable < nwalkers:
        raise ValueError(f"Only {samples.shape[0]} selected samples; not enough to pack {nwalkers} walkers.")
    packed_samples = samples[:usable].reshape(usable // nwalkers, nwalkers, samples.shape[-1])
    packed_lnprob = lnprob[:usable].reshape(usable // nwalkers, nwalkers)
    return packed_samples, packed_lnprob


def main() -> None:
    args = parse_args()
    source = args.results.expanduser().resolve()
    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    params = Parameters.from_toml(source / "model.toml")
    names = [param.name for param in params.fitting]
    if args.parameter not in names:
        raise KeyError(f"{source} has no fitted parameter named {args.parameter!r}. Available: {names}")
    pidx = names.index(args.parameter)

    with np.load(source / "chain.npz") as data:
        chain = np.asarray(data["chain"], dtype=float)
        if "lnprob" in data.files:
            lnprob = np.asarray(data["lnprob"], dtype=float)
        elif "log_prob" in data.files:
            lnprob = np.asarray(data["log_prob"], dtype=float)
        else:
            raise KeyError(f"{source / 'chain.npz'} must contain lnprob or log_prob.")
        betas = np.asarray(data["betas"], dtype=float) if "betas" in data.files else np.asarray([], dtype=float)

    if chain.ndim == 4:
        chain = chain[:, 0, :, :]
    if lnprob.ndim == 3:
        lnprob = lnprob[:, 0, :]
    if chain.ndim != 3 or lnprob.ndim != 2:
        raise ValueError(f"Unexpected chain/lnprob shapes: {chain.shape}, {lnprob.shape}")

    flat_chain = chain.reshape(-1, chain.shape[-1])
    flat_lnprob = lnprob.reshape(-1)
    values = flat_chain[:, pidx]
    finite = np.isfinite(values) & np.isfinite(flat_lnprob)
    selected_mask = finite & build_mask(values, lt=args.lt, gt=args.gt)
    selected = flat_chain[selected_mask]
    selected_lnprob = flat_lnprob[selected_mask]
    if selected.shape[0] < args.nwalkers:
        raise ValueError(f"Only {selected.shape[0]} samples matched {filter_label(args.parameter, args.lt, args.gt)}.")

    order = np.argsort(selected_lnprob)[::-1]
    selected_by_logprob = selected[order]
    selected_lnprob_by_logprob = selected_lnprob[order]
    packed_chain, packed_lnprob = repack_selected_chain(
        selected_by_logprob,
        selected_lnprob_by_logprob,
        nwalkers=args.nwalkers,
    )

    for name in ("model.toml", "obs.csv", "mcmc_settings.toml", "run.log"):
        src = source / name
        if src.exists():
            shutil.copy2(src, out / name)

    best_x = selected_by_logprob[0]
    best_payload = {
        "mode": "filtered_branch_seed",
        "source_results": str(source),
        "filter": filter_label(args.parameter, args.lt, args.gt),
        "seed_logprob": float(selected_lnprob_by_logprob[0]),
        "nmap": float(-2.0 * selected_lnprob_by_logprob[0]),
        "params": params.samples_to_dict(best_x),
        "x": [float(v) for v in best_x],
    }
    (out / "best_fit.json").write_text(json.dumps(best_payload, indent=2))

    np.savez_compressed(
        out / "chain.npz",
        chain=packed_chain,
        lnprob=packed_lnprob,
        betas=betas,
    )
    np.savez_compressed(
        out / "selected_parameter_samples.npz",
        samples=selected.astype(np.float32),
        lnprob=selected_lnprob.astype(np.float32),
        parameter_names=np.asarray(names),
    )
    write_parameter_summary(out, names, selected)

    selected_values = selected[:, pidx]
    event = args.event or source.name.split("_", 1)[0]
    manifest = {
        "event": event,
        "source_results": str(source),
        "source_chain": str(source / "chain.npz"),
        "output_results": str(out),
        "filter": filter_label(args.parameter, args.lt, args.gt),
        "parameter": args.parameter,
        "n_source_samples": int(flat_chain.shape[0]),
        "n_finite_samples": int(finite.sum()),
        "n_selected_samples": int(selected.shape[0]),
        "selected_fraction_of_finite": float(selected.shape[0] / max(int(finite.sum()), 1)),
        "repacked_chain_shape": list(packed_chain.shape),
        "n_dropped_for_even_repack": int(selected.shape[0] - packed_chain.shape[0] * packed_chain.shape[1]),
        "best_selected_seed_nmap": float(-2.0 * selected_lnprob_by_logprob[0]),
        "best_selected_seed_logprob": float(selected_lnprob_by_logprob[0]),
        "selected_parameter_summary": finite_summary(selected_values),
        "note": args.note,
    }
    (out / "selection_manifest.json").write_text(json.dumps(manifest, indent=2))

    readme = [
        f"# {event} Filtered Posterior Branch",
        "",
        f"Source run: `{source}`",
        f"Filter: `{manifest['filter']}`",
        "",
        args.note.strip(),
        "",
        "This directory is a self-contained branch-local result folder. Its `chain.npz` is repacked from the selected posterior samples so the standard minimizer and postfit product scripts can operate on this posterior island.",
        "",
        f"- selected samples: {manifest['n_selected_samples']} / {manifest['n_finite_samples']} finite samples",
        f"- selected fraction: {manifest['selected_fraction_of_finite']:.6f}",
        f"- repacked chain shape: `{tuple(manifest['repacked_chain_shape'])}`",
        f"- dropped only for even repack: {manifest['n_dropped_for_even_repack']}",
        f"- best selected seed nmap: {manifest['best_selected_seed_nmap']:.6f}",
        "",
        "Key branch files:",
        "",
        "- `chain.npz`: repacked selected branch chain.",
        "- `best_fit.json`: highest-log-probability selected sample, used only as a branch seed/fallback.",
        "- `selected_parameter_samples.npz`: all selected samples before repacking.",
        "- `posterior_summary_filtered.csv`: fitted-parameter summaries for the selected branch.",
        "- `selection_manifest.json`: provenance, filter, and sample counts.",
    ]
    (out / "README.md").write_text("\n".join(line for line in readme if line is not None))

    print(
        "parameter_filtered_branch_ok "
        f"out={out} selected={manifest['n_selected_samples']} "
        f"fraction={manifest['selected_fraction_of_finite']:.6f} "
        f"shape={tuple(manifest['repacked_chain_shape'])}"
    )


if __name__ == "__main__":
    main()
