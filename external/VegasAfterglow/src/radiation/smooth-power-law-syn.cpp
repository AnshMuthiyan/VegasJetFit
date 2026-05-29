//              __     __                            _      __  _                     _
//              \ \   / /___   __ _   __ _  ___     / \    / _|| |_  ___  _ __  __ _ | |  ___ __      __
//               \ \ / // _ \ / _` | / _` |/ __|   / _ \  | |_ | __|/ _ \| '__|/ _` || | / _ \\ \ /\ / /
//                \ V /|  __/| (_| || (_| |\__ \  / ___ \ |  _|| |_|  __/| |  | (_| || || (_) |\ V  V /
//                 \_/  \___| \__, | \__,_||___/ /_/   \_\|_|   \__|\___||_|   \__, ||_| \___/  \_/\_/
//                            |___/                                            |___/

#include "smooth-power-law-syn.h"

#include <algorithm>
#include <limits>

namespace {
inline Real regularize_smoothing(Real s) noexcept {
    if (!std::isfinite(s)) {
        return 1.0;
    }
    if (std::fabs(s) < 1e-12) {
        return (s < 0.0) ? -1e-12 : 1e-12;
    }
    return s;
}

inline Real log2_sum(Real a, Real b) noexcept {
    const Real hi = std::max(a, b);
    const Real lo = std::min(a, b);
    return hi + log2_softplus(lo - hi);
}

inline Real gs02_s12_slow(Real k, Real p) noexcept {
    return regularize_smoothing(1.84 - 0.040 * k - (0.40 - 0.010 * k) * p);
}

inline Real gs02_s23_slow(Real k, Real p) noexcept {
    return regularize_smoothing(1.15 - 0.125 * k - (0.06 - 0.015 * k) * p);
}

inline Real gs02_s12_mac(Real k, Real p) noexcept {
    return regularize_smoothing(1.47 - 0.11 * k - (0.21 - 0.015 * k) * p);
}

inline Real gs02_s12_fast(Real /*k*/, Real /*p*/) noexcept {
    return 0.597;
}

inline Real gs02_s23_fast(Real k, Real p) noexcept {
    return regularize_smoothing(3.34 + 0.17 * k - (0.82 + 0.035 * k) * p);
}

inline Real gs02_s12_cam() noexcept {
    return 0.9;
}

inline Real compute_transition_q(Real smoothing, Real b1, Real b3) noexcept {
    return regularize_smoothing(-smoothing * (b3 - b1));
}

inline Real transition_logistic(Real nu_ratio, Real q) noexcept {
    if (!(nu_ratio > 0.0) || !std::isfinite(nu_ratio)) {
        return 0.5;
    }
    return 1.0 / (1.0 + fast_pow(nu_ratio, q));
}
} // namespace

//========================================================================================================
//                                  SmoothPowerLawSyn Class Methods
//========================================================================================================
Real SmoothPowerLawSyn::compute_spectrum(Real nu) const noexcept {
    if (!(nu > 0.0)) {
        return 0.0;
    }
    return fast_exp2(compute_log2_spectrum(fast_log2(nu)));
}

Real SmoothPowerLawSyn::compute_log2_spectrum(Real log2_nu) const noexcept {
    if (!std::isfinite(log2_nu)) {
        return -std::numeric_limits<Real>::infinity();
    }

    // Translated from the AMPy / JetFit SpectralFluxModel.evaluate() path
    // used for Dylan Dutton's thesis workflow. The lower and upper smoothed
    // breaks are set in build() using the same regime logic as:
    //   BaseFluxModel.spectral_breaks()
    //   BaseFluxModel.spectral_indices()
    //   BaseFluxModel.smoothing()
    const Real log2_x12 = log2_nu - log2_nu12_;
    const Real log2_x23 = log2_nu - log2_nu23_;

    const Real term1 = (s23_ / s12_) * log2_softplus(-s12_ * (b1_ - b2a_) * log2_x12) - s23_ * b2a_ * log2_x12;
    const Real term2 = -s23_ * b2b_ * (log2_nu23_ - log2_nu12_) - s23_ * b3_ * log2_x23;

    Real log2_flux = -log2_sum(term1, term2) / s23_;

    if (mac_) {
        log2_flux += mac_corr_log2_;
    }
    if (cam_ && log2_nu > log2_nu_a) {
        log2_flux += cam_corr_log2_;
    }

    return log2_flux;
}

