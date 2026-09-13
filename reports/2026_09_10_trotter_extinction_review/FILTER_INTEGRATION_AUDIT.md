# Filter Integration Audit

Date: 2026-09-13

## Scientific Definition

For a photon-counting detector, the predicted count rate is proportional to

`integral F_nu(lambda) A_eff(lambda) / lambda dlambda`.

The implemented observable divides this by `integral A_eff/lambda dlambda`.
It is therefore the AB-equivalent, photon-weighted mean `F_nu` and exactly
preserves a constant `F_nu` spectrum. Source-frame extinction is evaluated at
`lambda/(1+z)` and Milky Way extinction at observer-frame `lambda`, inside the
integral. This ordering is essential for broad UV filters and their red leaks.

## Verified Responses

- Swift/UVOT `v`, `b`, `u`, `uvw1`, `uvm2`, and `uvw2`: current good-quality
  OGIP ARFs selected from the NASA HEASARC Swift CALDB index. The ARF
  `SPECRESP` field is the complete effective area.
- HST/WFC3 `F775W` (UVIS2) and `F125W` (IR): frozen total-system throughput
  VOTables from the SVO Filter Profile Service. Zhu et al. (2023) explicitly
  identify the two GRB 220101A points as WFC3 observations.

Checksums and retrieval details are stored beside the response files in
`jetfit/resources/filters/`.

## Campaign Coverage

The authoritative July-16 campaign contains 138 distinct event/filter pairs:

- 44 pairs use one of the eight verified responses above.
- 88 optical/NIR pairs have generic labels (`B`, `V`, `R`, `I`, `g`, `r`,
  `i`, `z`, `J`, `H`, `K`, and variants). Their exact camera/filter is not
  encoded, so they remain monochromatic rather than being silently assigned
  an incorrect Johnson, Cousins, SDSS, GROND, or other curve.
- 6 radio/millimeter channel pairs are narrow frequency measurements, not
  broadband optical photometry.

The complete event-by-event inventory is in
`filter_integration_inventory.csv`. Future data ingestion should add an
instrument/passband identifier, ideally an SVO filter ID, so generic labels
can be integrated safely.

## Calibration Convention

The UVOT CALDB defines AB calibration by convolving a constant `F_nu` spectrum
with the effective area, matching the normalization used here. Dylan's thesis
states that GRB 090424's UVOT measurements were reported in the AB system and
converted with standard AB zero points, so the new synthetic observable is
directly compatible with that event.

Not every legacy event has the same provenance. Some UVOT values were reported
as Vega/flight-system magnitudes or as already converted flux densities. A
response integral alone cannot reconstruct those catalog conventions without
the original count rate or an explicit reference spectrum. Those cases are
scientifically useful diagnostics but should not be called exact
recalibrations until the observation schema records the photometric system.

## Numerical Validation

- Unit tests load all eight responses, reproduce their pivot wavelengths,
  preserve constant `F_nu`, integrate source dust within the passband, retain
  UVOT red-leak tails at `A_V=10`, and leave ambiguous filters unchanged.
- On the completed 090424 Trotter best fit, direct evaluation at every CALDB
  wavelength takes 9.38 s per likelihood. Sixteen response-quantile intrinsic
  spectrum samples plus both response tails take 0.83 s and differ from the
  direct result by at most 0.0312% across all 79 UVOT observations (median
  0.00080%).
- The old monochromatic approximation differs from the direct response result
  by as much as 38.6% for the same UVOT observations (median 0.476%).
- Compressing the response and extinction together is forbidden in production:
  it can miss red-leak-dominated counts by order unity at high extinction.

`--bandpass-integration verified` activates all verified responses.
`--bandpass-nodes 16`
is the validated production setting; `--bandpass-nodes 0` performs the
brute-force reference calculation. Both settings are written into
`best_fit.json`.

## Remaining Physics Boundary

Bandpass integration does not replace host H I or Lyman-forest absorption.
This is especially important for high-redshift events such as 220101A. The
WFC3 curves are now ready, but a scientifically complete high-redshift fit must
apply the separate H I/Lyman transmission inside the same bandpass integral.
