# Paper Method Notes: Source-Frame Dust Test

We tested a source-frame extinction prescription based on Trotter (2011), which
combines the Cardelli, Clayton, and Mathis optical law with the Fitzpatrick-Massa
ultraviolet form.  The ultraviolet extinction contains a linear term controlled
by `c1` and `c2`, a Drude representation of the 2175 Angstrom bump with height
`B_H`, and a far-ultraviolet curvature term controlled by `c4`.  Between 1.82 and
3.3 inverse microns, the CCM curve is scaled continuously to meet the FM curve.
The extinction in magnitudes is applied to the intrinsic afterglow flux before
host contamination and Milky Way extinction.

For this diagnostic, `A_V`, `c2`, and `c4` are free.  The values of `c1`, `R_V`,
and `B_H` are connected to `c2` through Trotter's empirically fitted correlations,
including separate horizontal and vertical cosmic-scatter nuisance coordinates;
`x0` and `gamma` use their fitted asymmetric scatter distributions.  We fixed the
hyperparameters defining those fitted correlations at the posterior peaks reported
in Trotter's Tables 3.2--3.5.  Thus this is a conditional empirical-prior model,
not a new fit of the extinction-law population hierarchy.

For GRB 090424, the dust test preserves the authoritative structured-jet model,
all reviewed UV data, exclusion of the early X-ray flare, the Milky Way foreground,
calibration offsets, host terms, and the production numerical grid.  The sampler
is initialized from the existing correlated posterior walker cloud; only the new
dust dimensions are initialized from their conditional priors.  The comparison
should report changes in UV residuals and fit statistic together with any movement
in the physical afterglow posterior.  Improvement in fit quality alone is not
sufficient: the inferred extinction curve must remain physical and the extra
degrees of freedom must be constrained by the wavelength coverage.

Do not claim that the new gas-absorption model was tested in this experiment.
That implementation was not present in the reviewed student commit.

