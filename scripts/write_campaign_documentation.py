#!/usr/bin/env python3
"""Write a compact README and a reproducible method report for an MCMC campaign.

The script reads the canonical TOMLs and dispatch manifest, so campaign
documentation records the actual configuration rather than a remembered setup.
Use it whenever a new campaign directory is created.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - retained for older workers
    import tomli as tomllib


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def fitted_entries(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sections = ("model", "extinction", "offsets")
    result: dict[str, dict[str, Any]] = {}
    for section in sections:
        for entry in config.get(section, []):
            if isinstance(entry, dict) and "name" in entry and "prior" in entry:
                result[str(entry["name"])] = entry
    return result


def prior_signature(entry: dict[str, Any]) -> tuple[str, str, str]:
    prior = entry.get("prior", {})
    if not isinstance(prior, dict):
        return (str(entry.get("scale", "")), "", "")
    if prior.get("type") != "uniform":
        return (str(entry.get("scale", "")), str(prior.get("type", "")), "")
    return (
        str(entry.get("scale", "")),
        f"{float(prior['lower']):g}",
        f"{float(prior['upper']):g}",
    )


def common_prior_rows(config_dir: Path) -> tuple[list[str], list[tuple[str, str, str, str]]]:
    configs = [(path.stem, fitted_entries(load_toml(path))) for path in sorted(config_dir.glob("*.toml"))]
    if not configs:
        raise ValueError(f"No TOMLs in {config_dir}")
    events = [event for event, _ in configs]
    names = sorted(set.intersection(*(set(entries) for _, entries in configs)))
    rows: list[tuple[str, str, str, str]] = []
    for name in names:
        signatures = {prior_signature(entries[name]) for _, entries in configs}
        if len(signatures) == 1:
            scale, lower, upper = signatures.pop()
            rows.append((name, scale, lower, upper))
    return events, rows


def special_cases(config_dir: Path) -> list[str]:
    notes: list[str] = []
    for path in sorted(config_dir.glob("*.toml")):
        config = load_toml(path)
        entries = fitted_entries(config)
        rv = entries.get("rv_milky_way", {}).get("prior", {})
        if isinstance(rv, dict) and rv.get("type") == "milkywayrv":
            foreground = next(
                (
                    entry.get("value")
                    for entry in config.get("extinction", [])
                    if isinstance(entry, dict) and entry.get("name") == "ebv_milky_way"
                ),
                None,
            )
            suffix = "" if foreground is None else f" with fixed `E(B-V)_MW={float(foreground):g}` mag"
            notes.append(f"`{path.stem}` uses the dedicated Milky-Way `R_V` prior{suffix}.")
        offsets = []
        for name in ("F775W_offset", "F125W_offset"):
            prior = entries.get(name, {}).get("prior", {})
            if isinstance(prior, dict) and prior.get("type") == "gaussian":
                offsets.append(f"`{name}` (Gaussian sigma={float(prior['sigma']):g} mag)")
        if offsets:
            notes.append(f"`{path.stem}` retains HST filter offsets: {', '.join(offsets)}.")
    return notes


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def table(rows: list[tuple[str, ...]], headers: tuple[str, ...]) -> str:
    body = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    body.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(body)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--share-campaign", required=True)
    parser.add_argument(
        "--share-output-dir",
        type=Path,
        help="Optional shared campaign directory that receives the same documentation files.",
    )
    parser.add_argument("--sampler", required=True)
    parser.add_argument("--resolution", required=True)
    parser.add_argument("--mode", default="posterior-cloud thawed-parameter")
    parser.add_argument(
        "--campaign-purpose",
        default="Final robustness sampling from accepted event-specific solution families.",
        help="One-sentence scientific purpose stored with the campaign.",
    )
    parser.add_argument(
        "--abstract",
        default="",
        help="Meeting-book abstract stored verbatim in campaign metadata; defaults to an informative summary.",
    )
    parser.add_argument(
        "--seed-source-campaign",
        default="",
        help="Share-relative or absolute source campaign used to construct the initial ensemble.",
    )
    parser.add_argument(
        "--seeding-method",
        default="",
        help="Explicit initial-ensemble method, e.g. minimized center plus Gaussian posterior-width cloud.",
    )
    parser.add_argument("--metadata-name", default="campaign_metadata.json")
    parser.add_argument("--full-report-name", default="CAMPAIGN_METHOD_REPORT.md")
    parser.add_argument("--readme-name", default="README.md")
    args = parser.parse_args()

    events, priors = common_prior_rows(args.config_dir)
    manifest = read_manifest(args.manifest)
    if set(events) != {row["event"] for row in manifest}:
        raise ValueError("The config directory and dispatch manifest do not contain the same events")
    args.campaign_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).strftime("%Y-%m-%d")
    common_table = table(priors, ("Fitted quantity", "Scale", "Lower", "Upper / prior"))
    state_counts = Counter(row["host"] for row in manifest)
    manifest_by_event = {row["event"]: row for row in manifest}
    highres_080413 = manifest_by_event.get("080413B")
    if highres_080413 is None:
        highres_080413_note = "`080413B` is not part of this manifest."
    elif highres_080413["host"].startswith("blocked"):
        highres_080413_note = (
            "`080413B` remains blocked until its separate high-resolution standard "
            "final-seeded run is complete, postprocessed and published, then converted "
            "into and preflighted as a final-final posterior cloud."
        )
    else:
        launched = highres_080413.get("launched_utc", "")
        launch_text = f" (launched {launched})" if launched else ""
        highres_080413_note = (
            "`080413B` satisfied its high-resolution standard-final-seeded prerequisite "
            f"and is assigned to `{highres_080413['host']}` for final-final sampling{launch_text}."
        )
    queue_rows = [
        (row["queue_order"], row["event"], row["host"], row.get("workers", ""))
        for row in sorted(manifest, key=lambda item: int(item["queue_order"]))
    ]
    queue_table = table(queue_rows, ("Order", "Event", "Current dispatch state", "Workers"))
    special = special_cases(args.config_dir)
    special_text = "\n".join(f"- {note}" for note in special) or "- No configuration-specific exceptions detected."
    share_output_arg = ""
    if args.share_output_dir is not None:
        share_output_arg = f"  --share-output-dir {args.share_output_dir} \\\n"

    default_seed_method = (
        "The initial ensemble is constructed from the specified source campaign; "
        "the source is used only for initialization and does not alter the new likelihood or priors."
    )
    seed_method = args.seeding_method.strip() or default_seed_method
    source_campaign = args.seed_source_campaign.strip() or "Not recorded at setup."
    default_abstract = (
        f"{args.campaign_purpose} This campaign is seeded from {source_campaign}. "
        f"Initialization method: {seed_method}"
    )
    abstract = args.abstract.strip() or default_abstract
    metadata = {
        "title": args.title,
        "purpose": args.campaign_purpose,
        "abstract": abstract,
        "seed_source_campaign": source_campaign,
        "seeding_method": seed_method,
        "mode": args.mode,
        "sampler": args.sampler,
        "resolution": args.resolution,
        "share_campaign": args.share_campaign,
        "created_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    readme = f"""# {args.title}

