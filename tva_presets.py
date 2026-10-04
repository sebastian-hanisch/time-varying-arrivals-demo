"""SETTING_SPECS-Permalink-Muster, Presets und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio).
Alle Regler sind immer sichtbar - es gibt keinen ausblendbaren Regler (also auch kein KEPT-Muster)."""

import random
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st

import tva_constants as C


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None


SETTING_SPECS = {
    "a_select": SettingSpec("a", int, C.DEFAULT_A, C.A_OPTIONS[0], C.A_OPTIONS[-1]),
    "amp_slider": SettingSpec("amp", int, C.DEFAULT_AMP_PCT, C.AMP_PCT_MIN, C.AMP_PCT_MAX),
    "period_select": SettingSpec("p", int, C.DEFAULT_PERIOD, C.PERIOD_OPTIONS[0], C.PERIOD_OPTIONS[-1]),
    "alpha_select": SettingSpec("al", float, C.DEFAULT_ALPHA, C.ALPHA_OPTIONS[-1], C.ALPHA_OPTIONS[0]),
    "raster_select": SettingSpec("r", int, C.DEFAULT_RASTER, C.RASTER_OPTIONS[0], C.RASTER_OPTIONS[-1]),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, 0, C.SEED_MAX),
}
PRESET_KEYS = {"a": "a_select", "amp_pct": "amp_slider", "period": "period_select", "alpha": "alpha_select",
               "raster": "raster_select", "seed": "seed_input"}
OPTIONS = {"a_select": C.A_OPTIONS, "period_select": C.PERIOD_OPTIONS, "alpha_select": C.ALPHA_OPTIONS,
           "raster_select": C.RASTER_OPTIONS}       # Regler, die nur feste Stufen kennen


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def snap_to_option(state_key, value):
    """Regler mit festen Stufen: ein Permalink-Wert dazwischen rastet auf die nächste Stufe ein (bei Gleichstand auf die kleinere)."""
    return min(OPTIONS[state_key], key=lambda o: (abs(o - value), o))


def snap_amp(value):
    """Die Amplitude rastet auf das nächste Vielfache der Schrittweite (10 %) innerhalb der Grenzen ein."""
    snapped = round(value / C.AMP_PCT_STEP) * C.AMP_PCT_STEP
    return int(min(C.AMP_PCT_MAX, max(C.AMP_PCT_MIN, snapped)))


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
                if value != value:                     # NaN
                    continue
                if spec.lo is not None:
                    value = max(spec.lo, value)
                if spec.hi is not None:
                    value = min(spec.hi, value)
                if state_key in OPTIONS:
                    value = snap_to_option(state_key, value)
                if state_key == "amp_slider":
                    value = snap_amp(value)
                st.session_state[state_key] = value
            except (ValueError, TypeError):
                pass
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    for key, state_key in PRESET_KEYS.items():
        st.session_state[state_key] = C.PRESETS[name][key]


def randomize_seed():
    st.session_state["seed_input"] = random.randint(0, C.SEED_MAX)
