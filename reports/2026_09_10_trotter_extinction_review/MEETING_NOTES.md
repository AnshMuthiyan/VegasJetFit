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
to student use and is available only when explicitly confirmed.  The 090424
short diagnostic is on Pauley-01.  The corresponding 080319B test remains
blocked until Pauley-02 finishes the all-UVOIR, `n017`-upper-25 source chain.

