//              __     __                            _      __  _                     _
//              \ \   / /___   __ _   __ _  ___     / \    / _|| |_  ___  _ __  __ _ | |  ___ __      __
//               \ \ / // _ \ / _` | / _` |/ __|   / _ \  | |_ | __|/ _ \| '__|/ _` || | / _ \\ \ /\ / /
//                \ V /|  __/| (_| || (_| |\__ \  / ___ \ |  _|| |_|  __/| |  | (_| || || (_) |\ V  V /
//                 \_/  \___| \__, | \__,_||___/ /_/   \_\|_|   \__|\___||_|   \__, ||_| \___/  \_/\_/
//                            |___/                                            |___/
#pragma once

#include "inverse-compton.h"

/**
 * <!-- ************************************************************************************** -->
 * @struct SmoothPowerLawSyn
 * @brief Represents synchrotron photons in the comoving frame and provides spectral functions.
 * @details This compiled implementation translates the analytic smoothed
 *          synchrotron spectrum used in the local AMPy/JetFit workflow into
 *          the native VegasAfterglow radiation path. The translation follows:
 *
 *          - Granot & Sari (2002), ApJ 568, 820, for the GS02 smoothing
 *            coefficients and their interpolation in external-medium slope.
 *          - Dylan A. Dutton, "An Environmental Origin for Diversity in
 *            Gamma-Ray Burst Afterglows," Ph.D. dissertation, University of
 *            North Carolina at Chapel Hill (2025), Chapter 5.3, plus the
 *            corresponding AMPy source implementation.
 *
 *          The goal here is fidelity to the original local spectral-smoothing
 *          prescription while moving evaluation out of the Python wrapper and
 *          into compiled C++ for speed and reproducibility.
 * <!-- ************************************************************************************** -->
 */
struct SmoothPowerLawSyn {
    // All values in comoving frame
    Real I_nu_max{0}; ///< Maximum specific synchrotron power PER SOLID ANGLE
    Real nu_m{0};     ///< Characteristic frequency corresponding to gamma_m
    Real nu_c{0};     ///< Cooling frequency corresponding to gamma_c
    Real nu_a{0};     ///< Self-absorption frequency
    Real nu_M{0};     ///< Maximum photon frequency
    Real p{2.3};      ///< Power-law index for the electron energy distribution
    Real k_eff{2.0};  ///< Local effective density slope used for GS02-style smoothing

    Real log2_I_nu_max{0}; ///< Log2 of I_nu_max (for computational efficiency)
    Real log2_nu_m{0};     ///< Log2 of nu_m
    Real log2_nu_c{0};     ///< Log2 of nu_c
    Real log2_nu_a{0};     ///< Log2 of nu_a
    Real log2_nu_M{0};     ///< Log2 of nu_M
    Real Y_c{0};           ///< Inverse Compton Y parameter at cooling frequency
    size_t regime{0};      ///< Regime indicator (1-6, determines spectral shape)
    InverseComptonY Ys;    ///< InverseComptonY parameters for this electron population
    /**
     * Descriptive native name for the historical AMPy / JetFit ``fts=True``
     * option. When true, apply the additional Dutton (2025) fast-to-slow
     * transition smoothing formula directly, mirroring the historical
     * explicit ``fts=True`` setting from the local workflow.
     */
    bool smooth_fast_to_slow_transition{false};

    /**
     * <!-- ************************************************************************************** -->
     * @brief Calculates the comoving synchrotron specific intensity.
     * @details Includes inverse Compton corrections for frequencies above the cooling frequency.
     * @param nu Frequency at which to compute the specific intensity
     * @return The synchrotron specific intensity at the specified frequency
     * <!-- ************************************************************************************** -->
     */
    [[nodiscard]] Real compute_I_nu(Real nu) const noexcept; ///< Linear power PER SOLID ANGLE

    /**
     * <!-- ************************************************************************************** -->
     * @brief Calculates the base-2 logarithm of comoving synchrotron specific intensity at a given frequency.
     * @details Optimized for numerical computation by using logarithmic arithmetic.
     * @param log2_nu Base-2 logarithm of the frequency
     * @return Base-2 logarithm of synchrotron specific intensity
     * <!-- ************************************************************************************** -->
     */
    [[nodiscard]] Real compute_log2_I_nu(Real log2_nu) const noexcept;

    /**
     * <!-- ************************************************************************************** -->
     * @brief Updates cached calculation constants used for efficiently computing synchrotron spectra.
     * @details Constants vary based on the electron regime (1-6) and involve different power laws.
     * <!-- ************************************************************************************** -->
     */
    void build() noexcept;

  private:
    Real inv_nu_M_{0};       ///< Cached 1/nu_M for division optimization
    Real log2_nu12_{0};      ///< Lower smoothed-break frequency in the AMPy prescription
    Real log2_nu23_{0};      ///< Upper smoothed-break frequency in the AMPy prescription
    Real b1_{1.0 / 3.0};     ///< Low-frequency spectral index
    Real b2a_{-0.5};         ///< Middle spectral index entering the first break
    Real b2b_{-0.5};         ///< Middle spectral index entering the second break
    Real b3_{-1.0};          ///< High-frequency spectral index
    Real s12_{1};            ///< Lower-break smoothing parameter
    Real s23_{1};            ///< Upper-break smoothing parameter
    Real mac_corr_log2_{0};  ///< Log2 correction for the m<a<c normalization
    Real cam_corr_log2_{0};  ///< Log2 correction for the c<a<m normalization
    bool mac_{false};        ///< True when nu_m < nu_a in slow cooling
    bool cam_{false};        ///< True when nu_c < nu_a in fast cooling

    /**
     * <!-- ************************************************************************************** -->
     * @brief Calculates the synchrotron spectrum at a given frequency based on the electron regime.
     * @details Implements the translated AMPy smoothed broken-power-law
     *          spectrum before the exponential cutoff and inverse-Compton
     *          correction are applied.
     * @param nu The frequency at which to compute the spectrum
     * @return The normalized synchrotron spectrum value
     * <!-- ************************************************************************************** -->
     */
    [[nodiscard]] Real compute_spectrum(Real nu) const noexcept;

    /**
     * <!-- ************************************************************************************** -->
     * @brief Calculates the base-2 logarithm of synchrotron spectrum at a given frequency.
     * @details Uses logarithmic arithmetic for numerical stability in different spectral regimes.
     * @param log2_nu Base-2 logarithm of the frequency
     * @return Base-2 logarithm of the synchrotron spectrum
     * <!-- ************************************************************************************** -->
     */
    [[nodiscard]] Real compute_log2_spectrum(Real log2_nu) const noexcept;
};
