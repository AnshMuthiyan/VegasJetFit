#!/usr/bin/env python3
"""Compute AMRVAC log-grid parameters for the pressure-grid BoOST campaign."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


PLAN_CSV = Path(__file__).resolve().with_name("integrated_boost_pressure_grid_plan.csv")

BLOCK_NX = 8
BLOCK_GROUP = 2
CELLS_PER_DECADE = 80
INNER_RT_FRACTION_DEFAULT = 0.2
# Empirically safer inner-domain cuts for high-pressure slices.
# Keep p4 at the original 0.2*Rt, but trim deeper inner wind for p5/p6.
INNER_RT_FRACTION_BY_PRESSURE = {
    5: 0.3,
    6: 0.3,
}


def fmt_fortran(value: float) -> str:
    return f"{value:.16e}".replace("e", "d")


def ceil_block(value: float) -> int:
    """Round up so AMRVAC has an even number of level-1 blocks."""
    quantum = BLOCK_NX * BLOCK_GROUP
    return int(math.ceil(value / quantum) * quantum)


def load_rows() -> list[dict[str, str]]:
    with PLAN_CSV.open(newline="") as handle:
        return list(csv.DictReader(handle))


def pressure_exponent_from_run_id(run_id: str) -> int:
    # run_id pattern is p{pressure_exp}_n{density_exp}, e.g. p6_n21.
    return int(run_id.split("_", 1)[0][1:])


def inner_rt_fraction_for_run(run_id: str) -> float:
    p_exp = pressure_exponent_from_run_id(run_id)
    return INNER_RT_FRACTION_BY_PRESSURE.get(p_exp, INNER_RT_FRACTION_DEFAULT)


def derived(row: dict[str, str]) -> dict[str, object]:
    rwind = float(row["rwind_pc"])
    rt = float(row["rt_external_pc"])
    inner_rt_fraction = inner_rt_fraction_for_run(row["run_id"])
    xmin = inner_rt_fraction * rt
    xmax = float(row["xprobmax1_pc"])
    span_decades = math.log10(xmax / xmin)
    domain_nx = ceil_block(CELLS_PER_DECADE * span_decades)
    q = (xmax / xmin) ** (1.0 / domain_nx)
    return {
        **row,
        "inner_rt_fraction": inner_rt_fraction,
        "xprobmin1_pc": xmin,
        "domain_nx1": domain_nx,
        "block_nx1": BLOCK_NX,
        "cells_per_decade": CELLS_PER_DECADE,
        "span_decades": span_decades,
        "q_base": q,
        "dx_first_pc": xmin * (q - 1.0),
        "cells_to_rwind": math.log(rwind / xmin) / math.log(q),
        "cells_to_rt": math.log(rt / xmin) / math.log(q),
        "rho_fortran": fmt_fortran(float(row["rho_g_cm3"])),
        "tism_fortran": fmt_fortran(float(row["tism_k"])),
        "rwind_fortran": fmt_fortran(rwind),
        "rt_fortran": fmt_fortran(rt),
        "xmin_fortran": fmt_fortran(xmin),
        "xmax_fortran": fmt_fortran(xmax),
    }


def shell(row: dict[str, object]) -> str:
    keys = [
        "run_id",
        "pressure_k_cm3",
        "rho_g_cm3",
        "nism_cm3",
        "tism_k",
        "rt_external_pc",
        "rb_effective_pc",
        "rwind_pc",
        "inner_rt_fraction",
        "xprobmin1_pc",
        "xprobmax1_pc",
        "domain_nx1",
        "cells_per_decade",
        "span_decades",
        "q_base",
        "dx_first_pc",
        "cells_to_rwind",
        "cells_to_rt",
        "rho_fortran",
        "tism_fortran",
        "rwind_fortran",
        "rt_fortran",
        "xmin_fortran",
        "xmax_fortran",
    ]
    lines = []
    for key in keys:
        value = row[key]
        lines.append(f"{key}={str(value)!r}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", nargs="?")
    parser.add_argument("--shell", action="store_true")
    parser.add_argument("--csv", action="store_true")
    args = parser.parse_args()

    rows = [derived(row) for row in load_rows()]
    if args.csv:
        writer = csv.DictWriter(
            __import__("sys").stdout,
            fieldnames=[
                "run_id",
                "pressure_k_cm3",
                "rho_g_cm3",
                "nism_cm3",
                "tism_k",
                "rt_external_pc",
                "rb_effective_pc",
                "rwind_pc",
                "inner_rt_fraction",
                "xprobmin1_pc",
                "xprobmax1_pc",
                "domain_nx1",
                "cells_per_decade",
                "span_decades",
                "q_base",
                "dx_first_pc",
                "cells_to_rwind",
                "cells_to_rt",
            ],
        )
        writer.writeheader()
        writer.writerows({key: row[key] for key in writer.fieldnames} for row in rows)
        return 0

    if not args.run_id:
        raise SystemExit("run_id is required unless --csv is used")

    for row in rows:
        if row["run_id"] == args.run_id:
            print(shell(row) if args.shell else row)
            return 0
    raise SystemExit(f"unknown run_id: {args.run_id}")


if __name__ == "__main__":
    raise SystemExit(main())
