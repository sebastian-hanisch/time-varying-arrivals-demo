"""Auswertung: Kurven des momentanen und verzögerten Angebots, Spurzahlen beider Staffelungen, Simulation je Phase, Stabilität der
Wartewahrscheinlichkeit und die vorgerechnete Studie (Periode × Staffelung × Planungsraster). Die teure Studie (viele lange Läufe) steht
vorgerechnet in `precomputed_sweep.json` (Generator: generate_precomputed.py, Laden: `load_precomputed`)."""

import json
import math
from pathlib import Path

import tva_constants as C
import tva_formulas as F
from tva_simulation import BINS, simulate

PRECOMPUTED_PATH = Path(__file__).resolve().parent / "precomputed_sweep.json"


def gate_curves(mean_offer, amplitude, period, alpha, raster):
    """Alle Kurven über einen Zyklus in Minutenschritten: Zeit, momentanes Angebot, verzögertes Angebot, Spurzahl nach PSA und nach MOL
    (je mit Planungsraster `raster`: Maximum im Block), dazu die mittleren Spurzahlen und die Verschiebung des verzögerten Angebots."""
    n = int(period)
    ts = [k + 0.5 for k in range(n)]
    psa = F.blocked_staffing(F.staffing_per_minute(mean_offer, amplitude, period, alpha, "psa"), raster)
    mol = F.blocked_staffing(F.staffing_per_minute(mean_offer, amplitude, period, alpha, "mol"), raster)
    return {"t": ts,
            "momentary": [F.momentary_offer(t, mean_offer, amplitude, period) for t in ts],
            "mol": [F.mol_offer(t, mean_offer, amplitude, period) for t in ts],
            "c_psa": psa, "c_mol": mol, "mean_psa": sum(psa) / n, "mean_mol": sum(mol) / n,
            "lag_min": F.mol_lag_minutes(period), "offset_sqrt": F.offset_in_sqrt_units(mean_offer, amplitude, period)}


def horizon_for(mean_offer, period, n_customers):
    """Simulationsdauer: so viele ganze Zyklen, dass etwa `n_customers` Lkw ankommen (mindestens ein Zyklus)."""
    per_cycle = mean_offer * F.MU * period
    return max(1, round(n_customers / per_cycle)) * float(period)


def simulate_gate(mean_offer, amplitude, period, cap_per_min, n_customers, seed):
    """Ein Lauf des Gates mit Spurzahl `cap_per_min` je Minute über etwa `n_customers` Lkw."""
    return simulate(mean_offer, amplitude, period, cap_per_min, horizon_for(mean_offer, period, n_customers), seed)


def stability(result, alpha, tolerance=C.MISS_TOLERANCE):
    """Kennzahlen der Wartewahrscheinlichkeit je Phase: kleinster, größter und mittlerer Wert, Zahl der Phasen, die das Ziel verfehlen
    (P(warten) > Ziel + tolerance), Zahl der Phasen und kleinste Ankunftszahl je Phase."""
    pw = [p for p in result.wait_prob() if p is not None]
    return {"min": min(pw), "max": max(pw), "mean": sum(pw) / len(pw), "missed": sum(1 for p in pw if p > alpha + tolerance),
            "phases": len(pw), "min_arrivals": min(a for a in result.arrivals if a > 0)}


def study_cell_run(mean_offer, amplitude, period, alpha, raster, kind, n_customers, seed, reps=1):
    """Eine Zelle der Studie: Staffelung `kind` ("psa" oder "mol") mit Raster, `reps` unabhängige lange Simulationen (je etwa `n_customers`
    Lkw), Wartewahrscheinlichkeit je Phase aus den zusammengelegten Wiederholungen und Standardfehler je Phase (Streuung zwischen den
    Wiederholungen geteilt durch √reps; bei einer Wiederholung None)."""
    cap = F.blocked_staffing(F.staffing_per_minute(mean_offer, amplitude, period, alpha, kind), raster)
    runs = [simulate_gate(mean_offer, amplitude, period, cap, n_customers, seed + 1_000_003 * r) for r in range(reps)]
    bins = len(runs[0].arrivals)
    arrivals = [sum(r.arrivals[b] for r in runs) for b in range(bins)]
    waited = [sum(r.waited[b] for r in runs) for b in range(bins)]
    pw = [w / a if a else None for w, a in zip(waited, arrivals)]
    se = None
    if reps > 1:
        per_run = [r.wait_prob() for r in runs]
        se = []
        for b in range(bins):
            vals = [p[b] for p in per_run if p[b] is not None]
            mean = sum(vals) / len(vals)
            sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)) if len(vals) > 1 else 0.0
            se.append(sd / math.sqrt(len(vals)))
    valid = [p for p in pw if p is not None]
    return {"a": mean_offer, "amp": amplitude, "period": period, "raster": raster, "kind": kind, "alpha": alpha,
            "mean_lanes": sum(cap) / len(cap), "pw": pw, "se": se, "min": min(valid), "max": max(valid),
            "mean": sum(valid) / len(valid), "missed": sum(1 for p in valid if p > alpha + C.MISS_TOLERANCE),
            "min_arrivals": min(a for a in arrivals if a > 0), "reps": reps, "horizon": runs[0].horizon}


def load_precomputed():
    with open(PRECOMPUTED_PATH, encoding="utf-8") as f:
        return json.load(f)


def nearest(grid, value):
    """Nächster Wert der Studien-Achse (bei Gleichstand der kleinere)."""
    return min(grid, key=lambda g: (abs(g - value), g))


def study_cell(precomputed, a, amp, period, raster, kind):
    """Zelle der Studie für (gemessenes Angebot, gemessene Amplitude, Periode, Raster, Staffelung)."""
    return next(x for x in precomputed["study"] if x["a"] == a and abs(x["amp"] - amp) < 1e-9 and x["period"] == period
                and x["raster"] == raster and x["kind"] == kind)


def phase_midpoints(period, bins=BINS):
    """Mitten der Phasen eines Zyklus in Minuten (für Diagramme)."""
    width = period / bins
    return [(k + 0.5) * width for k in range(bins)]


def bin_average_mol(mean_offer, amplitude, period, bins=BINS, steps=40):
    """Mittleres verzögertes Angebot je Phase (Mittel der geschlossenen Form über die Phase): Vergleichswert für die Simulation einer
    Gate-Variante mit unendlich vielen Spuren."""
    width = period / bins
    out = []
    for k in range(bins):
        out.append(sum(F.mol_offer(k * width + (j + 0.5) * width / steps, mean_offer, amplitude, period) for j in range(steps)) / steps)
    return out
