# Purpose: Generate a three-input density law with controlled inner slopes, retain the earlier detailed fit, and overwrite fixed analysis outputs.
"""Three-input empirical density profile for the test0098 radial section."""
import argparse
import csv
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.optimize import brentq, minimize_scalar

HERE = Path(__file__).resolve().parent


def _base_log_density(x, contrast, minimum_density):
    f = (27 / 4) * x**2 * (1 - x)
    return (np.log(minimum_density)
            + contrast * (1 - f**2) / (1 + contrast**2 * f**2))


def _base_log_slope(x, contrast):
    f = (27 / 4) * x**2 * (1 - x)
    derivative = (27 / 4) * x * (2 - 3 * x)
    return -2 * contrast * (1 + contrast**2) * f * derivative * x / (1 + contrast**2 * f**2)**2


@lru_cache(maxsize=64)
def _inner_break_fraction(contrast):
    """Derive the outermost inner-branch crossing of slope -2; no fitted radius."""
    minimum = minimize_scalar(lambda x: _base_log_slope(x, contrast),
                              bounds=(1e-10, 2/3), method='bounded')
    if minimum.fun >= -2:
        return 0.0  # The original function already satisfies the inner slope bound.
    return brentq(lambda x: _base_log_slope(x, contrast) + 2,
                  minimum.x, 2/3, xtol=1e-13)


def _inputs(radius_pc, R, rhoR, rho_min, inner_behavior):
    modes = {'flat': 0.0, 'gentle': 1.0, 'wind': 2.0, 'original': None}
    if inner_behavior not in modes:
        raise ValueError('inner_behavior must be flat, gentle, wind, or original')
    if not (np.isfinite([R, rhoR, rho_min]).all() and R > 0 and 0 < rho_min < rhoR):
        raise ValueError('Require finite R>0 and 0<rho_min<rho_R')
    x = np.asarray(radius_pc, dtype=float) / R
    if np.any(~np.isfinite(x) | (x < 0) | (x > 1)):
        raise ValueError('This profile is defined only between r=0 and R; do not extrapolate')
    return x, float(np.log(rhoR/rho_min)), modes[inner_behavior]


def density_profile(radius_pc, outer_radius_pc, outer_density_g_cm3, minimum_density_g_cm3,
                    inner_behavior='flat'):
    """Return g/cm^3 from R [pc], rho(R), and one additional model minimum.

    The minimum position is fixed at 2R/3; wall sharpness is tied to density
    contrast. These are empirical restrictions, not conduction identities.
    The default inner extension flattens at the origin and has logarithmic
    slope >= -2. 'gentle' and 'wind' give asymptotic r^-1 and r^-2 instead.
    These are fixed behavior choices, not additional fitted coefficients.
    The original fit is calibrated only over the reported fit interval;
    the added inner extension does not determine the physical wind density.
    """
    x, contrast, beta = _inputs(radius_pc, outer_radius_pc, outer_density_g_cm3,
                                minimum_density_g_cm3, inner_behavior)
    log_density = _base_log_density(x, contrast, minimum_density_g_cm3)
    xb = _inner_break_fraction(contrast) if beta is not None else 0.0
    if xb > 0:
        log_rho_b = _base_log_density(xb, contrast, minimum_density_g_cm3)
        t = x / xb
        # Both the density and its first derivative match at t=1.
        # For beta=0 this remains finite and differentiable at r=0.
        inner = (log_rho_b - beta*np.log(np.maximum(t, np.finfo(float).tiny))
                 + (2-beta)*(1-t*t)/2)
        log_density = np.where(x < xb, inner, log_density)
    with np.errstate(over='ignore'):
        result = np.exp(log_density)
    if beta is not None and beta > 0 and xb > 0:
        result = np.where(x == 0, np.inf, result)
    return result


def density_log_slope(radius_pc, outer_radius_pc, outer_density_g_cm3, minimum_density_g_cm3,
                      inner_behavior='flat'):
    """Return d ln(rho)/d ln(r); controlled modes bound the index below by -2."""
    x, contrast, beta = _inputs(radius_pc, outer_radius_pc, outer_density_g_cm3,
                                minimum_density_g_cm3, inner_behavior)
    result = _base_log_slope(x, contrast)
    xb = _inner_break_fraction(contrast) if beta is not None else 0.0
    if xb > 0:
        result = np.where(x < xb, -beta-(2-beta)*(x/xb)**2, result)
    return result


