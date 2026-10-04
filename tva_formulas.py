"""Formeln zur zeitvariablen Besetzung: sinusförmige Ankunftsrate, momentanes Angebot (PSA), verzögertes Angebot (MOL, Modified Offered
Load) und die exakte Erlang-C-Staffelung, aus der die Spurzahl je Minute entsteht.

Modell: Die Ankunftsrate ist λ(t) = a·μ·(1 + A·sin(2πt/P)) mit mittlerem Angebot a (Erlang), Amplitude A und Periode P (Minuten);
die Abfertigung ist exponentiell mit Rate μ = 1/3 je Minute. Das **momentane Angebot** ist λ(t)/μ. Das **verzögerte Angebot** m(t) ist
die mittlere Zahl beschäftigter Server eines Systems mit unendlich vielen Servern (M_t/M/∞), m(t) = ∫₀^∞ λ(t − s)·e^{−μs} ds: ein
Lkw, der vor s Minuten ankam, ist noch in Abfertigung, wenn seine Dauer länger als s ist. Die Erlang-B/C-Formeln stehen zur Staffelung
(Kopie aus mmc-queue-demo, bewusst ohne Import zwischen Repos)."""

import math

MU = 1.0 / 3.0                 # Abfertigungsrate je Spur (3 min mittlere Dauer)


def erlang_b(c, a):
    """Erlang-B-Verlustwahrscheinlichkeit über die stabile Rekursion B_k = a·B_{k-1}/(k + a·B_{k-1})."""
    b = 1.0
    for k in range(1, c + 1):
        b = a * b / (k + a * b)
    return b


def erlang_c(c, a):
    """Erlang C: Wahrscheinlichkeit zu warten bei unendlicher Geduld, C = B/(1 − ρ(1 − B)); nur für c > a."""
    rho = a / c
    if rho >= 1:
        raise ValueError("c ≤ a: keine stationäre Verteilung")
    b = erlang_b(c, a)
    return b / (1 - rho * (1 - b))


def arrival_rate(t, mean_offer, amplitude, period):
    """Ankunftsrate λ(t) je Minute: a·μ·(1 + A·sin(2πt/P))."""
    return mean_offer * MU * (1.0 + amplitude * math.sin(2.0 * math.pi * t / period))


def momentary_offer(t, mean_offer, amplitude, period):
    """Momentanes Angebot λ(t)/μ = a·(1 + A·sin(2πt/P)) (PSA: so tun, als wäre die Last gerade stationär)."""
    return mean_offer * (1.0 + amplitude * math.sin(2.0 * math.pi * t / period))


def mol_offer(t, mean_offer, amplitude, period):
    """Verzögertes Angebot m(t) = ∫₀^∞ λ(t − s)·e^{−μs} ds in geschlossener Form: a·(1 + A/√(1 + (ω/μ)²)·sin(ωt − arctan(ω/μ))) mit
    ω = 2π/P. Die Welle ist gedämpft und um arctan(ω/μ)/ω Minuten verschoben."""
    w = 2.0 * math.pi / period
    r = w / MU
    return mean_offer * (1.0 + amplitude / math.sqrt(1.0 + r * r) * math.sin(w * t - math.atan(r)))


def mol_lag_minutes(period):
    """Verschiebung des verzögerten gegenüber dem momentanen Angebot in Minuten: arctan(ω/μ)/ω."""
    w = 2.0 * math.pi / period
    return math.atan(w / MU) / w


def mol_damping(period):
    """Dämpfungsfaktor der Amplitude des verzögerten Angebots: 1/√(1 + (ω/μ)²)."""
    w = 2.0 * math.pi / period
    return 1.0 / math.sqrt(1.0 + (w / MU) ** 2)


def offset_in_sqrt_units(mean_offer, amplitude, period, steps=720):
    """Größter Abstand zwischen momentanem und verzögertem Angebot über einen Zyklus, gemessen in √(mittleres Angebot): so viel
    Sicherheitsstufe β verschenkt, wer mit dem momentanen Angebot besetzt."""
    worst = 0.0
    for k in range(steps):
        t = period * (k + 0.5) / steps
        worst = max(worst, abs(mol_offer(t, mean_offer, amplitude, period) - momentary_offer(t, mean_offer, amplitude, period)))
    return worst / math.sqrt(mean_offer)


def exact_servers(a, alpha, guess=None):
    """Kleinste Spurzahl c > a mit Erlang-C-Wartewahrscheinlichkeit ≤ alpha (a darf ein reelles Angebot sein). `guess` (etwa die Lösung
    der Nachbarminute) verkürzt die Suche: von dort wird nach oben oder unten bis zur Minimalität gesucht."""
    c = int(a) + 1 if guess is None else max(int(a) + 1, guess)
    while erlang_c(c, a) > alpha:
        c += 1
    while c - 1 > a and erlang_c(c - 1, a) <= alpha:
        c -= 1
    return c


def staffing_per_minute(mean_offer, amplitude, period, alpha, kind):
    """Spurzahl je Minute über einen Zyklus (`period` ganze Minuten): kleinste Spurzahl mit Erlang-C-Wartewahrscheinlichkeit ≤ alpha beim
    Angebot der Minutenmitte; kind = "psa" (momentanes Angebot) oder "mol" (verzögertes Angebot)."""
    offer = {"psa": momentary_offer, "mol": mol_offer}[kind]
    out, prev = [], None
    for k in range(int(period)):
        c = exact_servers(offer(k + 0.5, mean_offer, amplitude, period), alpha, guess=None if prev is None else prev - 2)
        out.append(c)
        prev = c
    return out


def blocked_staffing(per_minute, width):
    """Planungsraster: die Spurzahl gilt für Blöcke von `width` Minuten und ist das Maximum der Minuten-Werte im Block (konservativ)."""
    out = []
    for i in range(0, len(per_minute), width):
        block = per_minute[i:i + width]
        out.extend([max(block)] * len(block))
    return out


def mol_numeric(mean_offer, amplitude, period, cycles=12, step=0.02):
    """Unabhängige Kontrollrechnung des verzögerten Angebots: numerische Integration von m' = λ(t) − μ·m über `cycles` Perioden (Runge-Kutta 4. Ordnung), Rückgabe
    der Kurve des letzten Zyklus als Liste (t, m) in Schritten von `period/720` Minuten."""
    def f(t, m):
        return arrival_rate(t, mean_offer, amplitude, period) - MU * m

    m, t = mean_offer, 0.0
    total = cycles * period
    out = []
    n_steps = int(total / step)
    record_from = (cycles - 1) * period
    next_record = record_from
    for _ in range(n_steps):
        k1 = f(t, m)
        k2 = f(t + step / 2, m + step * k1 / 2)
        k3 = f(t + step / 2, m + step * k2 / 2)
        k4 = f(t + step, m + step * k3)
        m += step * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        t += step
        if t >= next_record - 1e-9:
            out.append((t - record_from, m))
            next_record += period / 720
    return out
