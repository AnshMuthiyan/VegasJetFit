#!/usr/bin/env python3
"""
Build a pressure-grid AMRVAC plan from integrated BoOST bubble radii.

The input is boost_integrated_weaver_radii.csv, produced by
plot_boost_integrated_weaver_bubble.py.  The grid uses the pressure-confined
death-time radii:

  R_t = rt_external_pressure_pc
  R_b = rb_effective_pc = min(R_b,Weaver, R_b,pressure equilibrium)

For numerical robustness:

  Rwind = 0.1 R_t
  xprobmin = 0.02 R_t
  dx <= Rwind / cells_across_rwind
  xprobmax = outer_pad * R_b

This keeps the first cell center well inside R_t and places the outer boundary
well beyond the bubble wall.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


BLOCK_NX1 = 8


def block_ceil(value: float, block: int = BLOCK_NX1) -> int:
    return max(block, int(math.ceil(value / block) * block))


def build_plan(
    rows: list[dict[str, str]],
    outer_pad: float,
    rwind_fraction_rt: float,
    xprobmin_fraction_rt: float,
    cells_across_rwind: float,
) -> list[dict[str, object]]:
    plan = []
    for row in rows:
        rt_pc = float(row["rt_external_pressure_pc"])
        rb_pc = float(row["rb_effective_pc"])
        rwind_pc = rwind_fraction_rt * rt_pc
        xprobmin_pc = xprobmin_fraction_rt * rt_pc
        xprobmax_pc = outer_pad * rb_pc
        dx_target_pc = rwind_pc / cells_across_rwind
        n_cells_raw = (xprobmax_pc - xprobmin_pc) / dx_target_pc
        domain_nx1 = block_ceil(n_cells_raw)
        dx_actual_pc = (xprobmax_pc - xprobmin_pc) / domain_nx1
        first_cell_center_pc = xprobmin_pc + 0.5 * dx_actual_pc
        cells_inside_rwind = max((rwind_pc - xprobmin_pc) / dx_actual_pc, 0.0)
        cells_inside_rt = max((rt_pc - xprobmin_pc) / dx_actual_pc, 0.0)
        plan.append(
            {
                "run_id": row["run_id"],
                "pressure_exponent": int(row["pressure_exponent"]),
                "density_exponent": int(row["density_exponent"]),
                "pressure_k_cm3": float(row["pressure_k_cm3"]),
                "rho_g_cm3": float(row["rho_g_cm3"]),
                "nism_cm3": float(row["nism_cm3"]),
                "tism_k": float(row["tism_k"]),
                "rt_external_pc": rt_pc,
                "rb_weaver_pc": float(row["rb_weaver_pc"]),
                "rb_pressure_equilibrium_pc": float(row["rb_pressure_equilibrium_pc"]),
                "rb_effective_pc": rb_pc,
                "rwind_pc": rwind_pc,
                "xprobmin1_pc": xprobmin_pc,
                "xprobmax1_pc": xprobmax_pc,
                "outer_pad": outer_pad,
                "rb_box_fraction": rb_pc / xprobmax_pc,
                "dx_target_pc": dx_target_pc,
                "dx_actual_pc": dx_actual_pc,
                "domain_nx1": domain_nx1,
                "first_cell_center_pc": first_cell_center_pc,
                "first_cell_center_over_rt": first_cell_center_pc / rt_pc,
                "cells_inside_rwind": cells_inside_rwind,
                "cells_inside_rt": cells_inside_rt,
                "pressure_confined": row["pressure_confined"],
            }
        )
    return plan


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_readme(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    max_nx = max(int(row["domain_nx1"]) for row in rows)
    min_first = min(float(row["first_cell_center_over_rt"]) for row in rows)
    max_first = max(float(row["first_cell_center_over_rt"]) for row in rows)
    min_rwind_cells = min(float(row["cells_inside_rwind"]) for row in rows)
    min_rt_cells = min(float(row["cells_inside_rt"]) for row in rows)
    with path.open("w") as handle:
        handle.write("# Integrated BoOST Pressure-Grid Plan\n\n")
        handle.write("This plan sizes the AMRVAC domain from the integrated BoOST wind history at stellar death.\n\n")
        handle.write("Rules:\n")
        handle.write("- `R_t = rt_external_pressure_pc`, from wind ram pressure balance with the imposed external pressure.\n")
        handle.write("- `R_b = rb_effective_pc = min(R_b,Weaver, R_b,pressure equilibrium)`.\n")
        handle.write("- `Rwind = 0.1 R_t`.\n")
        handle.write("- `xprobmin1 = 0.02 R_t`.\n")
        handle.write("- `xprobmax1 = 4 R_b`, so the bubble wall is targeted at one quarter of the box radius.\n")
        handle.write("- `dx <= Rwind / 10`, rounded to an AMRVAC block multiple of 8 cells.\n\n")
        handle.write("Diagnostics:\n")
        handle.write(f"- max `domain_nx1`: {max_nx}\n")
        handle.write(f"- first-cell-center / R_t range: {min_first:.4f} to {max_first:.4f}\n")
        handle.write(f"- minimum cells inside Rwind: {min_rwind_cells:.2f}\n")
        handle.write(f"- minimum cells inside R_t: {min_rt_cells:.2f}\n\n")
        handle.write("The previous preliminary grid failed because `Rwind=0.2 pc` and `xprobmin1=0.19 pc` put the first cell center outside the wind source in most runs. This plan avoids that failure mode.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--radii-csv",
        default="/Users/jkeohane/GRBs/VegasJetFit/reports/amrvac_pressure_grid_prelim_20260424/boost_integrated_weaver_radii.csv",
    )
    parser.add_argument(
        "--output-csv",
        default="/Users/jkeohane/GRBs/GRBs_old/Code/amrvac_runs/Boost_Test_runs_2026_04_24_pressure_grid_integrated_boost_plan/integrated_boost_pressure_grid_plan.csv",
    )
    parser.add_argument(
        "--readme",
        default="/Users/jkeohane/GRBs/GRBs_old/Code/amrvac_runs/Boost_Test_runs_2026_04_24_pressure_grid_integrated_boost_plan/README.md",
    )
    parser.add_argument("--outer-pad", type=float, default=4.0)
    parser.add_argument("--rwind-fraction-rt", type=float, default=0.1)
    parser.add_argument("--xprobmin-fraction-rt", type=float, default=0.02)
    parser.add_argument("--cells-across-rwind", type=float, default=10.0)
    args = parser.parse_args()

    with Path(args.radii_csv).open(newline="") as handle:
        radii_rows = list(csv.DictReader(handle))
    plan = build_plan(
        radii_rows,
        outer_pad=args.outer_pad,
        rwind_fraction_rt=args.rwind_fraction_rt,
        xprobmin_fraction_rt=args.xprobmin_fraction_rt,
        cells_across_rwind=args.cells_across_rwind,
    )
    write_csv(plan, Path(args.output_csv))
    write_readme(plan, Path(args.readme))
    print(f"Wrote {args.output_csv}")
    print(f"Wrote {args.readme}")


if __name__ == "__main__":
    main()
