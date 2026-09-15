# Meeting Notes: 090424 Trotter Extinction Test

## Scientific Question

Can an in-situ, flexible source-frame dust law improve the poor UV-band fit of
GRB 090424 without forcing a materially different or nonphysical afterglow
solution?

## What Is Held Fixed in the Comparison

- Same authoritative 090424 data selection: all reviewed UV points included.
- Same exclusion of the early X-ray flare.
- Same structured power-law jet, power-law CSM, and numerical grid.
- Same Milky Way foreground and calibration/host nuisance structure.
- Same correlated afterglow posterior cloud used to initialize the fit.

## What Changes

The one-parameter source-frame CCM color excess is replaced by the conditional
Trotter CCM/FM model.  The new fit samples `A_V`, `c2`, `c4`, the horizontal and
vertical scatter about the empirical `c1-c2`, `R_V-c2`, and `B_H-c2`
relations, and the asymmetric scatter in bump center and width.  Derived `B_H`
is restricted to 0--10.  The fitted-prior hyperparameters are held at their
Trotter thesis peak values for this diagnostic.

## Decision Criteria

1. Compare residuals by wavelength, with special attention to UVOT bands.
2. Compare `nmap`, while accounting for the additional free parameters rather
   than treating any raw improvement as decisive.
3. Check whether `A_V`, `c2`, `B_H`, and `c4` are constrained or merely absorb
   noise/calibration differences.
4. Check whether the physical afterglow posterior moves significantly from the
   authoritative result.
5. Reject the model for production use if posterior mass accumulates at hard
   dust bounds or requires implausible extinction curves.

## Operational Note

During the academic year, Pauley is the normal fit pool.  PCRC belongs primarily
to student use and is available only when explicitly confirmed.  The completed
short 090424 diagnostics established the starting clouds for the longer paired
comparison.  The earlier Pauley-02 dependency on the 080319B all-UVOIR,
`n017`-upper-25 source chain has cleared.

## Paired Overnight Comparison: 2026-09-14

The production comparison runs the two extinction prescriptions concurrently
on identical M1 Max Pauley hosts.  Trotter runs on Pauley-01 and CCM runs on
Pauley-02.  Both use the same 607-point reviewed data file, exclude the early
X-ray flare, use verified photon-counting filter integration with 16 intrinsic
spectrum nodes, and retain the same Vegas numerical grid.  Each run starts from
all five temperatures and all 100 terminal walkers of its completed short
verified-bandpass diagnostic.

The overnight sampler uses five temperatures, 100 walkers, 100 burn-in steps,
800 retained production steps, eight workers, and checkpoints every 50 steps.
This is long enough to test whether the short-run model differences persist,
while fitting within the preparation window before the 2026-09-15 16:00 EDT
meeting.  The resulting comparison must distinguish raw fit improvement from
the cost of Trotter's additional dust coordinates; it reports pure likelihood,
approximate AIC/BIC, residual changes by band, and shifts in shared physical and
nuisance parameters.

After both chains complete, the Lyra watcher also writes a compact LaTeX/PDF
comparison report.  Its runtime section uses the final `/usr/bin/time -p`
records from both Pauley hosts and reports hours, absolute difference, and the
slower-to-faster ratio.  The two short diagnostics took 1.91 hours (Trotter)
and 1.99 hours (CCM), but those sequential Lyra measurements differ by only
4.3% and are not the controlled paired timing result.
The canonical completed package is written to the synced VegasGRBruns share at
`Reports/Meeting_Books/26_09_15__090424_ccm_vs_trotter_extinction_comparison/`.
