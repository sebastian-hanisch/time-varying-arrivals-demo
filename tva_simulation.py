"""Ereignisdiskrete Simulation eines Gates mit zeitvariabler Ankunftsrate und zeitvariabler Spurzahl (M_t/M/c_t, unendliche Geduld).

Ankünfte entstehen durch **Ausdünnung** (Lewis und Shedler): Kandidaten mit der Höchstrate λ_max, jeder wird mit Wahrscheinlichkeit
λ(t)/λ_max angenommen. Die Spurzahl gilt je Minute (Liste über einen Zyklus, periodisch); steigt sie, rücken Wartende sofort nach, sinkt
sie unter die Zahl der Beschäftigten, beenden diese ihre Abfertigung (keine neue Abfertigung, bis wieder Platz ist).

Aufbau nach Einheiten (je Ereignistyp ein Handler, kein versteckter Zustand): `handle_arrival` (Kandidat annehmen oder verwerfen),
`handle_departure`, `handle_capacity` (Minutenwechsel), `simulate` (Ereignisschleife). Zufall nur über übergebene `SplitMix64`-Ströme
(Kandidaten, Annahme, Abfertigung). Ergebnis je Phase des Zyklus (`bins` gleich breite Phasen): Zahl der Ankünfte, davon Wartende, und
das Zeitintegral der Zahl im System (für den Vergleich mit dem verzögerten Angebot)."""

import heapq
import math
from collections import deque
from dataclasses import dataclass

import tva_formulas as F

_MASK = (1 << 64) - 1
ARRIVAL, DEPARTURE, CAPACITY = 0, 1, 2
BINS = 24


class SplitMix64:
    """Kleiner, gut gemischter 64-Bit-Zufallsgenerator (Vigna); reine Ganzzahl-Arithmetik."""

    def __init__(self, seed):
        self.state = seed & _MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & _MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
        return z ^ (z >> 31)

    def uniform(self):
        """Gleichverteilt auf [0, 1) mit 53 Bit."""
        return (self.next() >> 11) * (1.0 / (1 << 53))

    def expovariate(self, rate):
        """Exponentiell mit Mittel 1/rate (Inversion; 1 − u liegt in (0, 1], der Logarithmus ist endlich)."""
        return -math.log(1.0 - self.uniform()) / rate


def streams(seed):
    """Die drei Zufallsströme eines Laufs: Kandidaten-Ankünfte, Annahme-Entscheidung, Abfertigung."""
    return SplitMix64(seed), SplitMix64(seed + 7_777_777), SplitMix64(seed + 15_555_555)


@dataclass
class SimResult:
    period: float
    bins: int
    horizon: float
    arrivals: list           # Ankünfte je Phase
    waited: list             # davon Wartende je Phase (nicht sofort bedient)
    area: list               # ∫ N(t) dt je Phase
    time_in_bin: list        # simulierte Zeit je Phase

    def wait_prob(self):
        """Anteil Wartender je Phase (None, wo es keine Ankunft gab)."""
        return [w / a if a else None for w, a in zip(self.waited, self.arrivals)]

    def mean_in_system(self):
        """Mittlere Zahl im System je Phase."""
        return [x / t if t else None for x, t in zip(self.area, self.time_in_bin)]


class _State:
    __slots__ = ("period", "bins", "cap_per_min", "cap", "t", "n", "busy", "queue", "events", "seq", "arrivals", "waited",
                 "area", "time_in_bin", "mean_offer", "amplitude", "lam_max", "mu")


def _bin_of(s, t):
    return int((t % s.period) / s.period * s.bins) % s.bins


def _advance_clock(s, t_new):
    """Zeit auf t_new vorstellen und das Integral der Zahl im System und die Zeit je Phase fortschreiben (Phasengrenzen werden geteilt)."""
    width = s.period / s.bins
    t = s.t
    while t < t_new - 1e-12:
        k = int(t / width + 1e-12)
        edge = (k + 1) * width
        step_to = min(t_new, edge)
        b = k % s.bins
        s.area[b] += s.n * (step_to - t)
        s.time_in_bin[b] += step_to - t
        t = step_to
    s.t = t_new


