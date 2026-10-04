"""Presets: Vollständigkeit, gültige Werte, Permalink-Konstanten."""

import pytest

import tva_constants as C
import tva_presets as P


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) == set(C.PRESET_ORDER) and len(C.PRESETS) == 4
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS) and C.PRESET_HELP[name]


def test_preset_values_are_valid_and_match_the_setting_specs():
    for preset in C.PRESETS.values():
        assert preset["a"] in C.A_OPTIONS and preset["period"] in C.PERIOD_OPTIONS and preset["alpha"] in C.ALPHA_OPTIONS
        assert preset["raster"] in C.RASTER_OPTIONS and C.AMP_PCT_MIN <= preset["amp_pct"] <= C.AMP_PCT_MAX
        assert P.snap_amp(preset["amp_pct"]) == preset["amp_pct"]
        for key, state_key in P.PRESET_KEYS.items():
            P.SETTING_SPECS[state_key].caster(preset[key])


def test_preset_names_state_the_values_they_set():
    assert C.PRESETS["Schnelle Welle (Periode 20 min)"]["period"] == 20 and C.PRESETS["Tageswelle (Periode 4 h)"]["period"] == 240
    assert C.PRESETS["Tagesverlauf (Periode 24 h)"]["period"] == 1440 and C.PRESETS["Schichtraster 60 min"]["raster"] == 60


def test_default_preset_equals_the_default_settings():
    p = C.PRESETS["Tageswelle (Periode 4 h)"]
    assert (p["a"], p["amp_pct"], p["period"], p["alpha"], p["raster"], p["seed"]) == (
        C.DEFAULT_A, C.DEFAULT_AMP_PCT, C.DEFAULT_PERIOD, C.DEFAULT_ALPHA, C.DEFAULT_RASTER, C.DEFAULT_SEED)


def test_bounds_and_url_params():
    assert P.bounds("amp_slider") == (C.AMP_PCT_MIN, C.AMP_PCT_MAX) and P.bounds("seed_input") == (0, C.SEED_MAX)
    assert len({spec.url_param for spec in P.SETTING_SPECS.values()}) == len(P.SETTING_SPECS)


@pytest.mark.parametrize("key,value,expected", [("a_select", 60, 50), ("a_select", 76, 100), ("a_select", 5, 20), ("period_select", 100, 60),
                                                ("period_select", 150, 60), ("period_select", 151, 240), ("period_select", 99999, 1440),
                                                ("alpha_select", 0.3, 0.2), ("alpha_select", 0.36, 0.5), ("raster_select", 30, 15),
                                                ("raster_select", 38, 60)])
def test_option_regulators_snap_to_the_nearest_option(key, value, expected):
    assert P.snap_to_option(key, value) == expected


@pytest.mark.parametrize("value,expected", [(0, 0), (4, 0), (6, 10), (33, 30), (35, 40), (99, 70), (-5, 0)])
def test_amplitude_snaps_to_the_step_inside_the_bounds(value, expected):
    assert P.snap_amp(value) == expected


def test_formatters():
    assert C.fmt_int(150000) == "150.000" and C.fmt_pct(0.2) == "20 %" and C.fmt_pct(0.0898, 1) == "9.0 %"
