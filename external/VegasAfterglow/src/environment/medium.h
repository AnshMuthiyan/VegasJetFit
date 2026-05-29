//              __     __                            _      __  _                     _
//              \ \   / /___   __ _   __ _  ___     / \    / _|| |_  ___  _ __  __ _ | |  ___ __      __
//               \ \ / // _ \ / _` | / _` |/ __|   / _ \  | |_ | __|/ _ \| '__|/ _` || | / _ \\ \ /\ / /
//                \ V /|  __/| (_| || (_| |\__ \  / ___ \ |  _|| |_|  __/| |  | (_| || || (_) |\ V  V /
//                 \_/  \___| \__, | \__,_||___/ /_/   \_\|_|   \__|\___||_|   \__, ||_| \___/  \_/\_/
//                            |___/                                            |___/

#pragma once
#include <algorithm>
#include <cmath>
#include <utility>
#include <variant>

#include "../util/macros.h"
#include "../util/utilities.h"
/**
 * <!-- ************************************************************************************** -->
 * @class Medium
 * @brief Represents the generic medium or any user-defined surrounding medium that the GRB jet interacts with.
 * @details The class provides methods to compute the density (rho) as a function of position (phi, theta, r).
 * <!-- ************************************************************************************** -->
 */
class Medium {
  public:
    /**
     * <!-- ************************************************************************************** -->
     * @brief Constructor: Initialize with density function
     * @param rho Density function
     * @param isotropic Flag indicating if the medium is isotropic within computational domain.
     * <!-- ************************************************************************************** -->
     */
    explicit Medium(TernaryFunc rho, bool isotropic = false) noexcept : rho(std::move(rho)), isotropic(isotropic) {}

    Medium() = default;

    /// Density function that returns the mass density at a given position (phi, theta, r)
    /// The function is initialized to zero by default
    TernaryFunc rho{func::zero_3d};

    bool isotropic{false}; ///< Flag indicating if the medium is isotropic within computational domain.
};

/**
 * <!-- ************************************************************************************** -->
 * @class ISM
 * @brief Implements a uniform interstellar medium (ISM) with constant density.
 * @details Provides methods to compute density at any position.
 *          The ISM is characterized by the particle number density n_ism.
 * <!-- ************************************************************************************** -->
 */
class ISM {
  public:
    /**
     * <!-- ************************************************************************************** -->
     * @brief Constructor: Initialize with particle number density in cm^-3
     * @param n_ism Particle number density in cm^-3
     * <!-- ************************************************************************************** -->
     */
    explicit ISM(Real n_ism) noexcept : rho_(n_ism * con::mp) {}

    /**
     * <!-- ************************************************************************************** -->
     * @brief Return density at a given position (constant everywhere)
     * @param phi Azimuthal angle (unused)
     * @param theta Polar angle (unused)
     * @param r Radial distance (unused)
     * @return Constant density value
     * <!-- ************************************************************************************** -->
     */
    [[nodiscard]] inline Real rho(Real /*phi*/, Real /*theta*/, Real /*r*/) const noexcept { return rho_; }

    /// Enclosed mass per solid angle up to radius r.
    [[nodiscard]] inline Real mass(Real r) const noexcept { return rho_ * r * r * r / 3.0; }

    bool isotropic{true}; ///< Flag indicating if the medium is isotropic within computational domain.

  private:
    Real rho_{0}; ///< Mass density (particle number density × proton mass)
};

/**
 * <!-- ************************************************************************************** -->
 * @class Wind
 * @brief Implements a stellar wind medium with density proportional to 1/r².
 * @details Provides methods to compute density at any position.
 *          The wind is characterized by the wind parameter A_star.
 * <!-- ************************************************************************************** -->
 */
class Wind {
  public:
    /**
     * <!-- ************************************************************************************** -->
     * @brief Constructor: Initialize with wind parameter A_star (in standard units)
     * @param A_star Wind density parameter in standard units
     * @param n_ism number density of ISM at large radii
     * @param n0 number density of wind at small radii
     * <!-- ************************************************************************************** -->
     */
    explicit Wind(Real A_star, Real n_ism = 0, Real n0 = con::inf, Real k = 2) noexcept
        : A(A_star * 5e11 * unit::g / unit::cm * std::pow(1e17 * unit::cm, k - 2)),
          rho_ism(n_ism * con::mp),
          r0k_(A / (n0 * 1.3 * con::mp)),
          k_(k) {}

