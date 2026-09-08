import math

import pytest

from jetfit.models.jet_energy import (
    core_gamma_profile_average,
    e_iso52_from_e_jet_core52,
    gamma0_axis_from_core_average,
    integrated_core_profile_beaming_fraction,
)


@pytest.mark.parametrize("jet_type", ["tophat", "gaussian", "powerlaw"])
def test_core_energy_round_trip(jet_type):
    theta_c = 0.2
    k_e = 2.7
    e_iso52 = 12.5
    fraction = integrated_core_profile_beaming_fraction(
        jet_type, theta_c, k_e=k_e
    )
    core_energy = e_iso52 * fraction
    recovered = e_iso52_from_e_jet_core52(
        core_energy,
        jet_type=jet_type,
        theta_c=theta_c,
        k_e=k_e,
    )
    assert recovered == pytest.approx(e_iso52, rel=2.0e-6)


@pytest.mark.parametrize("jet_type", ["tophat", "gaussian", "powerlaw"])
def test_core_gamma_round_trip(jet_type):
    theta_c = 0.2
    k_g = 3.1
    gamma_axis = 750.0
    profile_average = core_gamma_profile_average(
        jet_type, theta_c, k_g=k_g
    )
    gamma_core_average = 1.0 + (gamma_axis - 1.0) * profile_average
    recovered = gamma0_axis_from_core_average(
        gamma_core_average,
        jet_type=jet_type,
        theta_c=theta_c,
        k_g=k_g,
    )
    assert recovered == pytest.approx(gamma_axis, rel=2.0e-6)


def test_tophat_core_convention_is_two_sided():
    theta_c = 0.3
    expected = 1.0 - math.cos(theta_c)
    assert integrated_core_profile_beaming_fraction(
        "tophat", theta_c
    ) == pytest.approx(expected)
    assert core_gamma_profile_average("tophat", theta_c) == pytest.approx(1.0)
