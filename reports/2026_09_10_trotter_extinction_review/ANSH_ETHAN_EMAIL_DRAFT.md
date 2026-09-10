# Draft Email to Ansh and Ethan

Subject: Review and test of the Trotter extinction implementation

Hi Ansh and Ethan,

Thank you for pushing the Trotter prior work.  I reviewed it against Adam
Trotter's thesis and integrated the useful pieces into our current production
branch.  Ansh's fitted-prior constants and the central `c1-c2`, `R_V-c2`, and
`B_H-c2` relations were a good starting point.

The pushed version was not yet connected to the modeled flux, so its new
parameters could change the prior but could not change the likelihood.  I added
the combined CCM/FM attenuation law from equations 3.25--3.29, including `A_V`,
the Drude bump, `c4` far-UV curvature, and the CCM-to-FM interpolation.  I also
added the three horizontal-scatter coordinates required by equations 3.33, 3.35,
and 3.37, corrected the asymmetric-Gaussian normalization to equation 2.62, and
repaired the corner-plot syntax error.  I ported these changes onto our current
structured-jet production code because the student branch had pulled in an older
model interface.

The focused tests now verify continuity at both law boundaries, identity at
`A_V=0`, the wavelength dependence of `c4`, independent action of each scatter
coordinate, rejection of nonphysical derived parameters, agreement between fit
and plot attenuation paths, and actual sensitivity of the likelihood to the new
dust parameters.  A five-temperature, 100-walker end-to-end smoke test for GRB
090424 completed successfully.  I am running a 25-burn plus 100-production
diagnostic before considering a long fit.

For this first test I fixed the fitted-prior hyperparameters at the peak values in
Trotter's Tables 3.2--3.5 while sampling the quoted cosmic scatter.  Trotter's full
hierarchical prescription also samples those hyperparameters, so we should decide
together whether the final paper run needs that larger parameterization.

I did not find Ethan's gas/Lyman absorption implementation in the latest commit I
could fetch.  Please let me know which commit contains it when it is ready, and I
will audit that portion separately rather than conflating absorption with dust
extinction.

Best,
Jonathan

