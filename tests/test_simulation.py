"""Simulation: Generator, Mini-Instanzen von Hand (wachsende und sinkende Spurzahl, Phasen, Zeitintegral), Ausdünnung, Grenzfälle
(konstante Last gegen Erlang C, unendlich viele Spuren gegen das verzögerte Angebot)."""

import pytest

import tva_evaluation as E
import tva_formulas as F
import tva_simulation as S


def test_splitmix64_matches_the_reference_sequence():
    rng = S.SplitMix64(0)
    assert [rng.next() for _ in range(3)] == [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4, 0x06C45D188009454F]


def test_streams_are_distinct_and_expovariate_has_the_right_mean():
    g, a, s = S.streams(7)
    assert len({g.state, a.state, s.state}) == 3
    ex = [S.SplitMix64(5).expovariate(0.5) for _ in range(1)] + [g.expovariate(0.5) for _ in range(20000)]
    assert min(ex) > 0 and sum(ex) / len(ex) == pytest.approx(2.0, rel=0.05)


def test_mini_instance_with_growing_capacity_by_hand(growing_capacity_streams):
    """Siehe conftest. Ankünfte je Phase [3, 1], davon Wartende [2, 0]; Zeitintegral der Zahl im System je Phase [3.0, 4.6]
    (Phase 0: 0.5·1 + 0.5·2 + 0.5·3; Phase 1: 1·3 + 0.4·2 + 0.1·1 + 0.2·2 + 0.3·1), Zeit je Phase [2, 2]."""
    gap, accept, svc = growing_capacity_streams
    r = S.simulate(3.0, 0.0, 4, [1, 1, 2, 2], 4.0, seed=0, bins=2, gap_rng=gap, accept_rng=accept, svc_rng=svc)
    assert r.arrivals == [3, 1] and r.waited == [2, 0]
    assert r.area == pytest.approx([3.0, 4.6]) and r.time_in_bin == pytest.approx([2.0, 2.0])
    assert r.wait_prob() == pytest.approx([2 / 3, 0.0]) and r.mean_in_system() == pytest.approx([1.5, 2.3])


def test_mini_instance_with_shrinking_capacity_by_hand(shrinking_capacity_streams):
    """Siehe conftest. Sinkt die Spurzahl unter die Zahl der Beschäftigten, beenden diese ihre Abfertigung, aber niemand rückt nach:
    Lkw 3 (Phase 1) wartet bis zur Rückkehr der zweiten Spur bei 4.0. Ankünfte [2, 1], Wartende [0, 1], Zeitintegral [2.5, 5.2]."""
    gap, accept, svc = shrinking_capacity_streams
    r = S.simulate(3.0, 0.0, 4, [2, 2, 1, 1], 4.0, seed=0, bins=2, gap_rng=gap, accept_rng=accept, svc_rng=svc)
    assert r.arrivals == [2, 1] and r.waited == [0, 1]
    assert r.area == pytest.approx([2.5, 5.2]) and r.time_in_bin == pytest.approx([2.0, 2.0])


def test_rejected_candidates_are_not_counted():
    """Ausdünnung: bei Annahmewert 0.9·λ_max wird ein Kandidat angenommen, wenn λ(t) ≥ 0.9·λ_max, sonst verworfen."""
    from conftest import ScriptedRng

    gap = ScriptedRng(exp_values=[1.0, 1.0, 1.0, 100.0])
    accept = ScriptedRng(uniform_values=[0.9, 0.9, 0.9, 0.9])
    svc = ScriptedRng(exp_values=[0.1, 0.1, 0.1])
    # Periode 4, Amplitude 1: λ(t) = a·μ·(1 + sin(πt/2)): t = 1 → 2·a·μ (angenommen), t = 2 → a·μ < 0.9·2·a·μ (verworfen), t = 3 → 0 (verworfen)
    r = S.simulate(3.0, 1.0, 4, [1, 1, 1, 1], 4.0, seed=0, bins=2, gap_rng=gap, accept_rng=accept, svc_rng=svc)
    assert sum(r.arrivals) == 1 and r.arrivals == [1, 0]


def test_same_seed_same_result_and_different_seed_differs():
    cap = [12] * 60
    a = S.simulate(10, 0.5, 60, cap, 600.0, 11)
    b = S.simulate(10, 0.5, 60, cap, 600.0, 11)
    other = S.simulate(10, 0.5, 60, cap, 600.0, 12)
    assert a.arrivals == b.arrivals and a.waited == b.waited and a.arrivals != other.arrivals


def test_arrival_counts_follow_the_wave():
    """Über viele Zyklen folgt die Zahl der Ankünfte je Phase dem Integral von λ(t) (Poisson-Streuung)."""
    a, amp, period, bins = 20, 0.5, 60, 12
    cycles = 400
    res = S.simulate(a, amp, period, [60] * period, cycles * period, 3, bins=bins)
    width = period / bins
    for b in range(bins):
        expected = cycles * sum(F.arrival_rate(b * width + (j + 0.5) * width / 50, a, amp, period) * width / 50 for j in range(50))
        assert res.arrivals[b] == pytest.approx(expected, rel=0.06), b


def test_constant_load_with_constant_lanes_matches_erlang_c():
    """Amplitude 0, 26 Spuren bei Angebot 20: Anteil Wartender je Phase nahe der Erlang-C-Wahrscheinlichkeit."""
    res = S.simulate(20, 0.0, 60, [26] * 60, 60 * 3000.0, 4)
    pw = [p for p in res.wait_prob() if p is not None]
    exact = F.erlang_c(26, 20)
    assert sum(pw) / len(pw) == pytest.approx(exact, abs=0.015)


def test_infinite_servers_reproduce_the_delayed_offer():
    """Mit praktisch unendlich vielen Spuren ist die mittlere Zahl im System je Phase das verzögerte Angebot (M_t/M/∞): unabhängiger
    Vergleich der Simulation mit der geschlossenen Form."""
    a, amp, period = 20, 0.5, 60
    res = S.simulate(a, amp, period, [10_000] * period, 3000 * float(period), 5)
    sim = res.mean_in_system()
    ref = E.bin_average_mol(a, amp, period)
    for s, r in zip(sim, ref):
        assert s == pytest.approx(r, rel=0.03)
    assert max(res.waited) == 0


def test_clock_conservation():
    res = S.simulate(10, 0.5, 40, [14] * 40, 800.0, 6)
    assert sum(res.time_in_bin) == pytest.approx(800.0) and res.horizon == 800.0
