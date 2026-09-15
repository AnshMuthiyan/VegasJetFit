# JetFit
Gamma-ray Burst Afterglow Light Curve Fitting Tool.

The JetFit package fits GRB afterglow light curves for arbitrary viewing
angle using the "boosted fireball" structured jet model [Duffell \& MacFadyen (2013)](https://iopscience.iop.org/article/10.1088/2041-8205/776/1/L9/meta)
for the jet dynamics (for details see [Wu \& MacFadyen (2018)](https://iopscience.iop.org/article/10.3847/1538-4357/aae9de). The 
light curve computation is based on the ScaleFit package ([Ryan, van Eerten, MacFadyen \& Zhang (2015)](http://iopscience.iop.org/article/10.1088/0004-637X/799/1/3/pdf)).
JetFit is currently in some state between alpha and beta.

`Table.h5` contains the characteristic spectral functions, which are used 
to generate synthetic light curves. The table is almost the same as the 
table used in [Wu \& MacFadyen (2018)](https://iopscience.iop.org/article/10.3847/1538-4357/aae9de). We are improving the table by 
increasing resolution, adding synchrotron absorption and wind circumburst 
medium. Hopefully, it will come out pretty soon.


# Setup
- Clone the repo and enter it.
  ```
  git clone https://github.com/astrodyl/JetFit.git
  cd JetFit
  ```
- Install Python 3.8 and create a virtual environment.
  ```
  python -m venv /path/to/new/virtual/environment
  ```
- Activate the venv and install the dependencies.
  ```shell
  # Windows Users
  /path/to/new/virtual/environment/Scripts/activate
  pip install --upgrade setuptools
  pip install -r requirements.txt
  
  # Linux Users
  source /path/to/new/virtual/environment/bin/activate
  pip install -r requirements.txt
  ```


# Usage
To run JetFit, simply activate your virtual environment and run `python __main__.py`.

## Source-frame dust extinction

Choose the host/source-frame dust law explicitly near the top of each model
TOML. New configurations default to `trotter2011` when the key is omitted, but
committed legacy CCM configurations are marked explicitly so their physics does
not change.

```toml
# Source-frame dust-law references:
# Trotter, A. S. 2011, UNC-Chapel Hill PhD thesis, DOI 10.17615/2gjp-g156.
# Cardelli, Clayton, and Mathis 1989, ApJ, 345, 245 (CCM89).
# Allowed: "trotter2011" (default for new configs) or "ccm89".
source_extinction_model = 'trotter2011'
```

The Trotter model requires source-frame extinction parameters
`av_source_frame`, `c2`, and `c4`. Its empirical scatter coordinates named
`delta_*` are optional; when present, their correlated priors are included.
CCM89 instead requires `ebv_source_frame` and optionally accepts
`rv_source_frame` (default `R_V=3.1`). Milky Way extinction remains a separate
CCM89 foreground specified by `ebv_milky_way` and optionally
`rv_milky_way`.

For a deliberate one-run override, use either canonical name or its short
alias:

```shell
python -m jetfit.run ... --source-extinction-model trotter2011
python -m jetfit.run ... --source-extinction-model ccm89
# `trotter` and `ccm` are accepted aliases.
```

Preflight validation rejects mixed or incomplete CCM/Trotter parameter blocks
before the sampler starts. Because the two prescriptions fit different
coordinates, their posterior-cloud seed files are not interchangeable.

## Neutral-hydrogen absorption

Gas absorption is selected independently from dust extinction. The
intergalactic component uses the mean Lyman-series plus Lyman-continuum model
of [Inoue et al. (2014)](https://doi.org/10.1093/mnras/stu936). The optional
host component uses the damped-Lyman-alpha profile and source-frame Lyman
limit in [Trotter (2011), Section 3.4.1](https://doi.org/10.17615/2gjp-g156),
following [Totani et al. (2006)](https://doi.org/10.1093/pasj/58.2.485).

Existing TOMLs that do not contain these keys remain gas-off to preserve the
provenance of historical fits. New absorption experiments must state both
choices explicitly:

```toml
# Neutral-hydrogen absorption references (separate from dust extinction):
# Inoue et al. 2014, MNRAS, 442, 1805: mean intergalactic Lyman absorption.
# Trotter 2011 thesis, Section 3.4.1: host DLA and source Lyman limit.
# Totani et al. 2006, PASJ, 58, 485: host damped-Lyman-alpha profile.
igm_absorption_model = 'inoue2014'
host_hi_absorption_model = 'none'
```

The Inoue model has no fitted coordinate; it is determined by the fixed,
known source redshift `z`. To fit the host neutral-hydrogen column as well,
select `trotter2011` and add a physical `N_HI` parameter. A logarithmic
coordinate is recommended:

```toml
host_hi_absorption_model = 'trotter2011'

[[absorption]]
name = 'nhi_host'
scale = 'log'

[absorption.prior]
type = 'uniform'
lower = 18.0
upper = 23.0
```

The command line accepts `--igm-absorption-model none|inoue2014` and
`--host-hi-absorption-model none|trotter2011`. Enabling either component
requires one fixed, non-negative, linearly stored `z`; the host model also
requires `nhi_host`. Invalid combinations fail before MCMC initialization.

For filters with archived response curves, run with
`--bandpass-integration verified`. The intrinsic spectrum, dust, IGM, and
host-H-I transmission are then combined inside the photon-counting response
integral. Instrument-ambiguous filter labels retain the documented central
wavelength approximation. These optical/UV H I models must not be applied to
the absorption-corrected Swift-XRT integrated-flux products.

# Module Description
JetFit package consists of three classes: Interpolator, FluxGenerator and Fitter. FluxGenerator can be used separately.

 ## Interpolator:
  * `_load_table`: load characteristic spectral function table.
  * `_set_scale`: set scales for the table. By default, f_peak and tau are in log scale.
  * `_get_interpolator`: use `scipy.interpolate.RegularGridInterpolator` as interpolator.
  * `get_value`: get values for characteristic spectral function at specific position (tau, Eta0, GammaB, theta_obs).

 ## FluxGenerator:
  * `get_taus`: rescale the observational time in second.
  * `get_transformed_value`: get the transformed values f_peak, nu_c and nu_m (Ryan et al. 2015).
  * `get_spectral`: calculate synthetic light curves f_nu (Sari et al. 1998).
  * `get_integrated_flux`: calculate synthetic integrated light curves.

 ## ScaleFitClass:
  * `_set_fit_parameter`: set up ScaleFit, e.g. parameter scales and parameter bounds.
  * `load_data`: load observational data.
  * `set_sampler`: initialize sampler from emcee package.
  * `run`: run sampling procedure and save results to local drive.
