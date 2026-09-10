# Trotter Source-Frame Extinction Scientific Audit

Date: 2026-09-10  
Student branch reviewed: `origin/jonathan-mac-version` at `e100a87`  
Production base: `jonathan-mac-version` at `317b0a0`  
Reviewed integration branch: `codex/trotter-extinction-production`

## Bottom Line

Ansh correctly transcribed many of the fitted-prior peak values and the central
curves relating `c1`, `R_V`, and `B_H` to `c2`.  The submitted code was not yet a
scientifically operative extinction model: the new parameters never entered the
modeled flux or likelihood.  It also omitted `A_V`, `c4`, and all three horizontal
scatter coordinates required by Trotter equations 3.33, 3.35, and 3.37.  The
submitted plotting code did not compile, and its 090424 configuration reverted to
an older afterglow model.

The reviewed integration repairs these issues on top of the current production
code.  It preserves the legacy CCM `E(B-V)` path for existing campaigns and selects
the Trotter path only when `av_source_frame` is present.

## Thesis Comparison

The implementation was checked against Adam S. Trotter (2011), *The Gamma-Ray
Burst Afterglow Modeling Project: Foundational Statistics and Absorption &
Extinction Models*, UNC-Chapel Hill, DOI 10.17615/2gjp-g156.

- Equations 3.25--3.28: the UV law uses the linear `c1 + c2 x` term, the Drude
  bump parameterized by `B_H`, and the far-UV curvature `c4 F(x)`, then converts
  extinction in magnitudes to flux attenuation with `10^(-0.4 A_lambda)`.
- Equation 3.27: `F(x)=0` below 5.9 inverse microns and uses the stated quadratic
  plus cubic expression above 5.9 inverse microns.
- Equation 3.29: the CCM optical law is scaled continuously from 1.82 to 3.3
  inverse microns to meet the FM law at 3.3 inverse microns.
- Equations 3.33, 3.35, and 3.37: separate horizontal and vertical nuisance
  offsets are included for each of the `c1-c2`, `R_V-c2`, and `B_H-c2`
  relations.
- Equation 3.38: asymmetric nuisance distributions are included for `x0` and
  `gamma`.
- Equation 2.62: the asymmetric Gaussian uses the single continuous
  normalization `2/[sqrt(2 pi)(sigma_plus+sigma_minus)]`.

## Deliberate Approximation

Trotter's full GRB model also samples the fitted-prior hyperparameters themselves.
For this first in-situ test, their values are fixed at the posterior peaks in
Tables 3.2--3.5 while the quoted cosmic-scatter nuisance coordinates are sampled.
This is a conditional fitted-prior model, not the full hierarchical model.  It is
computationally smaller and appropriate for testing whether flexible source-frame
dust improves the UV residuals, but that conditioning must be stated in any paper.

## Adopted 090424 Bounds

The requested hard physical bounds are retained:

| Parameter | Bound |
|---|---:|
| `A_V` | 0 to 10 mag |
| `c2` | -1 to 3.5 |
| derived `B_H` | 0 to 10 |
| `c4` | 0 to 2 |

The nuisance coordinates are bounded at five times their quoted Trotter scatter
for numerical containment.  The derived model additionally requires `R_V > 0`
and `gamma > 0`.

## Data and Provenance

The 090424 continuation starts from the authoritative all-reviewed-UV,
early-X-ray-excluded final-final result:

`jetfit/results/090424_core_logangle_powerlawcsm_kminus10to3_finalfinal_sthawed_highres_5temp_1000x5000_alluv_v2`

All existing afterglow, medium, geometry, calibration-offset, host, Milky Way,
and numerical-resolution settings are preserved.  The five latest 100-walker
cold-chain clouds seed the five temperatures.  The old source-frame `E(B-V)` is
mapped to the initial `A_V` as `A_V = 3.1 E(B-V)`; the new dust-shape coordinates
are drawn from their conditional fitted priors.

The second requested event is 080319B, whose early UVOIR/UVOT data have been
restored.  Its new extinction run must wait for the active `n017`-upper-25 chain
on Pauley-02 to finish, then use that completed cloud.  Using an older cloud would
break the requested provenance.

## Verification

- Python compilation passes on Lyra, Pauley-01, and Pauley-03.
- Seven focused physics/prior/likelihood tests pass on all tested hosts.
- Four plotting and legacy-extinction regression tests pass on Lyra.
- `A_V=0` is an exact identity.
- The attenuation is continuous at 1.82 and 3.3 inverse microns.
- `c4` changes only the far-UV curvature regime.
- Each horizontal nuisance coordinate changes only its intended relation.
- Nonphysical `B_H`, `R_V`, or `gamma` combinations receive zero prior support.
- A real 607-observation 090424 forward model is finite.
- Changing only `c4` in that forward model changes affected fluxes, proving that
  the new dust model is connected to the likelihood.
- A five-temperature, 100-walker, 2-burn plus 3-production sampler smoke test
  completed on Pauley-03 with 100 valid walkers at every temperature and wrote a
  resumable checkpoint, chain, and best-fit record.

## Remaining Acceptance Gates

1. Complete and inspect the 25-burn plus 100-production 090424 diagnostic.
2. Compare UV residuals, `nmap`, dust posteriors, and physical afterglow
   posteriors with the authoritative CCM fit.
3. Decide whether the production paper fit should retain the conditional
   peak-hyperparameter approximation or sample the full Trotter hierarchy.
4. Ethan's absorption implementation is not present in commit `e100a87`; dust
   extinction and gas/Lyman absorption must not be described as jointly tested.

