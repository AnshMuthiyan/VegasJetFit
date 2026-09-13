# Swift/UVOT effective-area curves

These OGIP ARFs are the latest good-quality (`CAL_QUAL=0`) files selected by
the Swift/UVOTA CALDB index on 2026-09-13. They were downloaded from:

`https://heasarc.gsfc.nasa.gov/FTP/caldb/data/swift/uvota/cpf/arf/`

| Filter | CALDB file | SHA-256 |
|---|---|---|
| V | `swuvv_20041120v104.arf` | `250da525bfeae25cd54cd2af828c1b27c518bc2e8ecc3d41958a2061fa0012a1` |
| B | `swubb_20041120v104.arf` | `9f40ea2174922f48cdeed69f2c6b336b8a8d10dffb4c44a052b6e633e8d7532c` |
| U | `swuuu_20041120v104.arf` | `0eeb76f208863a62e06d37c1ed2cd41fbb151541458b3cca74ad6ecf9e082644` |
| UVW1 | `swuw1_20041120v106.arf` | `9f30a3a4fd430ef9903009457d3fd4e5db876296e2f97de3797e3ea6164cb3d2` |
| UVM2 | `swum2_20041120v105.arf` | `19f75c2e812784b193fc94518aa64f16a35da9aa0a2cea1a6395ba4a048b1113` |
| UVW2 | `swuw2_20041120v105.arf` | `c7190c561d146398dc1d2376e5a95d115cd859eb482a2459c20f93029fd6c6d7` |

The `SPECRESP` column is the complete instrument effective area in square
centimeters. `jetfit.core.bandpass` applies the photon-counting weight
`A_eff(lambda)/lambda`; it does not multiply these ARFs by a second filter or
mirror curve.

Generic campaign labels such as `U`, `B`, `V`, `R`, `r`, and `i` are not
aliases for these files. They require instrument-level provenance before a
response curve can be assigned.
