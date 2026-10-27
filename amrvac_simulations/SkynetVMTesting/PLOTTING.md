<!-- Purpose: Explain how to plot every native AMRVAC snapshot in a chosen folder on Linux or Windows. -->

# Plot a folder of checkpoints

Copy `plot_dat_folder.py` to the VM or run it on downloaded results. Install
Matplotlib for that Python interpreter (no sudo needed):

```sh
python3 -m pip install --user matplotlib
```

Plot every `.dat` snapshot directly inside a folder:

```sh
python3 plot_dat_folder.py /path/to/output
```

One four-panel image per snapshot is saved in `/path/to/output/plots/`:
mass density (g/cm^3), radial velocity (km/s), thermal pressure (erg/cm^3), and
temperature (K), versus radius (pc). Titles include stellar age and iteration.
Density, pressure, and temperature use logarithmic vertical axes.
All individual and overlaid plots show the **full radial range by default**. Use `--rmax`
to set an upper radius limit explicitly, for example `--rmax 5` for 5 pc.

The script also creates **`density_overlay.png`**, with every snapshot's density
profile on the same axes, sorted and colored by stellar age. There are no
vertical offsets: all curves retain their physical densities. Up to ten
snapshots get individual legend labels; larger sets use the age colorbar.
With `--recursive`, each snapshot folder gets its own overlay, so separate
physics cases are not mixed.

To create only the combined density plot:

```sh
python3 plot_dat_folder.py /path/to/output --density-only
```

To include all case/output subfolders, choose another destination, or zoom in:

```sh
python3 plot_dat_folder.py /path/to/results --recursive --output /path/to/figures
python3 plot_dat_folder.py /path/to/output --log-radius --rmin 0.01 --rmax 2
python3 plot_dat_folder.py /path/to/output --format pdf
```

On Windows, replace `python3` with `python` and quote paths containing spaces.
No display or X forwarding is required. The script is standalone; it does not
need AMRVAC, yt, or the other campaign Python utilities installed.

This reader supports the current simulation's little-endian native v5, 1D HD
files from AMRVAC 3.1/3.2, with conserved variables `rho, m1, e`. Ghost cells
are excluded; cell averages are drawn using their actual AMR cell edges.
It is not a general-purpose reader for arbitrary text `.dat` files or MHD data.

Keep each case's `run.par` next to its checkpoint or above its `output/`
directory. The script uses that file to recover grid stretching; `--par FILE`
overrides automatic discovery. Downloaded cases also search the matching
`VM setup/<case>/run.par` folder. If no parameter file is found, plotting that
snapshot stops with a request for `--par`; a stretching ratio is never guessed.
Native checkpoints store the domain and AMR indices but omit the stretching
ratio. The parameter file supplies it to reconstruct the radius; VTU files,
when available, provide explicit coordinates for an independent check.
The script's physical units are fixed to the supplied `mod_usr.t` normalization.

Non-checkpoint files, including `stellar_evolution.dat`, are skipped. Bad native
files are reported without preventing other snapshots from being plotted.
Invalid physical cells are shown as gaps and flagged in the title, rather than
silently replaced with floors. `plot_summary.csv` records all plots, skipped
files, errors, and invalid-cell counts. Exit status is nonzero for bad native
files, invalid cells, or no usable snapshots. Avoid plotting a checkpoint that
AMRVAC is still writing.

## Fit and adjust the conduction front

```sh
python3 fit_conduction_front.py /path/to/test0015.dat --output /path/to/fit
```

Open `conduction_front_fit.html` in a browser. It is self-contained and works
offline. Sliders and number fields adjust p0 (g/cm^3) and R2 (pc); the curve and
weighted log-density error update immediately. Buttons restore the best fit or
the measured jump/wall anchors and export adjusted parameters or an SVG figure.
Static PNG, JSON parameters, and the fitted-cell CSV are also saved.

The -2/5 profile is normalized as
`rho(r) = p0 * [(1-r/R2)/(1-r0/R2)]^(-2/5)`, so p0 is the density at the first
resolved post-shock plateau r0, rather than at r=0. Automatic fitting uses the
contiguous hot region with T >= 1e6 K, excluding the cold swept-up shell, and
weights squared log-density residuals by radial cell width. The measured outer
wall is where density returns to within 1% of ambient after the shell peak.

The interactive page compares measured physical anchors with a free shape fit.
If the fitted R2 differs from the measured exterior wall, it is an effective
shape radius and must not be reported as that wall's position. A fixed exponent
cannot be guaranteed to reproduce every cell exactly.

To save a static figure with chosen parameters:

```sh
python3 fit_conduction_front.py /path/to/test0015.dat --p0 3.25e-25 --R2 2.25 --output /path/to/adjusted_fit
```