def _start_service(s, t, svc_rng):
    s.busy += 1
    s.seq += 1
    heapq.heappush(s.events, (t + svc_rng.expovariate(s.mu), s.seq, DEPARTURE))


def handle_arrival(s, gap_rng, accept_rng, svc_rng):
    """Ein Kandidat trifft ein: mit Wahrscheinlichkeit λ(t)/λ_max wird er zum Lkw (sonst verworfen). Ein Lkw findet eine freie Spur (und
    keine Schlange) und wird sofort bedient, sonst reiht er sich ein. Danach wird der nächste Kandidat eingeplant."""
    t = s.t
    lam_t = F.arrival_rate(t, s.mean_offer, s.amplitude, s.period)
    if accept_rng.uniform() * s.lam_max <= lam_t:
        b = _bin_of(s, t)
        s.arrivals[b] += 1
        s.n += 1
        if s.busy < s.cap and not s.queue:
            _start_service(s, t, svc_rng)
        else:
            s.waited[b] += 1
            s.queue.append(t)
    s.seq += 1
    heapq.heappush(s.events, (t + gap_rng.expovariate(s.lam_max), s.seq, ARRIVAL))


def handle_departure(s, svc_rng):
    """Ein Lkw ist abgefertigt; ist Platz (Beschäftigte unter der aktuellen Spurzahl), rückt der nächste Wartende nach."""
    s.busy -= 1
    s.n -= 1
    if s.queue and s.busy < s.cap:
        s.queue.popleft()
        _start_service(s, s.t, svc_rng)


def handle_capacity(s, svc_rng):
    """Minutenwechsel: die Spurzahl der neuen Minute gilt; Wartende rücken nach, solange Platz ist. Nächster Wechsel in einer Minute."""
    s.cap = s.cap_per_min[int(s.t % s.period) % len(s.cap_per_min)]
    while s.queue and s.busy < s.cap:
        s.queue.popleft()
        _start_service(s, s.t, svc_rng)
    s.seq += 1
    heapq.heappush(s.events, (s.t + 1.0, s.seq, CAPACITY))


def simulate(mean_offer, amplitude, period, cap_per_min, horizon, seed, bins=BINS, gap_rng=None, accept_rng=None, svc_rng=None):
    """Simuliert das Gate bis zum Zeitpunkt `horizon` (Minuten, am besten ein Vielfaches der Periode) bei Spurzahl `cap_per_min` je Minute
    des Zyklus. Start leer. `*_rng` ersetzen die Ströme aus `seed` (für Tests mit vorgegebenen Zahlen)."""
    if gap_rng is None or accept_rng is None or svc_rng is None:
        gap_rng, accept_rng, svc_rng = streams(seed)
    s = _State()
    s.period, s.bins, s.cap_per_min = float(period), bins, cap_per_min
    s.cap, s.t, s.n, s.busy, s.queue, s.events, s.seq = cap_per_min[0], 0.0, 0, 0, deque(), [], 0
    s.arrivals, s.waited, s.area, s.time_in_bin = [0] * bins, [0] * bins, [0.0] * bins, [0.0] * bins
    s.mean_offer, s.amplitude, s.mu = mean_offer, amplitude, F.MU
    s.lam_max = mean_offer * F.MU * (1.0 + amplitude)
    heapq.heappush(s.events, (gap_rng.expovariate(s.lam_max), 0, ARRIVAL))
    heapq.heappush(s.events, (0.0, 1, CAPACITY))
    s.seq = 1
    while s.events:
        t, _, ev = heapq.heappop(s.events)
        if t > horizon:
            break
        _advance_clock(s, t)
        if ev == ARRIVAL:
            handle_arrival(s, gap_rng, accept_rng, svc_rng)
        elif ev == DEPARTURE:
            handle_departure(s, svc_rng)
        else:
            handle_capacity(s, svc_rng)
    _advance_clock(s, horizon)
    return SimResult(float(period), bins, horizon, s.arrivals, s.waited, s.area, s.time_in_bin)