void SmoothPowerLawSyn::build() noexcept {
    log2_I_nu_max = (I_nu_max > 0.0) ? fast_log2(I_nu_max) : -std::numeric_limits<Real>::infinity();
    log2_nu_m = fast_log2(nu_m);
    log2_nu_c = fast_log2(nu_c);
    log2_nu_a = fast_log2(nu_a);
    log2_nu_M = fast_log2(nu_M);

    inv_nu_M_ = (nu_M > 0.0) ? (1.0 / nu_M) : 0.0;

    const bool slow = nu_m < nu_c;
    mac_ = slow && (nu_m < nu_a);
    cam_ = (!slow) && (nu_c < nu_a);

    log2_nu12_ = slow ? (mac_ ? log2_nu_a : log2_nu_m) : (cam_ ? log2_nu_a : log2_nu_c);
    log2_nu23_ = slow ? log2_nu_c : log2_nu_m;

    b1_ = 1.0 / 3.0;
    b2a_ = slow ? 0.5 * (1.0 - p) : -0.5;
    b2b_ = b2a_;
    b3_ = -0.5 * p;
    if (mac_) {
        b1_ = 2.5;
    }
    if (cam_) {
        b1_ = 2.0;
    }

    const Real k = std::isfinite(k_eff) ? k_eff : 2.0;
    const Real s12_base = slow ? gs02_s12_slow(k, p) : gs02_s12_fast(k, p);
    const Real s23_base = slow ? gs02_s23_slow(k, p) : gs02_s23_fast(k, p);
    s12_ = s12_base;
    s23_ = s23_base;
    if (mac_) {
        s12_ = gs02_s12_mac(k, p);
    }
    if (cam_) {
        s12_ = gs02_s12_cam();
    }

    // The AMPy / Dutton implementation has an optional fast-to-slow
    // transition smoother, historically toggled as ``fts=True``. Here we use
    // a descriptive native name but preserve the explicit historical
    // behavior: if the flag is enabled, apply the same local formulas at each
    // spectrum evaluation.
    if (smooth_fast_to_slow_transition) {
        const Real nu_ratio = nu_m / nu_c;
        const Real q12 = compute_transition_q(s12_, b1_, b3_);
        const Real q23 = compute_transition_q(s23_, b1_, b3_);
        const Real mix12 = transition_logistic(nu_ratio, q12);
        const Real mix23 = transition_logistic(nu_ratio, q23);

        const Real s12_slow = gs02_s12_slow(k, p);
        const Real s23_fast = gs02_s23_fast(k, p);
        const Real s23_slow = gs02_s23_slow(k, p);

        s12_ = regularize_smoothing(0.597 + (s12_slow - 0.597) * mix12);
        s23_ = regularize_smoothing(s23_fast + (s23_slow - s23_fast) * mix23);

        const Real slow_mid_index = 0.5 * (1.0 - p);
        b2a_ = -0.5 + (slow_mid_index + 0.5) * mix12;
        b2b_ = -0.5 + (slow_mid_index + 0.5) * mix23;
    }

    mac_corr_log2_ = mac_ ? b2a_ * (log2_nu_a - log2_nu_m) : 0.0;
    cam_corr_log2_ = cam_ ? (fast_log2(1.0 / 3.0) + 0.5 * (log2_nu_c - log2_nu_a)) : 0.0;
}

Real SmoothPowerLawSyn::compute_I_nu(Real nu) const noexcept {
    if (!(nu > 0.0)) {
        return 0.0;
    }
    if (nu <= nu_c) { // Below cooling frequency, simple scaling
        return fast_exp(-nu * inv_nu_M_) * I_nu_max * compute_spectrum(nu);
    } else {
        return fast_exp(-nu * inv_nu_M_) * I_nu_max * compute_spectrum(nu) * inverse_compton_correction(*this, nu);
    }
}

Real SmoothPowerLawSyn::compute_log2_I_nu(Real log2_nu) const noexcept {
    constexpr Real log2e = std::numbers::log2e;
    if (!std::isfinite(log2_nu)) {
        return -std::numeric_limits<Real>::infinity();
    }
    if (log2_nu <= log2_nu_c) { // Below cooling frequency, simple scaling
        return log2_I_nu_max + compute_log2_spectrum(log2_nu) - log2e * inv_nu_M_ * fast_exp2(log2_nu);
    } else {
        const Real nu = fast_exp2(log2_nu);
        return log2_I_nu_max + compute_log2_spectrum(log2_nu) - log2e * inv_nu_M_ * nu +
               fast_log2(inverse_compton_correction(*this, nu));
    }
}
