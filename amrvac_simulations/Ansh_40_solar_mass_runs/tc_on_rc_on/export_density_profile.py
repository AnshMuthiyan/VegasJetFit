# Purpose: Export a tc_on_rc_on native checkpoint as a density-only log plot with top radius scale, minor vertical grid lines, and optional CSV.
import argparse
import csv
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "SkynetVMTesting"))
from plot_dat_folder import read_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--par", type=Path)
    parser.add_argument("--output", type=Path, help="Output directory; default: reuse the snapshot folder's existing output directory")
    parser.add_argument("--rmax", type=float, help="Optional upper plot radius in pc; CSV always contains every active cell")
    parser.add_argument("--plot-only", action="store_true", help="Create only the density plot, without a CSV")
    args = parser.parse_args()
    if args.output is None:
        data_folder = args.snapshot.resolve().parent
        args.output = next((data_folder / name for name in ("OUTPUT files", "output", "plots")
                            if (data_folder / name).is_dir()), data_folder if data_folder.name == "output" else data_folder / "output")
    info = read_snapshot(args.snapshot, args.par)
    cells = info["cells"]
    if any(not math.isfinite(cell[2]) or cell[2] <= 0 for cell in cells):
        raise ValueError("Snapshot contains invalid densities; refusing to export a misleading profile")
    args.output.mkdir(parents=True, exist_ok=True)
    csv_path = args.output / f"{args.snapshot.stem}_density_profile.csv"
    if not args.plot_only:
        with csv_path.open("w", newline="") as stream:
            stream.write(f"# Purpose: Full active-cell mass-density profile of tc_on_rc_on/{args.snapshot.name}; radius in pc, density in g/cm^3.\n")
            writer = csv.writer(stream)
            writer.writerow(["radius_pc", "density_g_cm3", "r_inner_pc", "r_outer_pc"])
            for left, right, density, *_ in cells:
                writer.writerow([format(value, ".17g") for value in ((left + right) / 2, density, left, right)])

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import LogLocator, NullFormatter

    fig, ax = plt.subplots(figsize=(9, 5.5), layout="constrained")
    try:
        edges = [cells[0][0]] + [cell[1] for cell in cells]
        ax.stairs([cell[2] for cell in cells], edges, baseline=None, color="#24668e", linewidth=1.5)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.xaxis.set_minor_locator(LogLocator(base=10, subs=range(2, 10)))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.tick_params(axis="x", which="both", top=True, bottom=True, labeltop=True, labelbottom=True)
        ax.set_xlim(left=edges[0], right=edges[-1] if args.rmax is None else args.rmax)
        ax.set_xlabel("Radius [pc]")
        ax.xaxis.set_label_position("top")
        ax.set_ylabel(r"Mass density $\rho$ [g cm$^{-3}$]")
        title = f"Conduction on, cooling on | {args.snapshot.stem} | age = {info['age_years'] / 1e6:.6f} Myr"
        if info["invalid_cells"]:
            title += f"\n{info['invalid_cells']} cells have invalid thermal states"
        ax.set_title(title, fontsize=11)
        ax.grid(True, which="major", alpha=0.25)
        ax.grid(True, axis="x", which="minor", alpha=0.2, linewidth=0.6)
        png_path = args.output / f"{args.snapshot.stem}_density_profile.png"
        fig.savefig(png_path, dpi=200, metadata={
            "Title": f"tc_on_rc_on {args.snapshot.stem} density profile",
            "Description": "Purpose: Show the saved density with logarithmic axes, top radius scale, and minor vertical grid lines.",
        })
    finally:
        plt.close(fig)
    print(f"Snapshot: {args.snapshot}")
    print(f"Age: {info['age_years']:.12g} yr; iteration: {info['iteration']}; active cells: {len(cells)}; invalid cells: {info['invalid_cells']}")
    print(f"Grid: {info['grid']}")
    print(f"Radius range: {cells[0][0]:.12g} to {cells[-1][1]:.12g} pc")
    print(f"Plot: {png_path}")
    if not args.plot_only:
        print(f"CSV: {csv_path}")


if __name__ == "__main__":
    main()
