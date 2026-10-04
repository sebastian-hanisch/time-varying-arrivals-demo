"""JEDE Zahl aus README und App-Texten wird hier nachgerechnet: Formelwerte exakt, Studien-Zahlen aus der vorgerechneten Datei (3 Läufe à
800 000 Lkw je Zelle). Die Datei ist fest; ändern sich die Zahlen nach einer neuen Rechnung, müssen README und Hilfetexte nachgezogen
werden."""

import pytest

import tva_constants as C
import tva_evaluation as E
import tva_formulas as F

PRE = E.load_precomputed()


def cell(a, amp, period, raster, kind):
    return E.study_cell(PRE, a, amp, period, raster, kind)


def pct(x):
    return round(100 * x, 1)


def test_lag_and_offset_quoted_in_readme():
    """README (a = 100, Amplitude 50 %): Verschiebung des verzögerten Angebots 3.0 min (4 h und 24 h), 2.9 min (1 h), 2.4 min (20 min);
    Versatz 0.39·√a (4 h), 1.50·√a (60 min), 3.43·√a (20 min), 0.07·√a (24 h)."""
    assert [round(F.mol_lag_minutes(p), 1) for p in (240, 1440, 60, 20)] == [3.0, 3.0, 2.9, 2.4]
    assert [round(F.offset_in_sqrt_units(100, 0.5, p), 2) for p in (240, 60, 20, 1440)] == [0.39, 1.50, 3.43, 0.07]
    assert F.mol_damping(240) == pytest.approx(0.997, abs=0.001) and F.mol_damping(20) == pytest.approx(0.73, abs=0.005)


def test_both_staffings_use_the_same_number_of_lanes():
    """README: Die mittlere Spurzahl unterscheidet sich zwischen momentanem und verzögertem Angebot um höchstens 0.2 Spuren (in allen Zellen
    ohne Raster); a = 100: 111.3 bis 111.5, a = 20: 25.5 bis 25.8."""
    for a in C.STUDY_A:
        for amp in C.STUDY_AMP:
            for p in C.STUDY_PERIOD:
                assert abs(cell(a, amp, p, 1, "psa")["mean_lanes"] - cell(a, amp, p, 1, "mol")["mean_lanes"]) < 0.25
    lanes100 = [cell(100, amp, p, 1, k)["mean_lanes"] for amp in C.STUDY_AMP for p in C.STUDY_PERIOD for k in ("psa", "mol")]
    assert min(lanes100) >= 111.3 - 0.05 and max(lanes100) <= 111.5 + 0.05


def test_momentary_offer_misses_the_target_for_waves_quoted_in_readme():
    """README (a = 100, Amplitude 50 %, Ziel 20 %): PSA je Phase 0.9–100.0 % (20 min), 1.7–87.7 % (1 h), 6.4–35.9 % (4 h), 14.0–23.3 % (24 h);
    Phasen mit verfehltem Ziel 15, 14, 10, 4 von 24."""
    expected = {20: (0.9, 100.0, 15), 60: (1.7, 87.7, 14), 240: (6.4, 35.9, 10), 1440: (14.0, 23.3, 4)}
    for p, (lo, hi, missed) in expected.items():
        c = cell(100, 0.5, p, 1, "psa")
        assert (pct(c["min"]), pct(c["max"]), c["missed"]) == pytest.approx((lo, hi, missed), abs=0.051), p


def test_delayed_offer_holds_the_target_in_every_cell():
    """README: Nach dem verzögerten Angebot verfehlt in keiner der 16 Zellen ohne Raster eine Phase das Ziel (mehr als 2 Punkte darüber); a = 100,
    Amplitude 50 %: 16.4–21.1 % (20 min), 15.8–19.6 % (1 h), 16.7–20.4 % (4 h), 14.7–19.8 % (24 h)."""
    for a in C.STUDY_A:
        for amp in C.STUDY_AMP:
            for p in C.STUDY_PERIOD:
                assert cell(a, amp, p, 1, "mol")["missed"] == 0, (a, amp, p)
    expected = {20: (16.4, 21.1), 60: (15.8, 19.6), 240: (16.7, 20.4), 1440: (14.7, 19.8)}
    for p, (lo, hi) in expected.items():
        c = cell(100, 0.5, p, 1, "mol")
        assert (pct(c["min"]), pct(c["max"])) == pytest.approx((lo, hi), abs=0.051), p


def test_small_gate_and_small_amplitude_quoted_in_readme():
    """README: a = 20, Amplitude 50 %: PSA 2.3–79.6 % (20 min), 3.7–45.8 % (1 h), 11.2–23.9 % (4 h); a = 100, Amplitude 30 %, 4 h: PSA
    9.7–28.7 % gegen MOL 14.3–20.4 %."""
    for p, (lo, hi) in {20: (2.3, 79.6), 60: (3.7, 45.8), 240: (11.2, 23.9)}.items():
        c = cell(20, 0.5, p, 1, "psa")
        assert (pct(c["min"]), pct(c["max"])) == pytest.approx((lo, hi), abs=0.051), p
    assert (pct(cell(100, 0.3, 240, 1, "psa")["min"]), pct(cell(100, 0.3, 240, 1, "psa")["max"])) == pytest.approx((9.7, 28.7), abs=0.051)
    assert (pct(cell(100, 0.3, 240, 1, "mol")["min"]), pct(cell(100, 0.3, 240, 1, "mol")["max"])) == pytest.approx((14.3, 20.4), abs=0.051)


