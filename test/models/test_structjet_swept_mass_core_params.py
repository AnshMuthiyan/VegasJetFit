from scripts.plot_structjet_swept_mass_diagnostics import (
    resolve_structjet_e_iso52,
    resolve_structjet_gamma0_axis,
)


def test_swept_mass_resolvers_accept_core_fit_parameters():
    params = {
        "E_j_core_52": 1.0,
        "Gamma_0_core_avg": 300.0,
        "theta_c": 0.1,
        "k_e": 2.0,
        "k_g": 2.0,
    }

    assert resolve_structjet_e_iso52(params) > 0.0
    assert resolve_structjet_gamma0_axis(params) > params["Gamma_0_core_avg"]


def test_swept_mass_resolvers_preserve_legacy_fit_parameters():
    params = {
        "E_j_52": 1.0,
        "lf0": 300.0,
        "theta_c": 0.1,
        "k_e": 2.0,
        "k_g": 2.0,
    }

    assert resolve_structjet_e_iso52(params) > 0.0
    assert resolve_structjet_gamma0_axis(params) == params["lf0"]
