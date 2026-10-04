"""Konstanten der Demo zu zeitvariablen Ankünften: Regler, Voreinstellungen, Studien-Achsen. Zeiten in Minuten."""


def fmt_int(n):
    """Ganzzahl mit Punkt als Tausendertrenner (10000 -> 10.000)."""
    return f"{n:,}".replace(",", ".")


def fmt_pct(x, digits=0):
    """Anteil als Prozent mit Leerzeichen (0.086 -> "9 %", mit digits=1 "8.6 %")."""
    return f"{x:.{digits}%}".replace("%", " %")


A_OPTIONS = (20, 50, 100, 200)                    # mittleres Angebot a (Erlang)
DEFAULT_A = 100
AMP_PCT_MIN, AMP_PCT_MAX, AMP_PCT_STEP, DEFAULT_AMP_PCT = 0, 70, 10, 50       # Amplitude der Welle in Prozent des Mittels
PERIOD_OPTIONS = (20, 60, 240, 1440)              # Periode der Welle (Minuten)
DEFAULT_PERIOD = 240
ALPHA_OPTIONS = (0.5, 0.2, 0.1)                   # Ziel: höchstens so viele Lkw müssen zu jeder Tageszeit warten
DEFAULT_ALPHA = 0.2
RASTER_OPTIONS = (1, 15, 60)                      # Planungsraster (Minuten)
DEFAULT_RASTER = 1
SEED_MAX = 999999
DEFAULT_SEED = 35

LIVE_CUSTOMERS = 150_000                           # Lkw je Live-Lauf (je Staffelung)
MISS_TOLERANCE = 0.02                              # Phase gilt als Ziel verfehlt, wenn P(warten) > Ziel + 2 Prozentpunkte

# Vorgerechnete Studie (generate_precomputed.py)
STUDY_A = (20, 100)
STUDY_AMP = (0.3, 0.5)
STUDY_PERIOD = PERIOD_OPTIONS
STUDY_RASTER = RASTER_OPTIONS
STUDY_ALPHA = 0.2
STUDY_CUSTOMERS = 800_000                         # Lkw je Wiederholung
STUDY_REPS = 3                                    # unabhängige Wiederholungen je Zelle

PRESET_ORDER = ("Tageswelle (Periode 4 h)", "Schnelle Welle (Periode 20 min)", "Tagesverlauf (Periode 24 h)",
                "Schichtraster 60 min")


def _preset(a=DEFAULT_A, amp_pct=DEFAULT_AMP_PCT, period=DEFAULT_PERIOD, alpha=DEFAULT_ALPHA, raster=DEFAULT_RASTER):
    return {"a": a, "amp_pct": amp_pct, "period": period, "alpha": alpha, "raster": raster, "seed": DEFAULT_SEED}


PRESETS = {
    "Tageswelle (Periode 4 h)": _preset(),
    "Schnelle Welle (Periode 20 min)": _preset(period=20),
    "Tagesverlauf (Periode 24 h)": _preset(period=1440),
    "Schichtraster 60 min": _preset(raster=60),
}
# Zahlen aus der vorgerechneten Studie (Angebot 100, Amplitude 50 %, Ziel 20 %, je 3 Läufe à 800 000 Lkw); tests/test_claims.py rechnet sie nach
PRESET_HELP = {
    "Tageswelle (Periode 4 h)": "Periode 4 h: nach dem momentanen Angebot besetzt, warten je Phase 6 % bis 36 % der Lkw (Ziel 20 %), nach dem verzögerten Angebot 17 % bis 20 %, bei gleicher mittlerer Spurzahl.",
    "Schnelle Welle (Periode 20 min)": "Periode 20 min (Lkw-Pulk): nach dem momentanen Angebot warten je Phase 1 % bis 100 % der Lkw, nach dem verzögerten Angebot 16 % bis 21 %.",
    "Tagesverlauf (Periode 24 h)": "Periode 24 h: die langsame Welle verzeiht das momentane Angebot fast: je Phase 14 % bis 23 % gegen 15 % bis 20 % beim verzögerten Angebot (der Unterschied liegt nahe am Rauschen von bis zu 3.5 Prozentpunkten).",
    "Schichtraster 60 min": "Spurzahl nur stündlich änderbar (Maximum im Block), Periode 4 h: 137.5 statt 111.4 Spuren im Mittel (+23 %), dafür warten im Mittel nur noch 3 % der Lkw statt 18 %.",
}