    /**
     * <!-- ************************************************************************************** -->
     * @brief Return density at given positions (proportional to r^{-k})
     * @param phi Azimuthal angle (unused)
     * @param theta Polar angle (unused)
     * @param r Radial distance
     * @return Density value at radius r (= A/(r0k + r^k) + rho_ism)
     * <!-- ************************************************************************************** -->
     */

    [[nodiscard]] inline Real rho(Real /*phi*/, Real /*theta*/, Real r) const noexcept {
        return A / (r0k_ + std::pow(r, k_)) + rho_ism;
    }

    /// Enclosed mass per solid angle up to radius r.
    [[nodiscard]] inline Real mass(Real r) const noexcept {
        if (!(r > 0)) {
            return 0;
        }
        Real m = rho_ism * r * r * r / 3.0;
        if (A != 0) {
            if (r0k_ == 0) {
                const Real denom = 3 - k_;
                if (std::fabs(denom) > 1e-12) {
                    m += A * std::pow(r, denom) / denom;
                } else {
                    // k -> 3 limit: integral tends to A * ln(r/r_min)
                    const Real r_min = std::max(r * std::exp(-18.0), 1e-30 * unit::cm);
                    m += A * std::log(r / r_min);
                }
            } else if (std::fabs(k_ - 2.0) < 1e-12) {
                const Real a = std::sqrt(r0k_);
                m += A * (r - a * std::atan(r / a));
            } else {
                // General softened profile: Simpson integration in log-space.
                constexpr size_t N = 32;
                const Real u_max = std::log(r);
                const Real u_min = u_max - 18;
                const Real h = (u_max - u_min) / N;
                auto f = [&](Real u) noexcept {
                    const Real ri = std::exp(u);
                    return ri * ri * ri / (r0k_ + std::pow(ri, k_));
                };
                Real sum = f(u_min) + f(u_max);
                for (size_t i = 1; i < N; i += 2) {
                    sum += 4 * f(u_min + i * h);
                }
                for (size_t i = 2; i < N; i += 2) {
                    sum += 2 * f(u_min + i * h);
                }
                m += A * sum * h / 3;
            }
        }
        return m;
    }

    /// Expose parameters for analytic integrals in hot dynamics setup paths.
    [[nodiscard]] inline Real A_param() const noexcept { return A; }
    [[nodiscard]] inline Real rho_ism_param() const noexcept { return rho_ism; }
    [[nodiscard]] inline Real r0k_param() const noexcept { return r0k_; }
    [[nodiscard]] inline Real k_param() const noexcept { return k_; }
    // Backward-compat alias (historical k=2 notation).
    [[nodiscard]] inline Real r02_param() const noexcept { return r0k_; }

    bool isotropic{true}; ///< Flag indicating if the medium is isotropic within computational domain.

  private:
    Real A{0};       ///< Wind density normalization in physical units
    Real rho_ism{0}; ///< ISM density floor
    Real r0k_{0};    ///< Softcore scale in units of r^k
    Real k_{2};      ///< Density power-law slope: rho \propto r^{-k}
};

/**
 * <!-- ************************************************************************************** -->
 * @class SmoothBrokenPowerLaw
 * @brief Isotropic smoothly broken power-law external medium profile.
 * @details Number density is parameterized by (n_t, r_t, k1, k2, s_n) and converted
 *          to mass density assuming a hydrogen mass fraction X_h.
 * <!-- ************************************************************************************** -->
 */
class SmoothBrokenPowerLaw {
  public:
    explicit SmoothBrokenPowerLaw(Real n_t, Real r_t, Real k1, Real k2, Real s_n, Real X_h = 0.7) noexcept
        : rho_t_(n_t * X_h * con::mp), r_t_(r_t), k1_(k1), k2_(k2), s_n_(s_n) {}

    [[nodiscard]] inline Real rho(Real /*phi*/, Real /*theta*/, Real r) const noexcept {
        if (!(r > 0) || !(r_t_ > 0) || !(rho_t_ > 0)) {
            return 0;
        }
        const Real x = std::max(r / r_t_, 1e-30);
        const Real inv_s = 1.0 / s_n_;
        const Real log_x = std::log(x);
        const Real xk1s = std::exp(k1_ * s_n_ * log_x);
        const Real xk2s = std::exp(k2_ * s_n_ * log_x);
        const Real denom = std::pow(xk1s + xk2s, inv_s);
        if (!(denom > 0) || !std::isfinite(denom)) {
            return 0;
        }
        const Real k_eff = (k1_ * xk1s + k2_ * xk2s) / (xk1s + xk2s);
        const Real n = std::pow(2.0, inv_s) / denom;
        const Real n0 = n * std::exp(k_eff * log_x);
        return rho_t_ * n0;
    }