## Quick Look

- **Purpose:** {args.campaign_purpose}
- **Events:** {len(events)}. **Mode:** {args.mode}.
- **Sampler:** {args.sampler}.
- **Resolution:** {args.resolution}.
- **Seed source campaign:** `{source_campaign}`.
- **Initialization:** {seed_method}
- **Products:** Lyra is the sole publisher to `{args.share_campaign}`.
- **Completion protocol:** every validated event receives a fixed-solution numerical-resolution ladder, publication-ready post-fit figures, and an immediate refresh of the partial campaign meeting book. No report waits for an unrelated slow GRB.

## Shared Fitted-Prior Bounds

{common_table}

`s` is deliberately thawed: its prior stays broad while initialization is near the prior fixed value. See `CAMPAIGN_METHOD_REPORT.md` for rationale, safeguards, event status, data exceptions, and reproducibility details.

## Configuration Exceptions

{special_text}
"""

    full = f"""# {args.title}: Method and Operations Report

- **Generated:** {now}
- **Canonical configuration directory:** `{args.config_dir}`
- **Dispatch manifest:** `{args.manifest}`
- **Publication destination:** `{args.share_campaign}`

## 1. Scientific Purpose

This is a final robustness campaign, not a blind rediscovery run. The preceding final-seeded fits established event-specific physical solution families. We now retain the same likelihood and data choices, widen the agreed parameter domain, and thaw the structured-jet shape parameter `s`. This directly tests whether holding `s=4` made the reported uncertainties for energy, geometry, and microphysics artificially small.

