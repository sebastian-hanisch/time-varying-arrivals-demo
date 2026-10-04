"""AppTest-Rauchtests: Voreinstellung, jedes Preset, Randwerte, Würfel-Knopf, Permalink-Grenzen, Abschnitte, Footer."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import tva_constants as C

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _run(**state):
    at = AppTest.from_file(APP, default_timeout=600)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    return at


def _ok(at):
    assert not at.exception, [e.value for e in at.exception]


def _metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def test_default_run_has_no_exception_and_shows_both_staffings():
    at = _run()
    _ok(at)
    assert _metric(at, "Mittlere Spurzahl: momentanes Angebot") == _metric(at, "Mittlere Spurzahl: verzögertes Angebot") == "111.4"
    assert _metric(at, "Verschiebung des verzögerten Angebots") == "3.0 min"
    assert _metric(at, "Versatz der Angebote") == "0.39·√a"
    assert " bis " in _metric(at, "Wartewahrscheinlichkeit nach momentanem Angebot")


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_button_runs(name):
    at = _run()
    next(b for b in at.button if b.key == f"preset_{name}").click().run()
    _ok(at)
    p = C.PRESETS[name]
    assert at.session_state["period_select"] == p["period"] and at.session_state["raster_select"] == p["raster"]
    assert at.metric


def test_raster_changes_the_mean_number_of_lanes():
    fine, coarse = _run(raster_select=1), _run(raster_select=60)
    _ok(coarse)
    assert float(_metric(coarse, "Mittlere Spurzahl: verzögertes Angebot")) > 1.15 * float(_metric(fine, "Mittlere Spurzahl: verzögertes Angebot"))


def test_no_amplitude_means_no_difference_between_the_two_staffings():
    at = _run(amp_slider=0)
    _ok(at)
    assert _metric(at, "Spurzahl-Unterschied") == "+0.0" and _metric(at, "Versatz der Angebote") == "0.00·√a"


@pytest.mark.parametrize("kw", [dict(a_select=20, period_select=20), dict(a_select=200, period_select=1440, amp_slider=70),
                                 dict(period_select=20, alpha_select=0.5), dict(alpha_select=0.1, raster_select=15),
                                 dict(a_select=20, amp_slider=70, raster_select=60), dict(amp_slider=10)])
def test_extreme_settings_run(kw):
    _ok(_run(**kw))


def test_a_faster_wave_gives_a_larger_offset_and_a_shorter_lag():
    slow, fast = _run(period_select=1440), _run(period_select=20)
    off = lambda at: float(_metric(at, "Versatz der Angebote").split("·")[0])
    lag = lambda at: float(_metric(at, "Verschiebung des verzögerten Angebots").split()[0])
    assert off(fast) > off(slow) and lag(fast) < lag(slow)


def test_dice_button_changes_the_seed_and_the_simulated_range():
    at = _run()
    old_seed, old = at.session_state["seed_input"], _metric(at, "Wartewahrscheinlichkeit nach momentanem Angebot")
    next(b for b in at.button if b.label == "🎲 Neuen Lauf würfeln").click().run()
    _ok(at)
    assert at.session_state["seed_input"] != old_seed and _metric(at, "Wartewahrscheinlichkeit nach momentanem Angebot") != old


def test_permalink_values_are_clamped_and_snapped():
    at = AppTest.from_file(APP, default_timeout=600)
    at.query_params["a"] = "76"
    at.query_params["amp"] = "33"
    at.query_params["p"] = "150"
    at.query_params["al"] = "0.3"
    at.query_params["r"] = "38"
    at.run()
    _ok(at)
    assert at.session_state["a_select"] == 100 and at.session_state["amp_slider"] == 30 and at.session_state["period_select"] == 60
    assert at.session_state["alpha_select"] == 0.2 and at.session_state["raster_select"] == 60


def test_permalink_ignores_garbage():
    at = AppTest.from_file(APP, default_timeout=600)
    at.query_params["amp"] = "viel"
    at.query_params["al"] = "nan"
    at.run()
    _ok(at)
    assert at.session_state["amp_slider"] == C.DEFAULT_AMP_PCT and at.session_state["alpha_select"] == C.DEFAULT_ALPHA


def test_charts_sections_and_limits_table_are_present():
    at = _run()
    _ok(at)
    assert len(at.get("plotly_chart")) == 6
    headers = [s.value for s in at.subheader]
    for part in ("Wie schnell darf die Welle sein", "Warum ist das momentane Angebot", "Planungsraster", "Wo die Annahmen enden"):
        assert any(part in h for h in headers), part
    table = next(m.value for m in at.markdown if "Wer setzt an" in m.value)
    for name in ("Kingman", "Jackson-Netze", "Prioritätsklassen"):
        assert name in table
    assert "geplant" not in table      # die Linie wird erst vollständig veröffentlicht, kein Status-Zusatz


def test_study_table_lists_all_periods():
    at = _run()
    text = next(m.value for m in at.markdown if m.value.startswith("| Periode |"))
    for label in ("20 min", "1 h", "4 h", "24 h"):
        assert f"| {label} |" in text


def test_seed_control_uses_the_portfolio_wording():
    at = _run()
    assert [n.label for n in at.number_input] == ["Zufalls-Seed"]


def test_related_demos_are_linked_and_footer_is_present():
    at = _run()
    text = " ".join(c.value for c in at.caption)
    for name in ("square-root-staffing-demo", "erlang-a-demo", "mmc-queue-demo", "mm1-queue-demo", "truck-appointment-demo"):
        assert name in text
    assert "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net)" in text


def test_no_sentence_wide_comma_replacement_in_the_app_source():
    """Regressionsschutz: `.replace(",", ".")` auf einem ganzen (verketteten) Satz macht aus Kommas im Fließtext Punkte; Tausender
    nur über `fmt_int`."""
    source = Path(APP).read_text(encoding="utf-8")
    assert '.replace(",", ".")' not in source.replace('f"{n:,}".replace(",", ".")', "")
