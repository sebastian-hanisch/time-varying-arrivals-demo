"""Auswertung: Kurven, Horizont, Stabilität, kleine Studien-Zelle, Vollständigkeit der vorgerechneten Datei."""

import pytest

import tva_constants as C
import tva_evaluation as E
import tva_formulas as F
import tva_simulation as S


def test_gate_curves_structure_and_values():
    c = E.gate_curves(100, 0.5, 60, 0.2, 1)
    assert len(c["t"]) == len(c["momentary"]) == len(c["mol"]) == len(c["c_psa"]) == len(c["c_mol"]) == 60
    assert c["t"][0] == 0.5 and c["momentary"][14] == pytest.approx(F.momentary_offer(14.5, 100, 0.5, 60))
    assert c["lag_min"] == pytest.approx(F.mol_lag_minutes(60)) and c["offset_sqrt"] == pytest.approx(F.offset_in_sqrt_units(100, 0.5, 60))
    assert c["mean_psa"] == pytest.approx(sum(c["c_psa"]) / 60) and c["mean_mol"] == pytest.approx(sum(c["c_mol"]) / 60)


def test_gate_curves_raster_blocks_the_staffing_and_raises_the_mean():
    fine, coarse = E.gate_curves(100, 0.5, 240, 0.2, 1), E.gate_curves(100, 0.5, 240, 0.2, 60)
    assert len(set(coarse["c_mol"][:60])) == 1 and coarse["mean_mol"] > fine["mean_mol"]
    assert fine["momentary"] == coarse["momentary"]


def test_horizon_is_a_whole_number_of_cycles_and_at_least_one():
    assert E.horizon_for(100, 240, 150_000) % 240 == 0 and E.horizon_for(100, 240, 150_000) == pytest.approx(4560.0)
    assert E.horizon_for(20, 1440, 1_000) == 1440.0


def test_stability_by_hand():
    class Fake:
        arrivals = [10, 10, 10, 0]

        @staticmethod
        def wait_prob():
            return [0.1, 0.2, 0.3, None]

    s = E.stability(Fake(), 0.2)
    assert s["min"] == 0.1 and s["max"] == 0.3 and s["mean"] == pytest.approx(0.2) and s["phases"] == 3
    assert s["missed"] == 1 and s["min_arrivals"] == 10                     # nur 0.3 > 0.2 + 0.02


def test_phase_midpoints_and_bin_average_of_the_closed_form():
    assert E.phase_midpoints(240, 4) == [30.0, 90.0, 150.0, 210.0]
    avg = E.bin_average_mol(100, 0.5, 240)
    assert len(avg) == 24 and sum(avg) / 24 == pytest.approx(100.0, rel=1e-3)


def test_study_cell_run_small_structure_and_branches():
    psa = E.study_cell_run(20, 0.5, 20, 0.2, 1, "psa", 40_000, 3, reps=2)
    mol = E.study_cell_run(20, 0.5, 20, 0.2, 1, "mol", 40_000, 3, reps=2)
    for cell in (psa, mol):
        assert len(cell["pw"]) == 24 and len(cell["se"]) == 24 and cell["reps"] == 2 and 0 <= cell["min"] <= cell["mean"] <= cell["max"] <= 1
    assert psa["max"] - psa["min"] > mol["max"] - mol["min"]             # Zweig: die beiden Besetzungen unterscheiden sich wirklich
    single = E.study_cell_run(20, 0.5, 60, 0.2, 1, "mol", 20_000, 3, reps=1)
    assert single["se"] is None


def test_nearest_picks_the_closest_axis_value():
    assert E.nearest(C.STUDY_A, 60) == 20 and E.nearest(C.STUDY_A, 61) == 100 and E.nearest(C.STUDY_AMP, 0.0) == 0.3
    assert E.nearest(C.STUDY_AMP, 0.39) == 0.3 and E.nearest(C.STUDY_AMP, 0.41) == 0.5


def test_precomputed_file_is_complete():
    pre = E.load_precomputed()
    keys = {(x["a"], x["amp"], x["period"], x["raster"], x["kind"]) for x in pre["study"]}
    assert keys == {(a, amp, p, r, k) for a in C.STUDY_A for amp in C.STUDY_AMP for p in C.STUDY_PERIOD for r in C.STUDY_RASTER
                    for k in ("psa", "mol")}
    assert pre["study_alpha"] == C.STUDY_ALPHA and pre["study_reps"] == C.STUDY_REPS and pre["study_customers"] == C.STUDY_CUSTOMERS
    for x in pre["study"]:
        assert x["reps"] == C.STUDY_REPS and len(x["pw"]) == S.BINS and len(x["se"]) == S.BINS