**Campaign abstract:** {abstract}

The relevant meeting record is the current `GRB_Tracking` sheet notes: it calls for a thawed-`s` test where unusually tight viewing-angle constraints or off-axis numerical structure require a robustness check. High-density/inverted-profile cases also motivated the wider density domain and the explicit numerical-resolution audit.

## 2. Prior Domain

The table below is read from every canonical campaign TOML. Bounds are expressed in the fitted coordinates: a `log` scale means the listed bounds are base-10 logarithms of the physical quantity.

{common_table}

Interpretation details:

- `E_j_core_52` is the two-sided core kinetic afterglow energy in units of `10^52 erg`; `[-4, 2]` therefore spans `10^48`--`10^54 erg`.
- `Gamma_0_core_avg` is the core-averaged initial Lorentz factor; its log bounds correspond to 50--100000.
- `n017` is the power-law density normalization in the existing `10^17 cm` convention. The `[-6,10]` domain retains the agreed `10^10` upper ceiling while extending the lower limit.
- `theta_c` and `theta_v` are sampled in log radians. The plots must label those coordinates as logarithmic.
- `s` is now fitted over its full agreed physical test range; its broad prior, rather than its initialization width, defines the inference domain.
- Source-frame `E(B-V)` spans 0--1 mag. Milky-Way foreground treatment remains event-specific.

## 3. Posterior-Cloud Initialization Without Double Counting

For each approved event, the initial ensemble is built by drawing distinct, finite, cold-chain samples jointly from the validated final-seeded posterior. This preserves previously measured correlations among shared fitted parameters. The newly free `s` coordinate is initialized near the formerly fixed canonical value `s=4` with a compact truncated cloud, while its actual fitted prior remains broad.

The source posterior is used **only** to choose valid starting points. It is not multiplied into the new likelihood and it does not replace any prior. Consequently the final-final posterior is governed by the new run's likelihood, stated priors, burn-in, and retained production samples. This makes the run an efficient continuation/robustness measurement rather than an accidental double use of the data.

## 4. Sampler and Numerical Model

- **Sampler:** {args.sampler}.
- **Resolution:** {args.resolution}.
- The angular and time values are adaptive VegasAfterglow resolution controls in the existing per-degree, per-degree, and per-log10-time-decade convention. They are not literal fixed Cartesian grid-cell counts; radial accuracy is handled by the adaptive engine.
- The moderate setting increases base azimuthal/time resolution relative to the ordinary engine defaults while retaining the established polar resolution. It was selected to address mild off-axis light-curve and cooling-frequency oscillations without making every run prohibitively slow.
- Every launch performs the ordinary one-step numerical preflight and requires valid posterior evaluations for all temperatures and walkers before production.

## 5. Per-Event Numerical Resolution and Meeting-Book Protocol

After each MCMC run finishes, Lyra pulls the final checkpoint, minimizes it, generates the ordinary post-fit products, and validates the result before publication. Completion is not accepted unless the event has a fixed-minimized-solution VegasAfterglow resolution ladder containing the modeled-flux table, resolution summary, light-curve overlay, primary signed-convergence panel, and its PDF/PNG companions.

The coupled ladder varies azimuthal, polar, and time controls together relative to the production grid, from coarser through at least three finer levels. It also includes one-control refinements/coarsenings of each coordinate. The production grid is the zero-reference for signed flux and fit-statistic differences; the finest grid is a resolution reference, not a zero by definition. Runtime panels scale the actual recorded production MCMC wall clock by the fixed-model cost ratio, with cross-host estimates normalized only by the standard worker counts (Pauley 8, PCRC 16).

