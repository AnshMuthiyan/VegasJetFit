# Endpoint annotation correction: 30 October 2026

The interpretation prose in the two deliveries listed below mistakenly repeated the earlier endpoint's width, 2.343696614 native cells. Use these case-specific numerical widths:

| Case | Correct legacy 10–90 width (native cells) | Delivery commit |
| --- | ---: | --- |
| m25_n10000_pk100000000 | 2.14493042442 | 62d3bdda731d693715a35b34dcac61624192d4a1 |
| m25_n3000_pk10000000 | 1.86551671074 | 4cfeb5838c4c82f189e4c2bc43d6d34bce9b5207 |

Their structured legacy_inner records, feature diagnostics, CSV inventories, native profiles and case README numerical values already contain the correct widths. This correction supersedes only the copied prose value in scientific_review_qa.json and FEATURE_INTERPRETATION.md. Original delivered files are preserved.

Both widths remain below five native cells and overlap the independently selected flow transition. Neither establishes a resolved separate swept-density front, a physical shock width, convergence, a GRB wall or a calibrated prior. This annotation correction changes no field data, gates, feature definitions or training eligibility.
