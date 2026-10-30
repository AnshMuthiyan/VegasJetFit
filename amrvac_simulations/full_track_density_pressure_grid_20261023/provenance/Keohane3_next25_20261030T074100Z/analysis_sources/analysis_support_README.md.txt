# Native AMRVAC DAT reader provenance

`amrvac_datfile_utilities_v31.py` is an unmodified copy of
`tools/python/amrvac_pytools/datfiles/reading/datfile_utilities.py` from the
AMRVAC v3.1 source at commit `244c677fd6095bb019587a2fdc97feb67a66f06a`.
SHA-256: `a5b4e3db1451d5f9e403783a263a25baa54172540c9989f3a18b1c046e8b4e9e`.
The upstream GPL v3 license is retained as `AMRVAC_LICENSE`; the original
author header remains in the reader. Upstream: https://github.com/amrvac/amrvac/tree/244c677fd6095bb019587a2fdc97feb67a66f06a .

The parent `reconcile_completed.py` uses this format reader to obtain exact
Float64 ages and native conservative cells from version-5 DAT files. This
1024-cell fixed mesh needs no interpolation. VTU vtuBmpi outputs contain
1152 piece-vertex records, including duplicated block edges, and Float32 time
labels; they are preserved but do not control exact age, mass, or cell counts.

Mass conversions retain the source constants: 365 days/year and
1.98892e33 grams/solar mass. These are deliberately not replaced by other
conventions. The first independent run erroneously demanded the endpoint
outer tolerance at every transient save; its failed postprocessing gate is
preserved in `analysis_attempt_01_all_history_outer_gate/`. The corrected
report checks the endpoint outer atmosphere and retains every transient
drift explicitly. No AMRVAC input, run or frozen runtime checker was changed.