def summarize(r, y, predicted, widths, rmin, rmax):
    error = predicted / y - 1
    log_error = np.log(predicted / y)
    factor = np.exp(np.abs(log_error))
    w = widths / widths.sum()
    bins = []
    edges = np.linspace(rmin, rmax, 7)
    for left, right in zip(edges[:-1], edges[1:]):
        m = (r >= left) & (r < right)
        bw = widths[m] / widths[m].sum()
        bins.append(dict(left=left, right=right, count=int(m.sum()),
                         rms_dex=np.sqrt(np.sum(bw * log_error[m]**2)) / np.log(10),
                         rms_factor=np.exp(np.sqrt(np.sum(bw * log_error[m]**2))),
                         signed_bias_percent=100 * np.sum(bw * error[m]),
                         relative_rms_percent=100 * np.sqrt(np.sum(bw * error[m]**2))))
    return dict(median_percent=100 * np.median(np.abs(error)),
                p90_percent=100 * np.quantile(np.abs(error), 0.90),
                p90_factor=np.quantile(factor, 0.90),
                median_factor=np.median(factor), worst_factor=np.max(factor),
                worst_radius_pc=float(r[np.argmax(factor)]),
                rms_dex=np.sqrt(np.sum(w * log_error**2)) / np.log(10),
                relative_rms_percent=100 * np.sqrt(np.sum(w * error**2)), bins=bins)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=HERE / 'output/test0098_density_profile.csv')
    parser.add_argument('--output', type=Path, default=HERE / 'output')
    parser.add_argument('--outer-radius', type=float, default=2.955)
    parser.add_argument('--outer-density', type=float, help='Density at exactly R; otherwise log-interpolate the data')
    parser.add_argument('--rho-min', type=float, help='The one extra input; omit to fit it from this interval')
    parser.add_argument('--inner-behavior', choices=['flat', 'gentle', 'wind'], default='flat',
                        help='Fixed inner-limit choice: constant, r^-1, or r^-2; never steeper than r^-2')
    parser.add_argument('--rmin', type=float, default=1.16)
    args = parser.parse_args()
    if not args.output.is_dir():
        parser.error('Reuse the existing output directory; no new directory is created')
    data = np.genfromtxt(args.input, delimiter=',', names=True, skip_header=1)
    rr, yy = data['radius_pc'], data['density_g_cm3']
    R = args.outer_radius
    if not rr[0] < args.rmin < R < rr[-1]:
        parser.error('Fit interval must lie within the measured radius range')
    rhoR = args.outer_density if args.outer_density is not None else float(np.exp(np.interp(R, rr, np.log(yy))))
    if rhoR <= 0:
        parser.error('Outer density must be positive')
    selected = (rr >= args.rmin) & (rr < R)
    r, y = rr[selected], yy[selected]
    widths = np.minimum(data['r_outer_pc'][selected], R) - np.maximum(data['r_inner_pc'][selected], args.rmin)
    weights = widths / widths.sum()
    if args.rho_min is None:
        def loss(a):
            prediction = density_profile(r, R, rhoR, rhoR * np.exp(-a), args.inner_behavior)
            return np.sum(weights * np.log(prediction / y)**2)
        fitted = minimize_scalar(loss, bounds=(0.01, 30), method='bounded', options={'xatol': 1e-12})
        if not fitted.success:
            raise RuntimeError('Single-parameter fit failed')
        rho_min = float(rhoR * np.exp(-fitted.x))
    else:
        rho_min = args.rho_min
    a = float(np.log(rhoR / rho_min))
    predicted = density_profile(r, R, rhoR, rho_min, args.inner_behavior)
    xb = _inner_break_fraction(a)
    rb = float(R * xb)
    rho_b = float(density_profile(rb, R, rhoR, rho_min)) if rb > 0 else None
    flat_origin = float(density_profile(0, R, rhoR, rho_min, 'flat'))
    original_predicted = density_profile(r, R, rhoR, rho_min, 'original')
    if rb < args.rmin:
        assert np.array_equal(predicted, original_predicted)
    inner_grid = np.geomspace(R*1e-8, 2*R/3, 1200)
    for behavior in ('flat', 'gentle', 'wind'):
        assert np.min(density_log_slope(inner_grid, R, rhoR, rho_min, behavior)) >= -2-1e-10
    assert np.isfinite(flat_origin)
    assert np.isclose(density_profile(R, R, rhoR, rho_min) / rhoR, 1, rtol=1e-12)
    assert np.isclose(density_profile(2 * R / 3, R, rhoR, rho_min) / rho_min, 1, rtol=1e-12)
    stats = summarize(r, y, predicted, widths, args.rmin, R)
    reference_file = args.output / 'test0098_density_function.csv'
    reference = np.genfromtxt(reference_file, delimiter=',', names=True, skip_header=1)
    reference_density = np.exp(np.interp(r, reference['radius_pc'], np.log(reference['fitted_density_g_cm3'])))
    reference_stats = summarize(r, y, reference_density, widths, args.rmin, R)
    hot = np.flatnonzero((rr >= 1.2) & (rr <= 2.84))
    j = hot[np.argmin(yy[hot])]
    poly = np.polyfit(rr[j-1:j+2], np.log(yy[j-1:j+2]), 2)
    observed_minimum_r = float(-poly[1] / (2 * poly[0]))
    observed_minimum_rho = float(np.exp(np.polyval(poly, observed_minimum_r)))
    postjump = r >= 1.2
    postjump_factors = np.exp(np.abs(np.log(predicted[postjump] / y[postjump])))
    postjump_worst = float(np.max(postjump_factors))
    postjump_worst_r = float(r[postjump][np.argmax(postjump_factors)])
    base = args.output / 'test0098_density_simple'

    with base.with_suffix('.csv').open('w', newline='') as stream:
        stream.write('# Purpose: Original test0098 densities, the three-input model, the retained detailed reference, and fractional errors.\n')
        writer = csv.writer(stream)
        writer.writerow(['radius_pc', 'density_g_cm3', 'simple_density_g_cm3',
                         'relative_error_percent', 'detailed_reference_density_g_cm3'])
        for row in zip(r, y, predicted, 100 * (predicted / y - 1), reference_density):
            writer.writerow([format(float(v), '.17g') for v in row])

    lines = [
        '# Purpose: State the reduced endpoint-anchored density function, its three inputs, and the explicitly sacrificed shape accuracy.',
        '', 'INPUTS AND PARAMETER COUNT',
        f'R = {R:.14g} pc', f'rho_R = {rhoR:.14e} g/cm^3',
        f'rho_min = {rho_min:.14e} g/cm^3 (the only additional adjustable input)',
        'rho_R is log-interpolated at exactly R unless --outer-density supplies it.',
        'R and rho_R are fixed anchors, not fitted coefficients.',
        'Only rho_min is fitted when --rho-min is omitted.',
        '', 'OUTER FUNCTION (r>=rb; controlled inner continuation is given below)',
        'x = r/R', 'f(x) = (27/4)*x^2*(1-x)', 'a = ln(rho_R/rho_min)',
        'rho(r) = rho_min * exp[a*(1-f(x)^2)/(1+a^2*f(x)^2)]',
        f'Derived contrast a = {a:.14g}; it is NOT another independent parameter.',
        'Equivalent: rho=rho_R*exp[-a*(1+a^2)*f^2/(1+a^2*f^2)].',
        '', 'EXACT ANCHORS AND FIXED SHAPE ASSUMPTIONS',
        'rho(R)=rho_R exactly, and rho(2R/3)=rho_min exactly.',
        f'Predicted minimum radius 2R/3 = {2*R/3:.12g} pc.',
        'The normalized cubic fixes the minimum location; the density contrast also controls wall sharpness.',
        'The cubic and the a^2 coupling are explicit empirical restrictions, not a conduction derivation.',
        'There is no independently fitted minimum position, wall width, exponent, or sigmoid position.',
        'No old fitted coefficients have been frozen or hidden in this model.',
        '', 'CONTROLLED INNER EXTENSION (NEW)',
        'The unmodified cubic model tends to rho_R at r=0 but has an intermediate inner slope near -10.',
        'Find rb as the outermost inner-branch radius where dln(rho)/dln(r)=-2.',
        f'Derived rb = {rb:.14g} pc; it is not another fitted parameter.',
        f'rho_b = rho_original(rb) = {rho_b:.14e} g/cm^3.' if rb > 0 else 'No continuation needed: original slope is already bounded.',
        'Keep the original function at r>=rb. At r<rb, t=r/rb and',
        'rho_inner = rho_b * t^(-beta) * exp[(2-beta)*(1-t^2)/2].',
        'Its logarithmic slope is -beta-(2-beta)*t^2, always between -2 and -beta.',
        'beta=0: finite flat core; beta=1: gentle r^-1 limit; beta=2: r^-2 limit.',
        'Density and its first derivative match at rb. Choose beta as a fixed behavior, not a fitted coefficient.',
        f'Current choice: {args.inner_behavior}. Default flat rho(0) = {flat_origin:.14e} g/cm^3.',
        'For these coefficients rb is below 1.16 pc, so every density in the fitted interval is unchanged.',
        'This controlled extension is a mathematical assumption, not a fit to the simulation free-wind normalization.',
        '', 'SHAPE COST',
        f'Data interior minimum: radius {observed_minimum_r:.12g} pc, density {observed_minimum_rho:.12e} g/cm^3.',
        f'Model minimum-radius shift: {2*R/3-observed_minimum_r:+.6f} pc.',
        f'Model minimum-density offset: {100*(rho_min/observed_minimum_rho-1):+.4f}%.',
        'The initial resolved jump near 1.16--1.20 pc is not modeled independently.',
        f'Worst error across all selected cells: factor {stats["worst_factor"]:.6f} at {stats["worst_radius_pc"]:.9f} pc.',
        f'After r>=1.2 pc, worst error: factor {postjump_worst:.6f} at {postjump_worst_r:.9f} pc.',
        f'Median absolute fractional error: {stats["median_percent"]:.6f}%.',
        f'90th percentile absolute fractional error: {stats["p90_percent"]:.6f}%.',
        f'90th percentile multiplicative error factor: {stats["p90_factor"]:.6f}.',
        f'Width-weighted relative RMS: {stats["relative_rms_percent"]:.6f}% (includes poorly modeled jump cells).',
        f'Width-weighted RMS log10 error: {stats["rms_dex"]:.6f} dex.',
        '', 'SAME METRIC IN SIX EQUAL RADIAL BINS',
        'left_pc right_pc cells RMS_log10_dex multiplicative_RMS_factor relative_RMS_percent signed_bias_percent',
    ]
    for row in stats['bins']:
        lines.append(f'{row["left"]:.6f} {row["right"]:.6f} {row["count"]:3d} {row["rms_dex"]:.6f} {row["rms_factor"]:.6f} {row["relative_rms_percent"]:.6f} {row["signed_bias_percent"]:+.6f}')
    lines += [
        '', 'ASSESSMENT',
        'The local error is not uniform: both the first jump and the rapid wall are worse than the broad interior.',
        'This is a deliberately reduced shape approximation, not a replacement for the detailed fit when percent-level accuracy is required.',
        'A separate adjustable minimum position or wall width would require another independent input.',
        f'The detailed reference is retained unchanged in {reference_file.name} and its original plot/report.',
        '', 'LOG/RECIPROCAL TRANSFORMATION',
        'u = ln(rho_R/rho)/a; then the model implies',
        '1/u = [1/(1+a^2)]*(1/f^2) + a^2/(1+a^2).',
        'This provides a linearizing check; it is not evidence for a unique physical law.',
        '', 'USE',
        'from fit_test0098_density_simple import density_profile',
        f'density_profile(radius_pc, {R:.12g}, {rhoR:.12e}, {rho_min:.12e})',
        'Units: input radius in pc; output density in g/cm^3.',
        'Calibrated interval: 1.16--2.955 pc in this 4.77 Myr snapshot. Below that, the selected controlled extension is unvalidated against the actual wind density. Do not apply outside R.',
        'Reuse by supplying R, rho_R, and rho_min; no snapshot table is needed to evaluate the function.',
    ]
    base.with_suffix('.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FixedLocator, FuncFormatter, LogLocator, NullFormatter
    fig = plt.figure(figsize=(13, 11), layout='constrained')
    gs = fig.add_gridspec(3, 2, height_ratios=[1.2, 1, 0.85])
    full = fig.add_subplot(gs[0, :])
    zoom = fig.add_subplot(gs[1, 0])
    linear = fig.add_subplot(gs[1, 1])
    residual = fig.add_subplot(gs[2, 0])
    windows = fig.add_subplot(gs[2, 1])
    dense = np.linspace(args.rmin, R, 2000)
    curve = density_profile(dense, R, rhoR, rho_min)
    blue, green, black = '#196b94', '#77996b', '#333333'

    def radius_axis(ax, left=args.rmin, right=R):
        ax.set_xscale('log')
        ax.set_xlim(left, right)
        ax.xaxis.set_major_locator(FixedLocator([v for v in [1.2, 1.5, 2, 2.5, R] if left <= v <= right]))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:g}'))
        ax.xaxis.set_minor_locator(LogLocator(base=10, subs=np.arange(1.1, 10, .1)))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.tick_params(axis='x', which='both', top=True, bottom=True, labeltop=True, labelbottom=True)
        ax.set_xlabel('Radius [pc], logarithmic scale')
        ax.grid(True, which='major', alpha=.25)
        ax.grid(True, which='minor', axis='x', alpha=.12)

    full.scatter(r, y, s=12, color=black, label='Snapshot cell centers', zorder=4)
    full.plot(reference['radius_pc'], reference['fitted_density_g_cm3'], '--', color=green, lw=1.2,
              label='Retained detailed reference')
    full.plot(dense, curve, color=blue, lw=2, label='R, density at R, and one model minimum')
    full.scatter([R], [rhoR], color='#c46832', s=55, marker='D', label='Exact outer-density anchor', zorder=5)
    full.set_yscale('log')
    full.set_ylabel('Density [g cm$^{-3}$]')
    full.set_title('test0098 | three-input empirical law | 1.16-2.955 pc', fontsize=13)
    radius_axis(full)
    full.xaxis.set_label_position('top')
    full.legend(fontsize=8, loc='upper left')

    hm = (r >= 1.2) & (r <= 2.8458)
    zoom.scatter(r[hm], y[hm]/1e-24, s=12, color=black)
    zoom.plot(r[hm], reference_density[hm]/1e-24, '--', color=green, lw=1.2)
    hd = dense[(dense >= 1.2) & (dense <= 2.8458)]
    zoom.plot(hd, density_profile(hd, R, rhoR, rho_min)/1e-24, color=blue, lw=2)
    zoom.axvline(observed_minimum_r, ls=':', color='#777777', label='Observed minimum')
    zoom.axvline(2*R/3, ls=':', color=blue, label='Fixed minimum: 2R/3')
    zoom.set_ylabel(r'Density / $10^{-24}$ g cm$^{-3}$')
    zoom.set_title('Interior shape: a shallower minimum shifted outward')
    radius_axis(zoom, 1.2, 2.8458)
    zoom.legend(fontsize=8)

    f = (27/4)*(r/R)**2*(1-r/R)
    u = np.log(rhoR/y)/a
    lm = (r >= 1.2) & (r <= 2.93) & (u > 0)
    tx, ty = 1/f[lm]**2, 1/u[lm]
    linear.scatter(tx, ty, color=black, s=14, label='Log/reciprocal transformed data')
    xx = np.linspace(tx.min(), tx.max(), 300)
    linear.plot(xx, xx/(1+a*a)+a*a/(1+a*a), color=blue, label='Line implied by simple law')
    linear.set_xlabel(r'$1/f(r/R)^2$')
    linear.set_ylabel(r'$1/u$, where $u=\ln(\rho_R/\rho)/a$')
    linear.set_title('Linearizing check: deviations remain near the wall')
    linear.grid(alpha=.25)
    linear.legend(fontsize=8)

    residual.axhline(1, color='#777777', lw=.8)
    residual.plot(r, predicted/y, '.-', ms=3, color=blue, label='Simple model / data')
    residual.plot(r, reference_density/y, '--', lw=1, color=green, label='Detailed reference / data')
    residual.set_yscale('log')
    residual.set_ylabel('Predicted / measured density')
    residual.set_title('Tradeoff is explicit at the first jump and thin wall')
    radius_axis(residual)
    residual.legend(fontsize=8)

    centers = [(row['left']+row['right'])/2 for row in stats['bins']]
    windows.plot(centers, [row['rms_factor'] for row in stats['bins']], 'o-', color=blue, label='Simple model')
    windows.plot(centers, [row['rms_factor'] for row in reference_stats['bins']], 's--', color=green, label='Detailed reference')
    windows.axhline(1, color='#777777', lw=.8)
    windows.set_ylabel('Multiplicative RMS error factor')
    windows.set_title('Same error metric in six equal radial bins')
    radius_axis(windows)
    windows.legend(fontsize=8)
    fig.savefig(base.with_suffix('.png'), dpi=180, metadata={
        'Description': 'Purpose: Show a three-input endpoint-anchored density law, its shape compromises, and local errors against the retained detailed fit.'})
    plt.close(fig)
    inner_plot = args.output / 'test0098_density_inner_behavior.png'
    ir = np.geomspace(0.001, min(1.5, R), 1600)
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True, layout='constrained')
    for behavior, color, style, label in (
        ('original', '#c16644', '--', 'Original extrapolation'),
        ('flat', blue, '-', 'Flat inner limit (default)'),
        ('gentle', '#89944d', '-.', 'Gentle inner limit: r$^{-1}$'),
        ('wind', '#333333', ':', 'Free-wind-like inner limit: r$^{-2}$'),
    ):
        axes[0].plot(ir, density_profile(ir, R, rhoR, rho_min, behavior),
                     color=color, ls=style, lw=1.6, label=label)
        axes[1].plot(ir, density_log_slope(ir, R, rhoR, rho_min, behavior),
                     color=color, ls=style, lw=1.6)
    axes[0].set_yscale('log')
    axes[0].set_ylabel('Density [g cm$^{-3}$]')
    axes[0].set_title('Controlled inner extensions; fitted 1.16-2.955 pc section is unchanged')
    axes[0].legend(fontsize=9, loc='best')
    axes[1].axhline(-2, color='#888888', ls='--', lw=1, label='Steepest allowed negative index: -2')
    axes[1].axhline(0, color='#888888', lw=.8)
    axes[1].set_ylabel(r'Local index $d\ln\rho/d\ln r$')
    axes[1].set_ylim(-11, .8)
    axes[1].legend(fontsize=9, loc='lower left')
    for ax in axes:
        ax.set_xscale('log')
        ax.set_xlim(ir[0], ir[-1])
        ax.tick_params(axis='x', which='both', top=True, bottom=True, labeltop=True, labelbottom=True)
        ax.grid(True, which='major', alpha=.25)
        ax.grid(True, axis='x', which='minor', alpha=.12)
        if rb > 0:
            ax.axvline(rb, color='#888888', ls=':', lw=1)
    axes[0].set_xlabel(f'Radius [pc] | derived join radius = {rb:.3f} pc')
    axes[0].xaxis.set_label_position('top')
    axes[1].set_xlabel('Radius [pc]')
    fig.savefig(inner_plot, dpi=180, metadata={
        'Description': 'Purpose: Compare flat, r^-1 and r^-2 inner continuations and verify the logarithmic slope bound of -2.'})
    plt.close(fig)
    print('SUCCESS: only R, rho_R, and rho_min are independent inputs.')
    print(f'R={R:.12g} pc; rho_R={rhoR:.12e}; fitted rho_min={rho_min:.12e} g/cm^3; derived a={a:.12g}')
    print(f'Minimum radius={2*R/3:.9f} pc; measured={observed_minimum_r:.9f} pc')
    print(f'Median absolute error={stats["median_percent"]:.4f}%; P90={stats["p90_percent"]:.4f}%; worst factor={stats["worst_factor"]:.4f}; after first jump={postjump_worst:.4f}')
    print('Radial RMS factors:', [float(row['rms_factor']) for row in stats['bins']])
    print(f'Derived inner join={rb:.12g} pc; flat density at r=0={flat_origin:.12e}; fitted interval unchanged={rb < args.rmin}')
    print('Inner behavior plot:', inner_plot)
    print('Artifacts:', base.with_suffix('.png'), base.with_suffix('.txt'), base.with_suffix('.csv'), sep='\n')


if __name__ == '__main__':
    main()