    bool isotropic{true};

  private:
    Real rho_t_{0};
    Real r_t_{1};
    Real k1_{2};
    Real k2_{0};
    Real s_n_{1};
};

/// Type-erased medium variant for optimized dispatch in the ODE hot loop.
/// ISM and Wind have inline rho() methods; Medium uses std::function as fallback.
using MediumVariant = std::variant<ISM, Wind, SmoothBrokenPowerLaw, Medium>;

/// Helper: evaluate rho on a MediumVariant (for non-hot-path code)
inline Real medium_rho(MediumVariant const& mv, Real phi, Real theta, Real r) {
    return std::visit([&](auto const& m) { return m.rho(phi, theta, r); }, mv);
}

template <typename MediumT>
inline Real medium_local_k(MediumT const& medium, Real phi, Real theta, Real r) {
    const Real r_safe = std::max(r, 1e-30 * unit::cm);
    const Real r_lo = std::max(r_safe * 0.95, 1e-30 * unit::cm);
    const Real r_hi = r_safe * 1.05;

    const Real rho_lo = medium.rho(phi, theta, r_lo);
    const Real rho_hi = medium.rho(phi, theta, r_hi);
    if (!(rho_lo > 0) || !(rho_hi > 0) || !std::isfinite(rho_lo) || !std::isfinite(rho_hi)) {
        return 2.0;
    }

    const Real log_r_span = std::log(r_hi) - std::log(r_lo);
    if (log_r_span == 0) {
        return 2.0;
    }

    const Real k_eff = -(std::log(rho_hi) - std::log(rho_lo)) / log_r_span;
    return std::isfinite(k_eff) ? k_eff : 2.0;
}

inline Real medium_local_k(MediumVariant const& mv, Real phi, Real theta, Real r) {
    return std::visit([&](auto const& m) { return medium_local_k(m, phi, theta, r); }, mv);
}

/**
 * <!-- ************************************************************************************** -->
 * @namespace evn
 * @brief Provides functions to create different types of ambient medium profiles.
 * @details These functions return lambda functions that compute the density at any given position.
 * <!-- ************************************************************************************** -->
 */
namespace evn {
    /**
     * <!-- ************************************************************************************** -->
     * @brief Creates a uniform interstellar medium (ISM) profile
     * @param n_ism Number density of particles in cm^-3
     * @return function for density
     * <!-- ************************************************************************************** -->
     */
    inline auto ISM(Real n_ism) {
        const Real rho = n_ism * con::mp;

        return [=](Real /*phi*/, Real /*theta*/, Real /*r*/) noexcept { return rho; };
    };

    /**
     * <!-- ************************************************************************************** -->
     * @brief Creates a stellar wind medium profile
     * @param A_star Wind parameter in standard units
     * @param n_ism Number density of the ISM [cm^-3]
     * @param n0 Number density of inner region [cm^-3]
     * @param k power-law index
     * @return functions for density calculation
     * @details Converts A_star to proper units (A_star * 5e11 g/cm) and returns functions that compute
     *          density = A/r² and mass = A*r, representing a steady-state stellar wind where density
     *          falls off as 1/r²
     * <!-- ************************************************************************************** -->
     */
    inline auto wind(Real A_star, Real n_ism = 0, Real n0 = con::inf, Real k = 2) {
        // Convert A_star to proper units: A_star * 5e11 g/cm
        constexpr Real r0 = 1e17 * unit::cm; // reference radius
        const Real A = A_star * 5e11 * unit::g / unit::cm * std::pow(r0, k - 2);
        const Real rho_ism = n_ism * con::mp;
        const Real r0k = A / (n0 * 1.3 * con::mp);

        // Return a function that computes density = A/r^k
        // This represents a steady-state stellar wind where density falls off as 1/r^k
        return [=](Real /*phi*/, Real /*theta*/, Real r) noexcept { return A / (r0k + std::pow(r, k)) + rho_ism; };
    }
} // namespace evn