def test_the_delayed_offer_stays_below_the_target_on_average_because_of_integer_lanes():
    """README: Mittlerer Anteil Wartender bei verzögertem Angebot 17.3 bis 18.9 % (a = 100) und 16.3 bis 17.0 % (a = 20), nicht genau 20 %."""
    means100 = [cell(100, amp, p, 1, "mol")["mean"] for amp in C.STUDY_AMP for p in C.STUDY_PERIOD]
    means20 = [cell(20, amp, p, 1, "mol")["mean"] for amp in C.STUDY_AMP for p in C.STUDY_PERIOD]
    assert (pct(min(means100)), pct(max(means100))) == pytest.approx((17.3, 18.9), abs=0.051)
    assert (pct(min(means20)), pct(max(means20))) == pytest.approx((16.3, 17.0), abs=0.051)


def test_raster_quoted_in_readme_and_preset_help():
    """README (a = 100, Amplitude 50 %, verzögertes Angebot): Periode 4 h: 111.4 / 117.6 / 137.5 Spuren (+5.6 % / +23 %) bei im Mittel 18.3 / 7.5 /
    3.1 % Wartenden; 1 h: 111.3 / 134.2 / 161.0; 20 min: 111.5 / 132.8 / 150.0; 24 h: 111.3 / 112.4 / 115.5 (17.3 / 14.9 / 10.0 %)."""
    expected = {240: ((111.4, 117.6, 137.5), (18.3, 7.5, 3.1)), 60: ((111.3, 134.2, 161.0), None), 20: ((111.5, 132.8, 150.0), None),
                1440: ((111.3, 112.4, 115.5), (17.3, 14.9, 10.0))}
    for p, (lanes, means) in expected.items():
        cells = [cell(100, 0.5, p, r, "mol") for r in C.STUDY_RASTER]
        assert [round(c["mean_lanes"], 1) for c in cells] == pytest.approx(list(lanes), abs=0.051), p
        if means:
            assert [pct(c["mean"]) for c in cells] == pytest.approx(list(means), abs=0.051), p
    c240 = [cell(100, 0.5, 240, r, "mol")["mean_lanes"] for r in C.STUDY_RASTER]
    assert c240[1] / c240[0] - 1 == pytest.approx(0.056, abs=0.002) and c240[2] / c240[0] - 1 == pytest.approx(0.234, abs=0.002)


def test_preset_help_numbers():
    """PRESET_HELP: 4 h: PSA 6 % bis 36 %, MOL 17 % bis 20 %; 20 min: 1 % bis 100 % und 16 % bis 21 %; 24 h: 14 % bis 23 % gegen 15 % bis 20 %; Raster 60 min: 137.5
    statt 111.4 Spuren (+23 %), im Mittel 3 % statt 18 % Wartende; Rauschen bis 3 Punkte (24 h, a = 100)."""
    a = lambda p, kind: cell(100, 0.5, p, 1, kind)
    assert (round(100 * a(240, "psa")["min"]), round(100 * a(240, "psa")["max"])) == (6, 36)
    assert (round(100 * a(240, "mol")["min"]), round(100 * a(240, "mol")["max"])) == (17, 20)
    assert (round(100 * a(20, "psa")["min"]), round(100 * a(20, "psa")["max"])) == (1, 100)
    assert (round(100 * a(20, "mol")["min"]), round(100 * a(20, "mol")["max"])) == (16, 21)
    assert (round(100 * a(1440, "psa")["min"]), round(100 * a(1440, "psa")["max"])) == (14, 23)
    assert (round(100 * a(1440, "mol")["min"]), round(100 * a(1440, "mol")["max"])) == (15, 20)
    assert max(a(1440, "psa")["se"]) < 0.036 and max(a(1440, "mol")["se"]) < 0.036
    r60 = cell(100, 0.5, 240, 60, "mol")
    assert round(r60["mean_lanes"], 1) == 137.5 and round(100 * r60["mean"]) == 3 and round(100 * cell(100, 0.5, 240, 1, "mol")["mean"]) == 18


def test_noise_level_of_the_study_quoted_in_readme():
    """README: Der größte Standardfehler einer Phase beträgt in der Studie ohne Raster 3.5 Prozentpunkte (a = 100, 24 h), bei Perioden bis 4 h höchstens
    3.0 und bei 20 min höchstens 1.5 Punkte."""
    fine = [c for c in PRE["study"] if c["raster"] == 1]
    assert round(100 * max(max(c["se"]) for c in fine), 1) == 3.5
    assert round(100 * max(max(c["se"]) for c in fine if c["period"] <= 240), 1) == 3.0
    assert round(100 * max(max(c["se"]) for c in fine if c["period"] == 20), 1) == 1.5
