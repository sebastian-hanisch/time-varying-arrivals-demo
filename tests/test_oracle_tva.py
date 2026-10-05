"""Orakel-Tests (unabhängiger Rechenweg): das verzögerte Angebot gegen numerische Integration der Definition (scipy.quad), die Spurzahl gegen eine Erlang-C-Suche über
Geburts-Todes-Gleichungen, die Ausdünnung gegen das Integral der Rate, und die Simulation je Phase gegen die exakten Kolmogorov-Vorwärtsgleichungen von M_t/M/c_t
(Zustand Beschäftigte × Wartende, Spurzahl je Minute, periodischer Beharrungszustand)."""

import math

import numpy as np
import pytest

sp = pytest.importorskip("scipy.sparse")
splinalg = pytest.importorskip("scipy.sparse.linalg")
integrate = pytest.importorskip("scipy.integrate")

import tva_formulas as F  # noqa: E402
import tva_simulation as S  # noqa: E402

MU = 1.0 / 3.0


@pytest.mark.parametrize("a,amp,period,t", [(20, 0.5, 20, 7.3), (100, 0.3, 240, 55.0), (5, 0.8, 77, 190.4), (200, 0.0, 60, 12.0)])
def test_delayed_offer_against_numerical_integration_of_the_definition(a, amp, period, t):
    """m(t) = ∫₀^∞ λ(t − s)·e^{−μs} ds, die Definition (abgeschnitten bei 60 min: e^{−20} ≈ 2·10⁻⁹)."""
    lam = lambda s: a * MU * (1 + amp * math.sin(2 * math.pi * (t - s) / period))
    value, _ = integrate.quad(lambda s: lam(s) * math.exp(-MU * s), 0, 60, limit=500)
    assert F.mol_offer(t, a, amp, period) == pytest.approx(value, rel=1e-7)


def _erlang_c_by_birth_death(c, a, size=1500):
    w = np.ones(size)
    for k in range(1, size):
        w[k] = w[k - 1] * a / min(k, c)
    return (w / w.sum())[c:].sum()


@pytest.mark.parametrize("a", [0.7, 3.2, 10.0, 24.5, 80.0])
@pytest.mark.parametrize("alpha", [0.5, 0.2, 0.1])
def test_exact_servers_is_the_smallest_c_with_the_target_wait_probability(a, alpha):
    c = F.exact_servers(a, alpha)
    assert c > a and _erlang_c_by_birth_death(c, a) <= alpha
    assert c - 1 <= a or _erlang_c_by_birth_death(c - 1, a) > alpha            # minimal
    for guess in (1, int(a) + 20):
        assert F.exact_servers(a, alpha, guess=guess) == c


def test_offset_in_sqrt_units_against_a_fine_grid():
    for a, amp, period, expected in [(100, 0.5, 240, 0.39), (100, 0.5, 60, 1.50), (100, 0.5, 20, 3.43)]:
        ts = np.linspace(0, period, 40001)
        d = max(abs(F.mol_offer(t, a, amp, period) - F.momentary_offer(t, a, amp, period)) for t in ts[::20])
        assert F.offset_in_sqrt_units(a, amp, period) == pytest.approx(d / math.sqrt(a), rel=1e-4)
        assert d / math.sqrt(a) == pytest.approx(expected, abs=0.01)


def test_thinning_counts_follow_the_integral_of_the_rate():
    """Erwartete Ankünfte je Phase = Zyklen · ∫ λ(t) dt über die Phase (geschlossene Stammfunktion); Poisson-Streuung, z < 4.5."""
    a, amp, period, cycles = 20, 0.5, 60, 150
    res = S.simulate(a, amp, period, [40] * period, cycles * period, seed=3)
    w, width = 2 * math.pi / period, period / 24
    for b in range(24):
        lo, hi = b * width, (b + 1) * width
        expected = cycles * a * MU * ((hi - lo) - amp / w * (math.cos(w * hi) - math.cos(w * lo)))
        assert abs(res.arrivals[b] - expected) < 4.5 * math.sqrt(expected), b


