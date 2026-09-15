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
