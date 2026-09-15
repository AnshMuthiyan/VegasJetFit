# GRB 090424 XRT Flux Provenance Audit

Date: 2026-09-14

## Conclusion

Dylan's 090424 XRT data were intentionally corrected for photoelectric
absorption before fitting. They are intrinsic, absorption-corrected 0.3-10 keV
integrated fluxes, not the observed-flux light curve served directly by the
standard UKSSDC XRT light-curve repository. VegasJetFit should therefore compare
its intrinsic afterglow flux directly with these values and should not apply a
second X-ray absorption correction.

## Evidence

1. Dylan's dissertation, Section 5.2 and Equation 5.1, states that the UKSSDC
   time-resolved light curve is observed flux and that each XRT phase is scaled
   by `F_unabs/F_obs` from the corresponding spectral fit. Section 3.3 also
   states that AMPy's integrated-flux predictions correspond to
   absorption-corrected data products.
2. The original Git-tracked 090424 table at `grb_data` commit `4d6c3f3`
   contains 502 XRT integrated-flux rows. All 502 times, fluxes, uncertainties,
   and 0.3-10 keV band limits are numerically unchanged in the current
   `grb_data/090424/090424.csv`. The later table adds 145 early XRT rows and uses
   inclusion flags; it did not recalculate Dylan's fitted XRT values.
3. At `t=250.884 s`, the current UKSSDC observed-flux product gives
   `1.614435408e-9 erg cm^-2 s^-1`; Dylan's table gives `2.19e-9`, a factor of
   1.3565 higher. The associated error is larger by 1.3531. This is the expected
   signature of a multiplicative absorption correction, not a unit conversion.
4. The current automatic WT spectrum gives observed and unabsorbed fluxes of
   `7.05e-10` and `9.62e-10 erg cm^-2 s^-1`, respectively, a ratio of 1.3645.
   The current PC spectrum similarly gives `2.83e-11` and `3.78e-11`, a ratio of
   1.3357. These are consistent with the scale of Dylan's corrections, allowing
   for subsequent UKSSDC reprocessing and phase-dependent spectral evolution.
5. The current UKSSDC Burst Analyser explicitly provides an XRT unabsorbed
   0.3-10 keV light curve and reports the absorption columns used. Its present
   values are close to, but not expected to be bitwise identical with, Dylan's
   archived table because the online products and HEASOFT processing have since
   been updated.

## Scientific Interpretation

The correction removes both Milky Way and host-galaxy photoelectric absorption
as estimated by the Swift spectral fits. It is based on an absorbed power-law
spectrum and assumes the spectral shape within an XRT-defined phase is
adequately represented by that phase's fit. This is a normal and defensible way
to compare XRT band-integrated fluxes with an intrinsic synchrotron model.

This does not mean X-ray absorption is irrelevant. It means it was handled
upstream in the data reduction rather than sampled inside AMPy/VegasJetFit.
Adding `TBabs*zTBabs` to the current model without reverting to observed fluxes
or count spectra would double-count absorption.

## Provenance Limitation and Recommendation

The CSV records the corrected values and band limits, but not the UKSSDC trigger
ID, product version, HEASOFT version, absorption model, per-phase `N_H`, or the
exact `F_unabs/F_obs` factors used at the time. The calculation is validated by
the dissertation and numerical fingerprints, but it is not fully reproducible
from the CSV alone.

For future XRT ingestion, archive together:

- trigger ID and source URL;
- downloaded observed-flux/count-rate and spectral products;
- product and HEASOFT versions;
- Galactic and host `N_H`, absorber redshift, abundances, cross sections, and
  XSPEC model;
- each phase interval and its `F_unabs/F_obs` factor; and
- a machine-readable flag such as `AbsorptionCorrected=1`.

## Sources

- Local dissertation: `/Users/jkeohane/GRBs/GRBs_old/Dylan_Dissertation.pdf`,
  PDF pages 61 and 82 (thesis pages 46 and 67), especially Equation 5.1.
- Local original table: `grb_data` commit `4d6c3f3`, path
  `done/090424/090424.csv`.
- Local current table: `/Users/jkeohane/GRBs/grb_data/090424/090424.csv`.
- UKSSDC light-curve documentation:
  https://www.swift.ac.uk/xrt_curves/docs.php/
- Current GRB 090424 XRT spectrum:
  https://www.swift.ac.uk/xrt_spectra/00350311/
- Current GRB 090424 Burst Analyser:
  https://www.swift.ac.uk/burst_analyser/00350311/
