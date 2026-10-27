# Purpose: Find and document one smooth density law on test0098's 1.16--2.955 pc section, emphasizing its shape and local errors; overwrite fixed analysis outputs.
"""Empirical density fit for the final 40-Msun conduction/cooling snapshot."""
import argparse
import csv
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares, minimize, minimize_scalar
from scipy.special import expit

HERE = Path(__file__).resolve().parent
SCALE = 1e-24
# Coordinates: log(A/SCALE), log(q), Rc, log(w), log(epsilon), ri, log(wi).
SEED = np.array([np.log(0.75), np.log(0.54), 2.884, np.log(0.004),
                 np.log(1e-9), 1.1724, np.log(0.00386)])
LOWER = np.array([np.log(0.05), np.log(0.02), 2.70, np.log(1e-4),
                  np.log(1e-14), 1.155, np.log(1e-4)])
UPPER = np.array([np.log(10), np.log(5), 2.95, np.log(0.08),
                  np.log(1e-3), 1.195, np.log(0.03)])


def unpack(theta, minimum_radius):
    a, logq, rc, logw, logeps, ri, logwi = theta
    q, w, eps, wi = np.exp([logq, logw, logeps, logwi])
    dm = eps + w * np.logaddexp(0, (rc - minimum_radius) / w)
    # Enforce an exact stationary point at the measured interior minimum.
    p = minimum_radius * (q * expit((rc - minimum_radius) / w) / dm
                           + (1 - expit((minimum_radius - ri) / wi)) / wi)
    return dict(A_g_cm3=float(SCALE * np.exp(a)), p=float(p), q=float(q),
                Rc_pc=float(rc), w_pc=float(w), epsilon_pc=float(eps),
                ri_pc=float(ri), wi_pc=float(wi))


def log_profile(radius_pc, theta, minimum_radius):
    c = unpack(theta, minimum_radius)
    r = np.asarray(radius_pc, dtype=float)
    d = c['epsilon_pc'] + c['w_pc'] * np.logaddexp(0, (c['Rc_pc'] - r) / c['w_pc'])
    return (theta[0] - c['p'] * np.log(r) - c['q'] * np.log(d / c['Rc_pc'])
            - np.logaddexp(0, -(r - c['ri_pc']) / c['wi_pc']))


def density_profile(radius_pc, coefficients):
    """Evaluate the reported law; radius is numeric pc, return density in g/cm^3.

    This empirical fit is valid only on the reported snapshot/fit interval.
    """
    c = coefficients
    r = np.asarray(radius_pc, dtype=float)
    d = c['epsilon_pc'] + c['w_pc'] * np.logaddexp(0, (c['Rc_pc'] - r) / c['w_pc'])
    return np.exp(np.log(c['A_g_cm3']) - c['p'] * np.log(r)
                  - c['q'] * np.log(d / c['Rc_pc'])
                  - np.logaddexp(0, -(r - c['ri_pc']) / c['wi_pc']))


def metrics(log_prediction, log_data, widths, r, edges):
    delta = np.asarray(log_prediction) - log_data
    relative = np.expm1(delta)
    weights = widths / widths.sum()
    bins = []
    for i, (left, right) in enumerate(zip(edges[:-1], edges[1:])):
        mask = (r >= left) & (r < right if i < len(edges) - 2 else r <= right)
        w = widths[mask] / widths[mask].sum()
        bins.append(dict(left=float(left), right=float(right), cells=int(mask.sum()),
                         rms_percent=float(100 * np.sqrt(np.sum(w * relative[mask]**2))),
                         bias_percent=float(100 * np.sum(w * relative[mask])),
                         rms_dex=float(np.sqrt(np.sum(w * (delta[mask] / np.log(10))**2)))))
    return dict(rms_percent=float(100 * np.sqrt(np.sum(weights * relative**2))),
                max_percent=float(100 * np.max(np.abs(relative))),
                max_log_error=float(np.max(np.abs(delta))), bins=bins)


