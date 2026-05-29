//              __     __                            _      __  _                     _
//              \ \   / /___   __ _   __ _  ___     / \    / _|| |_  ___  _ __  __ _ | |  ___ __      __
//               \ \ / // _ \ / _` | / _` |/ __|   / _ \  | |_ | __|/ _ \| '__|/ _` || | / _ \\ \ /\ / /
//                \ V /|  __/| (_| || (_| |\__ \  / ___ \ |  _|| |_|  __/| |  | (_| || || (_) |\ V  V /
//                 \_/  \___| \__, | \__,_||___/ /_/   \_\|_|   \__|\___||_|   \__, ||_| \___/  \_/\_/
//                            |___/                                            |___/

#include "physics.h"

#include <algorithm>

namespace physics::scales {

    Real dec_radius(Real E_iso, Real n0, Real Gamma0, Real engine_dura, Real k, Real r0) {
        return std::max(thin_shell_dec_radius(E_iso, n0, Gamma0, k, r0),
                        thick_shell_dec_radius(E_iso, n0, engine_dura, k, r0));
    }

    Real thin_shell_dec_radius(Real E_iso, Real n0, Real Gamma0, Real k, Real r0) {
        const Real denom = 3 - k;
        if (!(denom > 0) || !(n0 > 0) || !(Gamma0 > 0) || !(r0 > 0)) {
            return con::inf;
        }
        const Real r0k = std::pow(r0, k);
        const Real inner = denom * E_iso / (4 * con::pi * con::mp * con::c2 * n0 * r0k * Gamma0 * Gamma0);
        return std::pow(inner, 1.0 / denom);
    }

    Real thick_shell_dec_radius(Real E_iso, Real n0, Real engine_dura, Real k, Real r0) {
        const Real denom = 4 - k;
        if (!(denom > 0) || !(n0 > 0) || !(engine_dura > 0) || !(r0 > 0)) {
            return con::inf;
        }
        const Real r0k = std::pow(r0, k);
        const Real inner = (3 - k) * E_iso * engine_dura * con::c / (4 * con::pi * con::mp * con::c2 * n0 * r0k);
        return std::pow(inner, 1.0 / denom);
    }

    Real shell_spreading_radius(Real Gamma0, Real engine_dura) {
        return Gamma0 * Gamma0 * con::c * engine_dura;
    }

    Real RS_transition_radius(Real E_iso, Real n_ism, Real Gamma0, Real engine_dura) {
        return std::pow(sedov_length(E_iso, n_ism), 1.5) / std::sqrt(con::c * engine_dura) / Gamma0 / Gamma0;
    }

    Real shell_thickness_param(Real E_iso, Real n_ism, Real Gamma0, Real engine_dura) {
        const Real Sedov_l = sedov_length(E_iso, n_ism);
        const Real shell_width = con::c * engine_dura;
        return std::sqrt(Sedov_l / shell_width) * std::pow(Gamma0, -4. / 3);
    }

    Real calc_engine_duration(Real E_iso, Real n_ism, Real Gamma0, Real xi) {
        const Real Sedov_l = sedov_length(E_iso, n_ism);
        return Sedov_l / (xi * xi * std::pow(Gamma0, 8. / 3) * con::c);
    }

} // namespace physics::scales
