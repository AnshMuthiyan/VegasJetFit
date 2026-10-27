# arm64 full-track grid build

Pinned MPI-AMRVAC v3.1 commit244c677fd6095bb019587a2fdc97feb67a66f06a. New isolated build on23October2026. Source SHA-256 `1f67f0d084a59d9bcb2eeba27f544cba9e15afe7288933f72eef3bf3a4054e91`; executable SHA-256 `2da92626736cc8fc3e5c3b54e1e30defc0ed0080fd0d3c0d779413697243ed51`. Setup: `setup.pl -d=1`; make serially with the pinned AMRVAC_DIR. The Mac source tree is a fresh exact Git archive in `/private/tmp/van_marle_grid_amrvac_v31_20261023`; the Linux source is `/home/jonathan/codes/amrvac-v3.1-244c677`.

`preflight_results.json`: five compiled source transition/endpoint checks plus four independent pressure checks, all PASS. `atmosphere_preflight_results.json`: two static and two wind-smoke checks at opposite corners, all PASS. Each case repeats its own initial-state gate before the full track. No old AMRVAC library or problem source was modified.

The earlier RSG-to-WR fixture failed because the boundary timestep used nominal rather than actual stretched-cell spacing when the wind accelerated. The new source uses local spacing and the maximum track speed; final v5 fixtures passed on both architectures. Failed fixture records are preserved separately; these are artificial-age transition tests, not stellar-evolution results.
