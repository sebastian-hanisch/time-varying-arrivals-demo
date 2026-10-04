"""Formeln: Ankunftsrate, momentanes und verzögertes Angebot (geschlossene Form gegen zwei unabhängige Kontrollrechnungen), Besetzung."""

import math

import pytest

import tva_formulas as F

OMEGA_MU_ONE = 2 * math.pi / F.MU         # Periode, bei der ω/μ = 1 gilt


def test_arrival_rate_and_momentary_offer_by_hand():
    """λ(0) = a·μ, λ(P/4) = a·μ·(1 + A), λ(3P/4) = a·μ·(1 − A); das momentane Angebot ist λ/μ."""
    assert F.arrival_rate(0, 100, 0.5, 240) == pytest.approx(100 * F.MU)
    assert F.arrival_rate(60, 100, 0.5, 240) == pytest.approx(100 * F.MU * 1.5)
    assert F.arrival_rate(180, 100, 0.5, 240) == pytest.approx(100 * F.MU * 0.5)
    assert F.momentary_offer(60, 100, 0.5, 240) == pytest.approx(150.0)


def test_damping_and_lag_by_hand():
    """Bei ω/μ = 1: Dämpfung 1/√2, Verschiebung arctan(1)/ω = (π/4)/ω = 3·π/4 / 1 Minuten·… = 2.356 min."""
    assert F.mol_damping(OMEGA_MU_ONE) == pytest.approx(1 / math.sqrt(2))
    assert F.mol_lag_minutes(OMEGA_MU_ONE) == pytest.approx(2.35619449, abs=1e-6)


def test_lag_approaches_one_service_time_for_slow_waves_and_damping_goes_to_one():
    assert F.mol_lag_minutes(1_000_000) == pytest.approx(3.0, abs=1e-3) and F.mol_damping(1_000_000) == pytest.approx(1.0, abs=1e-6)
    assert F.mol_lag_minutes(5) < F.mol_lag_minutes(20) < F.mol_lag_minutes(240) < 3.0
    assert F.mol_damping(5) < F.mol_damping(20) < F.mol_damping(240) < 1.0


@pytest.mark.parametrize("period", [20, 60, 240])
def test_mol_closed_form_matches_the_numerical_solution_of_the_ode(period):
    """m' = λ(t) − μ·m (Runge-Kutta, unabhängig von der geschlossenen Form) im eingeschwungenen Zyklus."""
    curve = F.mol_numeric(100, 0.5, period)
    for t, m in curve[::90]:
        assert m == pytest.approx(F.mol_offer(t, 100, 0.5, period), rel=2e-4), (period, t)


@pytest.mark.parametrize("period,t", [(60, 7.0), (60, 31.0), (240, 100.0), (20, 3.3)])
def test_mol_closed_form_matches_the_defining_integral(period, t):
    """m(t) = ∫₀^∞ λ(t − s)·e^{−μs} ds (Trapezregel bis 60/μ, wo e^{−μs} < 1e-26 ist), unabhängig von der geschlossenen Form."""
    step, upper = 0.01, 60 / F.MU
    n = int(upper / step)
    total = 0.0
    for k in range(n + 1):
        s = k * step
        w = 0.5 if k in (0, n) else 1.0
        total += w * F.arrival_rate(t - s, 100, 0.5, period) * math.exp(-F.MU * s)
    assert total * step == pytest.approx(F.mol_offer(t, 100, 0.5, period), rel=2e-4)


def test_mol_equals_the_mean_offer_without_amplitude_and_the_cycle_mean_is_preserved():
    assert all(F.mol_offer(t, 100, 0.0, 60) == pytest.approx(100.0) for t in (0, 13, 40))
    mean = sum(F.mol_offer(t + 0.5, 100, 0.5, 240) for t in range(240)) / 240
    assert mean == pytest.approx(100.0, rel=1e-3)


def test_offset_by_hand_and_monotone_in_the_period():
    """Ohne Amplitude kein Versatz; er fällt mit der Periode, bei sehr schnellen Wellen nähert er sich A·√a (hier 5.0)."""
    assert F.offset_in_sqrt_units(100, 0.0, 240) == pytest.approx(0.0, abs=1e-12)
    values = [F.offset_in_sqrt_units(100, 0.5, p) for p in (5, 10, 20, 60, 240, 1440)]
    assert all(x > y for x, y in zip(values, values[1:]))
    assert values[0] < 5.0 and values[0] > 4.5 and F.offset_in_sqrt_units(100, 0.5, 1) == pytest.approx(5.0, abs=0.1)


def test_exact_servers_is_minimal_and_feasible_for_real_offers_and_with_a_guess():
    for a, alpha in ((6.4, 0.2), (49.7, 0.2), (101.3, 0.5), (150.0, 0.1)):
        c = F.exact_servers(a, alpha)
        assert c > a and F.erlang_c(c, a) <= alpha
        assert c - 1 <= a or F.erlang_c(c - 1, a) > alpha
        for guess in (c - 5, c + 5, c):
            assert F.exact_servers(a, alpha, guess=guess) == c


def test_staffing_per_minute_has_one_value_per_minute_and_follows_the_offer():
    psa = F.staffing_per_minute(100, 0.5, 60, 0.2, "psa")
    mol = F.staffing_per_minute(100, 0.5, 60, 0.2, "mol")
    assert len(psa) == len(mol) == 60 and psa != mol
    assert psa.index(max(psa)) == 14 and abs(mol.index(max(mol)) - 17) <= 1          # Gipfel bei P/4 = 15, verzögert um etwa 3 Minuten
    flat = F.staffing_per_minute(100, 0.0, 60, 0.2, "psa")
    assert len(set(flat)) == 1 and flat[0] == 111


def test_blocked_staffing_by_hand():
    assert F.blocked_staffing([1, 3, 2, 5, 4, 4, 7], 3) == [3, 3, 3, 5, 5, 5, 7]
    assert F.blocked_staffing([1, 3, 2], 1) == [1, 3, 2] and F.blocked_staffing([4, 2], 60) == [4, 4]


def test_coarser_raster_never_lowers_the_mean_number_of_lanes():
    base = F.staffing_per_minute(100, 0.5, 240, 0.2, "mol")
    means = [sum(F.blocked_staffing(base, w)) / len(base) for w in (1, 15, 60)]
    assert means[0] <= means[1] <= means[2] and means[2] > 1.15 * means[0]


def test_erlang_hand_values():
    assert F.erlang_b(2, 1.0) == pytest.approx(0.2) and F.erlang_c(2, 1.0) == pytest.approx(1 / 3)
    with pytest.raises(ValueError):
        F.erlang_c(3, 3.0)