The watcher immediately rebuilds the campaign comparisons and LaTeX/PDF meeting book after every newly validated event. Only validated, published event folders are included, so incomplete runs cannot appear as finished. Figure provenance remains in the manifest, machine-readable metadata, and campaign path; routine figures omit run-folder/source-file footers so their artwork is suitable for review and later publication.

## 6. Event-Specific Scientific Safeguards

{special_text}

- `220101A` must retain native HST `F775W`/`F125W` data and its intended early X-ray points; the event runner verifies this before launch.
- `221009A` must use the Milky-Way `R_V` treatment because its foreground reddening is large; the builder and runner both enforce it.
- `111228A` requires explicit review of its swept-mass and numerical-resolution diagnostics before physical interpretation; this is a scientific quality-control requirement, not a reason to suppress otherwise valid post-fit products.
- {highres_080413_note}

## 7. Scheduling and Reproducibility

The manifest is the single source of truth for event ownership. The first approved event, `160131A`, is intentionally marked `queued-lyra-first`; it must be changed only to `pending-lyra` at explicit launch. Once it is recorded on Lyra, the dispatcher excludes Lyra from subsequent MCMC assignments, reserving it for serial scientific work.

Lyra owns result retrieval, minimization, post-fit diagnostics, validation, and publication. A single Lyra watcher publishes to the dated campaign directory above, preventing competing Google Drive clients from creating duplicate event folders. The watcher ignores queued, pending, and blocked manifest markers rather than treating them as SSH hosts.

{queue_table}

Current manifest-state counts: {', '.join(f'`{state}`: {count}' for state, count in sorted(state_counts.items()))}.

## 8. Validation and Interpretation Requirements

1. Inspect traces, swap behavior, and first-versus-second-half production intervals before quoting final uncertainties.
2. Retain all finite terminal cold-chain walkers for walker-curve diagnostics. Density-profile and swept-mass products are configured to show all available terminal walkers; corner/scatter render caps are display choices, not discarded inference samples.
3. Keep numerical diagnostics visible. NaNs, boundary contact, or oscillatory light curves are scientific/numerical findings to investigate, not artifacts to hide.
4. Compare fixed-`s` and thawed-`s` results event by event. A broad or weakly correlated `s` posterior means the data do not strongly constrain it; it does not by itself prove `s` is physically irrelevant.
5. Record the exact data inclusion decisions and any event-specific branch selection with each published product. Those decisions are needed for the eventual paper.
6. Treat the numerical ladder as a convergence diagnostic, not a refit. Its fixed minimized parameters isolate numerical-resolution sensitivity from posterior variation; any material production-grid discrepancy should trigger scientific review before results are quoted.

## 9. Regeneration

Regenerate these two files after changing the config directory, manifest, sampler settings, or campaign design:

```bash
/Users/jkeohane/GRBs/.venv/bin/python VegasJetFit/scripts/write_campaign_documentation.py \\
  --campaign-dir {args.campaign_dir} \\
  --config-dir {args.config_dir} \\
  --manifest {args.manifest} \\
  --title '{args.title}' \\
  --share-campaign '{args.share_campaign}' \\
{share_output_arg}  --sampler '{args.sampler}' \\
  --resolution '{args.resolution}' \\
  --mode '{args.mode}'
```
"""

    (args.campaign_dir / args.readme_name).write_text(readme)
    (args.campaign_dir / args.full_report_name).write_text(full)
    (args.campaign_dir / args.metadata_name).write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"WROTE {args.campaign_dir / args.readme_name}")
    print(f"WROTE {args.campaign_dir / args.full_report_name}")
    print(f"WROTE {args.campaign_dir / args.metadata_name}")
    if args.share_output_dir is not None:
        args.share_output_dir.mkdir(parents=True, exist_ok=True)
        (args.share_output_dir / args.readme_name).write_text(readme)
        (args.share_output_dir / args.full_report_name).write_text(full)
        (args.share_output_dir / args.metadata_name).write_text(json.dumps(metadata, indent=2) + "\n")
        print(f"WROTE {args.share_output_dir / args.readme_name}")
        print(f"WROTE {args.share_output_dir / args.full_report_name}")
        print(f"WROTE {args.share_output_dir / args.metadata_name}")


if __name__ == "__main__":
    main()