def fit_models(r, y, widths, minimum_radius):
    z = np.log(y / SCALE)
    weights = widths / widths.sum()
    residual = lambda t: log_profile(r, t, minimum_radius) - z
    ls = least_squares(lambda t: np.sqrt(weights) * residual(t), SEED,
                       bounds=(LOWER, UPPER), max_nfev=5000,
                       ftol=1e-12, xtol=1e-12, gtol=1e-12)
    if not ls.success:
        raise RuntimeError('Shape-constrained least-squares fit did not converge: ' + ls.message)
    initial = np.r_[ls.x, np.max(np.abs(residual(ls.x))) + 1e-9]

    def constraints(v):
        e = residual(v[:-1])
        return np.r_[v[-1] - e, v[-1] + e]

    optimum = minimize(lambda v: v[-1], initial, method='SLSQP',
                       bounds=list(zip(LOWER, UPPER)) + [(0, 5)],
                       constraints={'type': 'ineq', 'fun': constraints},
                       options={'maxiter': 2000, 'ftol': 1e-11})
    if not optimum.success or np.min(constraints(optimum.x)) < -1e-6:
        raise RuntimeError('Worst-error fit did not converge: ' + optimum.message)
    if np.max(np.abs(residual(optimum.x[:-1]))) > np.max(np.abs(residual(ls.x))) + 1e-6:
        raise RuntimeError('Worst-error fit failed to improve the worst error')

    def linear_fit(design):
        beta = np.linalg.lstsq(design * np.sqrt(weights[:, None]), z * np.sqrt(weights), rcond=None)[0]
        return design @ beta, beta

    exponential, exponential_beta = linear_fit(np.c_[np.ones(len(r)), r])
    power, power_beta = linear_fit(np.c_[np.ones(len(r)), np.log(r)])
    quadratic, quadratic_beta = linear_fit(np.c_[np.ones(len(r)), r - 1.9, (r - 1.9)**2])

    def singular_product(loggap):
        rc = r.max() + np.exp(loggap)
        prediction, beta = linear_fit(np.c_[np.ones(len(r)), -np.log(r), -np.log1p(-r / rc)])
        return np.sum(weights * (prediction - z)**2), prediction, beta, rc

    singular_opt = minimize_scalar(lambda v: singular_product(v)[0],
                                   bounds=(np.log(1e-8), np.log(100)), method='bounded')
    _, singular, singular_beta, singular_rc = singular_product(singular_opt.x)
    predictions = {'recommended': log_profile(r, optimum.x[:-1], minimum_radius),
                   'same_law_least_squares': log_profile(r, ls.x, minimum_radius),
                   'single_exponential': exponential, 'single_power_law': power,
                   'quadratic_exponential': quadratic, 'unregularized_product': singular}
    return optimum.x[:-1], ls.x, predictions, dict(
        exponential=exponential_beta, power=power_beta,
        quadratic_exponential=quadratic_beta,
        unregularized_product=np.r_[singular_beta, singular_rc])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=HERE / 'output/test0098_density_profile.csv')
    parser.add_argument('--output', type=Path, default=HERE / 'output')
    parser.add_argument('--rmin', type=float, default=1.16)
    parser.add_argument('--rmax', type=float, default=2.955)
    args = parser.parse_args()
    # No dated folders: repeated analyses replace these same successful artifacts.
    if not args.output.is_dir():
        raise ValueError('Reuse the existing output folder; it must already exist')
    raw = np.genfromtxt(args.input, delimiter=',', names=True, skip_header=1)
    all_r, all_y = raw['radius_pc'], raw['density_g_cm3']
    # The requested outer radius is rounded to 3 decimals; include its matching cell.
    outer = int(np.argmin(np.abs(all_r - args.rmax)))
    endpoint = float(all_r[outer]) if abs(all_r[outer] - args.rmax) <= 0.0005 else args.rmax
    mask = (all_r >= args.rmin) & (all_r <= max(args.rmax, endpoint))
    r, y = all_r[mask], all_y[mask]
    widths = np.minimum(raw['r_outer_pc'][mask], max(args.rmax, endpoint)) - np.maximum(raw['r_inner_pc'][mask], args.rmin)
    if len(r) < 20 or np.any(y <= 0) or not np.all(np.isfinite(y)):
        raise ValueError('Insufficient valid positive density data')
    hot = np.flatnonzero((all_r > 1.3) & (all_r < 2.6))
    j = hot[np.argmin(all_y[hot])]
    polynomial = np.polyfit(all_r[j-1:j+2], np.log(all_y[j-1:j+2]), 2)
    minimum_radius = float(-polynomial[1] / (2 * polynomial[0]))
    measured_minimum_density = float(np.exp(np.polyval(polynomial, minimum_radius)))
    theta, theta_ls, predictions, other_coefficients = fit_models(r, y, widths, minimum_radius)
    coefficients = unpack(theta, minimum_radius)
    bin_edges = np.linspace(args.rmin, max(args.rmax, endpoint), 7)
    z = np.log(y / SCALE)
    scores = {name: metrics(prediction, z, widths, r, bin_edges) for name, prediction in predictions.items()}
    predicted = density_profile(r, coefficients)
    # Check that the exported formula and fitted log formula agree and retain a minimum.
    assert np.allclose(predicted, SCALE * np.exp(predictions['recommended']), rtol=1e-12)
    rr = np.array([minimum_radius - 1e-4, minimum_radius, minimum_radius + 1e-4])
    vv = density_profile(rr, coefficients)
    assert vv[1] < vv[0] and vv[1] < vv[2]

    prefix = args.output / 'test0098_density_function'
    with prefix.with_suffix('.csv').open('w', newline='') as stream:
        stream.write('# Purpose: Selected test0098 density data, the successful shape-constrained fit, and pointwise fractional errors.\n')
        writer = csv.writer(stream)
        writer.writerow(['radius_pc', 'density_g_cm3', 'fitted_density_g_cm3', 'relative_error_percent', 'cell_radial_weight_pc'])
        for row in zip(r, y, predicted, 100 * (predicted / y - 1), widths):
            writer.writerow([format(float(v), '.17g') for v in row])

    lines = [
        '# Purpose: Explain the successful empirical test0098 density law, its transformations, and error consistency over the corrected radius interval.',
        '', 'SOURCE AND INTERVAL',
        f'Source: {args.input.resolve()}',
        'Snapshot: test0098.dat; age 4.77 Myr; conduction and radiative cooling on.',
        f'Requested radii: {args.rmin:.12g} to {args.rmax:.12g} pc.',
        f'Used {len(r)} active-cell centers: {r[0]:.12g} to {r[-1]:.12g} pc.',
        'The endpoint 2.955 pc is interpreted as the rounded cell center 2.95504889729 pc.',
        'Fits describe finite-volume cell densities evaluated at their radial centers.',
        '', 'RECOMMENDED SINGLE SMOOTH FORM',
        'Let x = r/(1 pc), with every radius parameter below also numeric in pc.',
        'S(x) = 1 / [1 + exp(-(x-ri)/wi)]',
        'D(x) = epsilon + w*ln[1 + exp((Rc-x)/w)]',
        'rho(x) = A*x^(-p)*[D(x)/Rc]^(-q)*S(x), in g/cm^3.',
    ]
    lines += [f'{key} = {value:.14g}' for key, value in coefficients.items()]
    lines += [
        '', f'Interior minimum fixed at {minimum_radius:.12g} pc using a 3-point quadratic in log density.',
        f'Data minimum density: {measured_minimum_density:.12e} g/cm^3.',
        f'Model density there: {float(density_profile(minimum_radius, coefficients)):.12e} g/cm^3.',
        '', 'TRANSFORMATIONS AND WHY THIS SHAPE',
        'Once the first jump is crossed, S is almost 1. Before the rapid outer rise,',
        'D is almost Rc-x. Thus rho is approximately A*x^(-p)*(1-x/Rc)^(-q).',
        'Its decline and rise meet at the observed interior density minimum.',
        'The inverse transformation D_data=Rc*[rho*x^p/(A*S)]^(-1/q) is approximately',
        'the straight line Rc-x over the smooth interior. The plot checks this directly.',
        'Past Rc, when epsilon is still negligible, D is approximately w*exp((Rc-x)/w):',
        'rho is approximately A*x^(-p)*(w/Rc)^(-q)*exp(q*(x-Rc)/w).',
        'This supplies an exponential-like wall rise; epsilon removes the artificial singularity.',
        'The first sigmoid reproduces the resolved inner jump at the start of the interval.',
        '', 'FITTING AND LOCAL SHAPE',
        'The recommended fit minimizes max(abs(ln(model/data))) over all selected cells.',
        'The exponent p is derived to force d(ln rho)/dx=0 at the measured interior minimum.',
        'RMS values use clipped radial cell widths, preventing mesh refinement from dominating.',
        'Relative error is 100*(model/data-1); signed bias and RMS are checked in six equal radial bins.',
        'These are deterministic approximation errors, not observational uncertainties.',
        '', 'MODEL COMPARISON: width-weighted relative RMS %, worst relative error %',
    ]
    for name, score in scores.items():
        lines.append(f'{name:28s} RMS={score["rms_percent"]:9.4f}%  worst={score["max_percent"]:10.4f}%')
    lines += ['', 'RADIAL BINS FOR THE RECOMMENDED MODEL: left, right, cells, RMS %, signed bias %, RMS dex']
    for row in scores['recommended']['bins']:
        lines.append(f'{row["left"]:.6f} {row["right"]:.6f} {row["cells"]:3d} {row["rms_percent"]:.6f} {row["bias_percent"]:+.6f} {row["rms_dex"]:.6f}')
    lines += [
        '', 'LIMITS',
        'Use this empirical formula only on this snapshot and the fitted 1.16--2.955 pc interval.',
        'Rc, w and epsilon are coupled shape parameters, not independently measured interface properties.',
        'The rapid wall is sampled by only a few cells. Subcell fit widths are not resolved physical widths.',
        'Error is not exactly constant with radius: the bin table exposes its variation.',
        'The upper edge includes cold 100 K shell gas; the fitted q is not a universal conduction exponent.',
        'Compute the softplus using numpy.logaddexp(0,(Rc-x)/w) to avoid overflow.',
        'No time evolution, causal physical derivation, or accuracy outside this interval is claimed.',
        '', 'REPRODUCE', f'python "{Path(__file__).resolve()}"',
    ]
    prefix.with_suffix('.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FixedLocator, FuncFormatter, LogLocator, NullFormatter
    fig = plt.figure(figsize=(13, 13), layout='constrained')
    gs = fig.add_gridspec(3, 2, height_ratios=[1.25, 1, 0.9])
    full = fig.add_subplot(gs[0, :])
    hotax = fig.add_subplot(gs[1, 0])
    transform = fig.add_subplot(gs[1, 1])
    residual_ax = fig.add_subplot(gs[2, 0])
    binax = fig.add_subplot(gs[2, 1])
    dense = np.linspace(args.rmin, args.rmax, 3000)
    curve = density_profile(dense, coefficients)
    navy, red, gray = '#176b8e', '#c95b36', '#333333'

    def radius_axis(ax, lo=args.rmin, hi=args.rmax):
        ax.set_xscale('log')
        ax.set_xlim(lo, hi)
        ax.xaxis.set_major_locator(FixedLocator([x for x in [1.2, 1.5, 2, 2.5, 2.955] if lo <= x <= hi]))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:g}'))
        ax.xaxis.set_minor_locator(LogLocator(base=10, subs=np.arange(1.1, 10, 0.1)))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.tick_params(axis='x', which='both', top=True, labeltop=True, bottom=True, labelbottom=True)
        ax.grid(True, which='major', alpha=0.25)
        ax.grid(True, which='minor', axis='x', alpha=0.12)
        ax.set_xlabel('Radius [pc], logarithmic scale')

    full.scatter(r, y, color=gray, s=13, label='Snapshot cell centers', zorder=3)
    full.plot(dense, curve, color=navy, lw=2, label='Recommended shape-constrained minimax law')
    full.plot(r, SCALE * np.exp(predictions['single_exponential']), '--', color=red, lw=1.1, label='Single exponential: misses the shape')
    full.fill_between(dense, curve * np.exp(-scores['recommended']['max_log_error']),
                      curve * np.exp(scores['recommended']['max_log_error']), color=navy, alpha=0.12,
                      label='Uniform worst-error envelope')
    full.set_yscale('log')
    full.set_ylim(y.min() * 0.6, y.max() * 2)
    radius_axis(full)
    full.xaxis.set_label_position('top')
    full.set_ylabel('Mass density [g cm$^{-3}$]')
    full.set_title('test0098 | age 4.77 Myr | corrected interval 1.16-2.955 pc', fontsize=13)
    full.legend(fontsize=9, loc='upper left')

    hm = (r >= 1.20) & (r <= 2.8458)
    hotax.scatter(r[hm], y[hm] / SCALE, s=12, color=gray, label='Data')
    hd = dense[(dense >= 1.20) & (dense <= 2.8458)]
    hotax.plot(hd, density_profile(hd, coefficients) / SCALE, color=navy, lw=2)
    hotax.axvline(minimum_radius, color='#999999', ls=':', lw=1)
    hotax.set_ylabel(r'Density / $10^{-24}$ g cm$^{-3}$')
    hotax.set_title('Interior density zoom: preserve the minimum')
    radius_axis(hotax, 1.20, 2.8458)

    s_inner = expit((r[hm] - coefficients['ri_pc']) / coefficients['wi_pc'])
    inverse = coefficients['Rc_pc'] * (y[hm] * r[hm]**coefficients['p'] / (coefficients['A_g_cm3'] * s_inner))**(-1 / coefficients['q'])
    transform.scatter(r[hm], inverse, s=12, color=gray, label='Transformed data')
    transform.plot(r[hm], coefficients['Rc_pc'] - r[hm], color=navy, label='$R_c-r$: straight line')
    transform.set_xlabel('Radius [pc], linear scale for this check')
    transform.set_ylabel(r'$R_c[\rho r^p/(A S)]^{-1/q}$ [pc]')
    transform.set_title('Log/power inversion reveals an almost straight line')
    transform.grid(alpha=0.25)
    transform.legend(fontsize=8)

    residual_ax.axhline(0, color='#777777', lw=0.8)
    residual_ax.plot(r, 100 * np.expm1(predictions['same_law_least_squares'] - z), color='#ba8c5e', lw=1,
                     label='Average-error fit')
    residual_ax.plot(r, 100 * (predicted / y - 1), '.-', color=navy, ms=3, lw=1, label='Recommended worst-error fit')
    residual_ax.set_ylabel('Pointwise relative error [%]')
    residual_ax.set_title('No hidden high-error radial section')
    radius_axis(residual_ax)
    residual_ax.legend(fontsize=8)

    rows = scores['recommended']['bins']
    centers = [(row['left'] + row['right']) / 2 for row in rows]
    binax.plot(centers, [row['rms_percent'] for row in rows], 'o-', color=navy, label='RMS fractional error')
    binax.plot(centers, [row['bias_percent'] for row in rows], 's--', color=red, label='Signed bias')
    binax.axhline(0, color='#777777', lw=0.8)
    binax.set_ylabel('Radial-width-weighted error [%]')
    binax.set_title('Same metric in six equal radial windows')
    radius_axis(binax)
    binax.legend(fontsize=8)
    fig.savefig(prefix.with_suffix('.png'), dpi=180, metadata={
        'Description': 'Purpose: Compare the successful single density law, inverted data, pointwise residuals and equal-radius-window errors.'})
    plt.close(fig)
    print('SUCCESS: corrected interval', args.rmin, args.rmax, 'pc;', len(r), 'cells')
    print('Coefficients:', coefficients)
    print('Interior minimum:', minimum_radius, 'pc')
    print('Recommended relative RMS/worst:', scores['recommended']['rms_percent'], scores['recommended']['max_percent'])
    print('Six radial-bin RMS %:', [row['rms_percent'] for row in rows])
    print('Least-squares relative RMS/worst:', scores['same_law_least_squares']['rms_percent'], scores['same_law_least_squares']['max_percent'])
    print('Artifacts:', prefix.with_suffix('.png'), prefix.with_suffix('.txt'), prefix.with_suffix('.csv'), sep='\n')


if __name__ == '__main__':
    main()
