#!/usr/bin/env python3
"""Clean the VegasGRBruns share root after fit reorganization.

Run from a project Python environment:

    /Users/jkeohane/GRBs/.venv/bin/python scripts/clean_share_root.py <share_root>

The goal is a human-readable science workspace. Useful products are moved into
named folders. Ambiguous, old, or duplicate material is moved under `trash/`.
"""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path


def unique_dest(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    i = 2
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def move_file(root: Path, src_name: str, dst_rel: str, moves: list[str]) -> None:
    src = root / src_name
    if not src.exists():
        return
    dst = unique_dest(root / dst_rel)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    moves.append(f"{src_name} -> {dst.relative_to(root)}")


def move_dir(root: Path, src_name: str, dst_rel: str, moves: list[str]) -> None:
    src = root / src_name
    if not src.exists():
        return
    dst = unique_dest(root / dst_rel)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    moves.append(f"{src_name}/ -> {dst.relative_to(root)}/")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def clean(root: Path) -> list[str]:
    moves: list[str] = []
    generated = datetime.now().isoformat(timespec="seconds")

    for name in [".DS_Store"]:
        p = root / name
        if p.exists():
            p.unlink()
            moves.append(f"deleted {name}")

    move_file(root, "GRB Tracking.gsheet", "Tracking/GRB_Tracking.gsheet", moves)
    move_file(root, "GRB Tracking - Column C Paste.tsv", "Tracking/exports/GRB_Tracking_Column_C_Paste.tsv", moves)
    move_file(root, "GRB Tracking - Column C Paste (Short).tsv", "Tracking/exports/GRB_Tracking_Column_C_Paste_Short.tsv", moves)
    move_file(root, "GRB Tracking - Column C Updates.csv", "Tracking/exports/GRB_Tracking_Column_C_Updates.csv", moves)
    move_file(root, "GRB Tracking - Column C Updates (Short).csv", "Tracking/exports/GRB_Tracking_Column_C_Updates_Short.csv", moves)

    for name in [
        "GRB_fit_summary.xlsx",
        "GRB_fit_summary_all_runs.csv",
        "GRB_fit_summary_best_per_grb.csv",
        "GRB_fit_summary_simple.csv",
        "GRB_fit_summary_simple.xlsx",
        "ansh_style_all15_summary.csv",
    ]:
        move_file(root, name, f"Tables/fit_summaries/{name}", moves)

    for name in [
        "Dylan_SBPL_Run_Status_dylan_sbpl_init5pct_2000x2000_v1.csv",
        "Dylan_SBPL_Run_Status_dylan_sbpl_init5pct_2000x2000_v1.xlsx",
        "Dylan_SBPL_Run_Status_thetacfree_dylan_sbpl_init5pct_2000x2000_v1.csv",
        "Dylan_SBPL_Run_Status_thetacfree_dylan_sbpl_init5pct_2000x2000_v1.xlsx",
        "NegativeK_Bubble_Run_Status.csv",
        "NegativeK_Bubble_Run_Status.xlsx",
        "SBPL_Empirical_Bubble_Run_Status_empirical_bubble_tophat_theta1p0_dylanspec_sbplseed_v1.csv",
        "SBPL_Empirical_Bubble_Run_Status_empirical_bubble_tophat_theta1p0_dylanspec_sbplseed_v1.xlsx",
        "Thesis_Reproduction_Run_Status_theta1p0_thesis_reproduction_dylanphyspriors_init5pct_2000x2000_v1.csv",
        "Thesis_Reproduction_Run_Status_theta1p0_thesis_reproduction_dylanphyspriors_init5pct_2000x2000_v1.xlsx",
        "Thesis_Reproduction_Run_Status_theta1p0_thesis_reproduction_median10sig_2000x2000_v1.csv",
        "Thesis_Reproduction_Run_Status_theta1p0_thesis_reproduction_median10sig_2000x2000_v1.xlsx",
        "Thesis_Reproduction_Run_Status_theta1p0_thesis_reproduction_median5sig_2000x2000_v1.csv",
        "Thesis_Reproduction_Run_Status_theta1p0_thesis_reproduction_median5sig_2000x2000_v1.xlsx",
        "Thesis_Reproduction_Run_Status_theta1p0_thesis_reproduction_recentered10sig_2000x2000_v1.csv",
        "Thesis_Reproduction_Run_Status_theta1p0_thesis_reproduction_recentered10sig_2000x2000_v1.xlsx",
        "Tophat_DylanSpectrum_Run_Status.csv",
        "Tophat_DylanSpectrum_Run_Status.xlsx",
        "Tophat_DylanSpectrum_Run_Status_160131A.csv",
        "Tophat_DylanSpectrum_Run_Status_160131A.xlsx",
        "Tophat_DylanSpectrum_Run_Status_seeded_v2.csv",
        "Tophat_DylanSpectrum_Run_Status_seeded_v2.xlsx",
    ]:
        move_file(root, name, f"Tables/run_status/{name}", moves)

    for name in [
        "k_compare_thesis_vs_short.pdf",
        "k_compare_thesis_vs_short.png",
        "p_compare_thesis_vs_short.pdf",
        "p_compare_thesis_vs_short.png",
        "221009A grid overview.png",
    ]:
        move_file(root, name, f"Figures/diagnostics/{name.replace(' ', '_')}", moves)
    move_file(root, "To_do_List_2026_05_13.jpg", "Figures/meeting_notes/To_do_List_2026_05_13.jpg", moves)

    move_file(root, "README_structure.txt", "trash/old_readmes/README_structure.txt", moves)
    move_file(root, "ansh_style.tar", "trash/old_archives/ansh_style.tar", moves)
    move_file(root, "reports.tar", "trash/old_archives/reports.tar", moves)
    move_dir(root, "VegasGRBruns", "trash/empty_or_duplicate_dirs/VegasGRBruns", moves)
    move_dir(root, "_legacy_unorganized", "trash/legacy_unorganized_20260521", moves)

    write_text(
        root / "Tracking" / "README.md",
        """# Tracking

Current collaboration and meeting-tracking files live here.

`GRB_Tracking.gsheet` is the primary tracking sheet. The `exports/` directory
contains small paste/update files derived from that sheet.
""",
    )
    write_text(
        root / "Tables" / "README.md",
        """# Tables

`fit_summaries/` contains compact comparison tables across GRBs and campaigns.

`run_status/` contains generated status tables from specific campaigns. These
are useful snapshots, while `../Fits/run_registry.csv` is the current organized
fit registry.
""",
    )
    write_text(
        root / "Figures" / "README.md",
        """# Figures

`diagnostics/` contains comparison and diagnostic figures.

`meeting_notes/` contains photographed or scanned planning notes that are useful
historically but are not primary fit products.
""",
    )
    write_text(
        root / "trash" / "README.md",
        f"""# Trash

Created: `{generated}`

This folder holds stale, ambiguous, duplicate, or legacy material moved out of
the main science-facing tree. The share directory was backed up to
`/Volumes/Science_Data` before this cleanup, so material here is not treated as
the authoritative working copy.
""",
    )
    write_text(
        root / "CLEANUP_LOG_20260521.md",
        "# Cleanup Log: 2026-05-21\n\n"
        "The share root was reorganized so the top-level folders are science-facing.\n"
        "Useful products were sorted into `Fits/`, `Data_Products/`, `Tables/`,\n"
        "`Figures/`, `Tracking/`, `Model_Comparisons/`, `Reports/`, and `Literature/`.\n"
        "Ambiguous or stale material was moved to `trash/`.\n\n"
        "## Moves\n\n"
        + "\n".join(f"- `{m}`" for m in moves)
        + "\n",
    )
    return moves


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("share_root", type=Path)
    args = parser.parse_args()
    moves = clean(args.share_root.expanduser().resolve())
    print(f"Completed {len(moves)} cleanup actions")
    for move in moves:
        print(move)


if __name__ == "__main__":
    main()