def _periodic_wait_by_kolmogorov(a, amp, period, caps, qmax=40, bins=24, step=0.1, cycles=12):
    """Exakte ankunftsgewichtete Wartewahrscheinlichkeit je Phase: Zustand (b, q) = (Beschäftigte, Wartende); Ankunft startet sofort, wenn b < Spurzahl und q = 0, sonst
    wartet sie; Abgang mit Rate b·μ, dabei rückt ein Wartender nach, wenn b − 1 < Spurzahl; beim Minutenwechsel rücken Wartende nach, solange b < neue Spurzahl.
    Zeitschritte mit eingefrorener Rate in der Schrittmitte (Matrixexponential), Iteration bis zum periodischen Beharrungszustand."""
    bmax, nq = max(caps), qmax + 1
    n_states = (bmax + 1) * nq
    idx = lambda b, q: b * nq + q

    def generators(cap):
        ar, dr = [], []
        for b in range(bmax + 1):
            for q in range(nq):
                i = idx(b, q)
                if b < cap and q == 0:
                    ar.append((i, idx(b + 1, q), 1.0))
                elif q < qmax:
                    ar.append((i, idx(b, q + 1), 1.0))
                if b > 0:
                    dr.append((i, idx(b, q - 1) if (q > 0 and b - 1 < cap) else idx(b - 1, q), b * MU))
        out = []
        for entries in (ar, dr):
            rows, cols, vals = zip(*entries)
            m = sp.coo_matrix((vals, (rows, cols)), shape=(n_states, n_states)).tocsr()
            m = m - sp.diags(np.asarray(m.sum(axis=1)).ravel())
            out.append(m.T.tocsr())
        return out

    mats = {c: generators(c) for c in set(caps)}
    lam = lambda t: a * MU * (1 + amp * math.sin(2 * math.pi * t / period))
    width = period / bins
    p = np.zeros(n_states)
    p[0] = 1.0
    waited_by_cycle = None
    for _ in range(cycles):
        arrivals, waited = np.zeros(bins), np.zeros(bins)
        for minute in range(period):
            c = caps[minute]
            if minute > 0 and caps[minute - 1] != c or (minute == 0 and caps[-1] != c):
                moved = np.zeros(n_states)
                for b in range(bmax + 1):
                    for q in range(nq):
                        k = min(q, max(c - b, 0))
                        moved[idx(b + k, q - k)] += p[idx(b, q)]
                p = moved
            A, Dm = mats[c]
            wait_mask = np.repeat(np.arange(bmax + 1), nq) >= c
            n_sub = int(round(1.0 / step))
            for s in range(n_sub):
                t = minute + (s + 0.5) / n_sub
                bin_ = int(t / width) % bins
                arrivals[bin_] += lam(t) / n_sub
                before = p[wait_mask].sum()
                p = splinalg.expm_multiply((lam(t) * A + Dm) / n_sub, p)
                waited[bin_] += lam(t) / n_sub * 0.5 * (before + p[wait_mask].sum())      # Trapezregel über den Schritt
        new = waited / arrivals
        if waited_by_cycle is not None and np.abs(new - waited_by_cycle).max() < 1e-9:
            break
        waited_by_cycle = new
    return new


def test_constant_rate_gives_erlang_c_in_the_kolmogorov_oracle():
    pw = _periodic_wait_by_kolmogorov(6, 0.0, 24, [8] * 24, qmax=70, step=0.5, cycles=20)
    assert pw == pytest.approx(_erlang_c_by_birth_death(8, 6.0), abs=1e-6)


@pytest.mark.parametrize("kind", ["psa", "mol"])
def test_simulation_per_phase_against_the_kolmogorov_oracle(kind):
    a, amp, period, alpha = 8, 0.5, 20, 0.2
    caps = F.staffing_per_minute(a, amp, period, alpha, kind)
    exact = _periodic_wait_by_kolmogorov(a, amp, period, caps)
    runs = np.array([np.array(S.simulate(a, amp, period, caps, 1500 * period, seed=40 + 7 * r).wait_prob(), float) for r in range(5)])
    mean, se = runs.mean(axis=0), runs.std(axis=0, ddof=1) / math.sqrt(len(runs))
    assert np.all(np.abs(mean - exact) < np.maximum(4 * se, 0.02)), np.round(mean - exact, 3)
    assert abs(float((mean - exact).mean())) < 0.01
