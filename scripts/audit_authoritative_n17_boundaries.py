#!/usr/bin/env python3
"""Audit n17 upper-bound proximity in an authoritative GRB source manifest."""
from __future__ import annotations

import argparse
import csv
import json
import re
import tomllib
from pathlib import Path

import numpy as np


SECTIONS = ("model", "extinction", "offsets", "host", "slop")


def source_results(event_dir: Path) -> Path:
    text = (event_dir / "sync_manifest.txt").read_text(errors="replace")
    match = re.search(r"^source_results=(.+)$", text, flags=re.MULTILINE)
    if not match:
        raise ValueError(f"No source_results entry in {event_dir / 'sync_manifest.txt'}")
    return Path(match.group(1)).expanduser().resolve()


def fitted_names(model_path: Path) -> list[str]:
    with model_path.open("rb") as handle:
        config = tomllib.load(handle)
    return [
        str(entry["name"])
        for section in SECTIONS
        for entry in config.get(section, [])
        if isinstance(entry, dict) and isinstance(entry.get("prior"), dict)
    ]


def n17_bounds(model_path: Path) -> tuple[float, float]:
    with model_path.open("rb") as handle:
        config = tomllib.load(handle)
    entry = next(item for item in config["model"] if item.get("name") == "n017")
    prior = entry["prior"]
    return float(prior["lower"]), float(prior["upper"])


def classify(q99: float, fraction_above_99_percent: float) -> str:
    if fraction_above_99_percent >= 0.10:
        return "boundary_affected"
    if q99 >= 9.5 or fraction_above_99_percent >= 0.01:
        return "expand_and_refit"
    return "no_refit"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--share-root", type=Path, required=True)
    parser.add_argument("--out-csv", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    rows: list[dict[str, object]] = []
    for entry in manifest["events"]:
        event = str(entry["event"])
        event_dir = args.share_root / str(entry["result_path"])
        source = source_results(event_dir)
        names = fitted_names(source / "model.toml")
        index = names.index("n017")
        lower, upper = n17_bounds(source / "model.toml")
        with np.load(source / "chain.npz", allow_pickle=False) as archive:
            chain = np.asarray(archive["chain"], dtype=float)
        if chain.ndim == 4:
            chain = chain[:, 0, :, :]
        values = chain[..., index].reshape(-1)
        values = values[np.isfinite(values)]
        q16, median, q84, q95, q99 = np.quantile(values, [0.16, 0.5, 0.84, 0.95, 0.99])
        near_fraction = float(np.mean(values > upper - 0.1))
        decision = classify(float(q99), near_fraction) if upper == 10.0 else "already_expanded"
        rows.append(
            {
                "event": event,
                "source_results": str(source),
                "prior_lower": lower,
                "prior_upper": upper,
                "samples": values.size,
                "q16": q16,
                "median": median,
                "q84": q84,
                "q95": q95,
                "q99": q99,
                "maximum": float(values.max()),
                "fraction_above_upper_minus_0p1": near_fraction,
                "decision": decision,
            }
        )

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    selected = [row for row in rows if row["decision"] in {"boundary_affected", "expand_and_refit"}]
    lines = [
        "# Authoritative n17 Boundary Audit",
        "",
        "This audit uses the event-by-event source map from the September 1 authoritative meeting book and the retained cold production chain for each GRB.",
        "",
        "The automatic follow-up criterion is deliberately conservative but broader than visible pile-up: refit when at least 1% of samples lie within 0.1 dex of the upper bound, or when the 99th percentile is at least 9.5. A single maximum at 10 is not sufficient.",
        "",
        "| GRB | Median | q84 | q95 | q99 | Fraction > 9.9 | Decision |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['event']} | {row['median']:.3f} | {row['q84']:.3f} | "
            f"{row['q95']:.3f} | {row['q99']:.3f} | "
            f"{100 * row['fraction_above_upper_minus_0p1']:.3f}% | {row['decision']} |"
        )
    lines.extend(
        [
            "",
            "## Follow-up Set",
            "",
            ", ".join(str(row["event"]) for row in selected),
            "",
            "GRB 080319B is already covered by the completed expanded-n17 boundary test and the active all-UVOIR replacement. The other selected events receive controlled posterior-cloud continuations with only the n17 upper bound expanded from 10 to 15.",
        ]
    )
    args.out_md.write_text("\n".join(lines) + "\n")
    print(f"wrote={args.out_csv}")
    print(f"wrote={args.out_md}")
    print("selected=" + ",".join(str(row["event"]) for row in selected))


if __name__ == "__main__":
    main()
