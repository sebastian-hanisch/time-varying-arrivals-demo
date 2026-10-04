"""Zeitvariable Ankünfte - Besetzung für Wellen - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Sechstes Stück der Konzepte-Linie "Warteschlangentheorie und Simulation": Die Ankunftsrate des Terminal-Gates schwankt in Wellen
(Tagesverlauf, Fähr-Ankünfte). Die Demo vergleicht zwei Wege, die Spurzahl über die Zeit zu planen: nach dem MOMENTANEN Angebot
(als wäre die Last gerade konstant) und nach dem VERZÖGERTEN Angebot (Modified Offered Load: gedämpft und verschoben, weil wer vor
einer Abfertigungsdauer ankam, noch im System ist). Siehe README für die Einordnung in die Linie.

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import tva_constants as C
from tva_evaluation import (gate_curves, load_precomputed, nearest, simulate_gate, stability, study_cell)
from tva_presets import (apply_preset, bounds, init_session_state_defaults, load_permalink_settings, randomize_seed,
                         sync_query_params)
from tva_visualization import (build_offer_chart, build_offset_chart, build_raster_chart, build_staffing_chart,
                               build_study_chart, build_wait_chart, period_label)

st.set_page_config(page_title="Zeitvariable Ankünfte – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _precomputed():
    return load_precomputed()


@st.cache_data(show_spinner=False)
def _curves(a, amp, period, alpha, raster):
    return gate_curves(a, amp, period, alpha, raster)


@st.cache_data(show_spinner=False)
def _sims(a, amp, period, alpha, raster, seed):
    cur = gate_curves(a, amp, period, alpha, raster)
    out = {}
    for kind, key in (("psa", "c_psa"), ("mol", "c_mol")):
        res = simulate_gate(a, amp, period, cur[key], C.LIVE_CUSTOMERS, seed)
        out[kind] = {"wait": res.wait_prob(), "stab": stability(res, alpha), "horizon": res.horizon}
    return out


def _span(s):
    return f"{C.fmt_pct(s['min'])} bis {C.fmt_pct(s['max'])}"


st.title("🌊 Zeitvariable Ankünfte: Besetzung für Wellen")
st.markdown(
    """
Die Stücke 3 bis 5 nahmen eine **konstante Ankunftsrate** an. Echte Gates haben **Wellen**: Tagesverlauf, Morgenspitze, Lkw-Pulks
nach einer Fährankunft. Naheliegend ist, zu jeder Zeit so zu besetzen, **als wäre die Last gerade konstant** (Wurzelregel mit dem
**momentanen Angebot**). Das geht schief, weil die Schlange ein **Gedächtnis** hat: Wer vor einer Abfertigungsdauer angekommen ist,
steht noch im System. Das richtige Maß ist das **verzögerte Angebot** (*Modified Offered Load*): die mittlere Zahl beschäftigter
Spuren bei unendlich vielen Spuren, **gedämpft und verschoben** gegenüber der Ankunftsrate. Wer danach besetzt, hält die
Wartewahrscheinlichkeit zu jeder Tageszeit nahe am Ziel, **bei derselben mittleren Spurzahl**.
"""
)
st.caption(
    "Sechstes Stück der Linie „Warteschlangentheorie und Simulation“, aufbauend auf "
    "[square-root-staffing-demo](https://sebastianhanisch-square-root-staffing-demo.streamlit.app/) (Wurzelregel), "
    "[erlang-a-demo](https://sebastianhanisch-erlang-a-demo.streamlit.app/) und "
    "[mmc-queue-demo](https://sebastianhanisch-mmc-queue-demo.streamlit.app/) (Erlang C). Jedes Folgestück hebt eine der Annahmen "
    "unter „Wo die Annahmen enden“ auf."
)

with st.expander("So funktioniert die Besetzung für Wellen", expanded=True):
    st.markdown(
        """
- **Welle:** Die Ankunftsrate ist λ(t) = a·μ·(1 + A·sin(2πt/P)): mittleres Angebot a (Erlang), Amplitude A, Periode P.
- **Momentanes Angebot** λ(t)/μ: so viele Spuren wären beschäftigt, wenn die Last gerade stationär wäre (PSA, *pointwise stationary
  approximation*).
- **Verzögertes Angebot** m(t) = ∫ λ(t − s)·e^(−μs) ds: ein Lkw, der vor s Minuten ankam, ist noch in Abfertigung, wenn seine Dauer
  länger als s ist. Bei einer Sinuswelle ist m(t) **gedämpft** und um **arctan(ω/μ)/ω Minuten** verschoben, bei 3 min Abfertigung
  etwa 3 Minuten.
- **Besetzung:** je Minute die kleinste Spurzahl, deren Erlang-C-Wartewahrscheinlichkeit beim jeweiligen Angebot höchstens das Ziel
  beträgt. Das Planungsraster (1, 15 oder 60 min) legt fest, wie oft die Spurzahl wechseln darf; im Block gilt das Maximum.
- **Simulation:** Ankünfte durch Ausdünnung, Spurzahl je Minute; wer eine Abfertigung beginnt, wird nicht abgebrochen.
        """
    )

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_cols = st.columns(len(C.PRESET_ORDER))
for i, name in enumerate(C.PRESET_ORDER):
    with preset_cols[i]:
        st.button(name, key=f"preset_{name}", width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name] or None)

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    a = st.select_slider("Mittleres Angebot a (Erlang)", options=C.A_OPTIONS, key="a_select",
                         help="So viele Spuren sind im Mittel gleichzeitig beschäftigt. Abfertigungsdauer fest 3 min je Spur.")
    amp_pct = st.slider("Amplitude der Welle", *bounds("amp_slider"), step=C.AMP_PCT_STEP, key="amp_slider", format="%d %%",
                        help="Wie stark die Ankunftsrate um ihr Mittel schwankt (0 % = konstant).")
    period = st.select_slider("Periode der Welle", options=C.PERIOD_OPTIONS, key="period_select", format_func=period_label,
                              help="Dauer eines Zyklus: schnelle Pulks (20 min) bis zum Tagesverlauf (24 h).")
    alpha = st.select_slider("Ziel: höchstens so viele müssen warten", options=C.ALPHA_OPTIONS, key="alpha_select",
                             format_func=lambda v: f"{v:.0%}", help="Zu jeder Tageszeit.")
    raster = st.select_slider("Planungsraster", options=C.RASTER_OPTIONS, key="raster_select", format_func=lambda v: f"{v} min",
                              help="Wie oft die Spurzahl wechseln darf; im Block gilt das Maximum der Minuten-Werte.")
    seed = st.number_input("Zufalls-Seed", min_value=bounds("seed_input")[0], max_value=bounds("seed_input")[1], step=1,
                           key="seed_input", help="Bestimmt alle Zufallszahlen der Simulation.")
    st.button("🎲 Neuen Lauf würfeln", on_click=randomize_seed)

a, amp_pct, period, raster, seed = int(a), int(amp_pct), int(period), int(raster), int(seed)
alpha = float(alpha)
amp = amp_pct / 100.0
sync_query_params({"a_select": a, "amp_slider": amp_pct, "period_select": period, "alpha_select": alpha, "raster_select": raster,
                   "seed_input": seed})

curves = _curves(a, amp, period, alpha, raster)
pre = _precomputed()
with st.spinner("Simuliere beide Besetzungen …"):
    sims = _sims(a, amp, period, alpha, raster, seed)
sp, sm = sims["psa"]["stab"], sims["mol"]["stab"]

st.markdown("---")
st.markdown("## 🌊 Zwei Besetzungen, eine Welle")
st.caption(
    f"Mittleres Angebot {a}, Amplitude {amp_pct} %, Periode {period_label(period)}, Ziel {C.fmt_pct(alpha)} Wartende zu jeder "
    f"Tageszeit, Planungsraster {raster} min. Simuliert: je Besetzung etwa {C.fmt_int(C.LIVE_CUSTOMERS)} Lkw."
)
r1 = st.columns(3)
r1[0].metric("Mittlere Spurzahl: momentanes Angebot", f"{curves['mean_psa']:.1f}")
r1[1].metric("Mittlere Spurzahl: verzögertes Angebot", f"{curves['mean_mol']:.1f}")
r1[2].metric("Verschiebung des verzögerten Angebots", f"{curves['lag_min']:.1f} min")
r2 = st.columns(3)
r2[0].metric("Wartewahrscheinlichkeit nach momentanem Angebot", _span(sp))
r2[1].metric("Wartewahrscheinlichkeit nach verzögertem Angebot", _span(sm))
r2[2].metric("Versatz der Angebote", f"{curves['offset_sqrt']:.2f}·√a",
             help="Größter Abstand zwischen momentanem und verzögertem Angebot über den Zyklus, in Einheiten von √a. Die Wurzelregel "
                  "kennt Sicherheitsstufen von etwa 1 bis 2: ein Versatz von 0.4 verschenkt davon schon einen großen Teil.")
r3 = st.columns(3)
r3[0].metric("Phasen mit verfehltem Ziel (momentanes Angebot)", f"{sp['missed']} von {sp['phases']}")
r3[1].metric("Phasen mit verfehltem Ziel (verzögertes Angebot)", f"{sm['missed']} von {sm['phases']}")
r3[2].metric("Spurzahl-Unterschied", f"{curves['mean_psa'] - curves['mean_mol']:+.1f}", help="Mittlere Spuren momentan minus verzögert.")

col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**Angebot über den Zyklus**")
    st.plotly_chart(build_offer_chart(curves, period), width="stretch", key=f"offer_{a}_{amp_pct}_{period}")
with col_b:
    st.markdown("**Spuren über den Zyklus**")
    st.plotly_chart(build_staffing_chart(curves, period), width="stretch", key=f"staff_{a}_{amp_pct}_{period}_{alpha}_{raster}")
st.markdown("**Simulierte Wartewahrscheinlichkeit je Phase des Zyklus**")
st.plotly_chart(build_wait_chart(sims["psa"]["wait"], sims["mol"]["wait"], alpha, period), width="stretch",
                key=f"wait_{a}_{amp_pct}_{period}_{alpha}_{raster}_{seed}")
st.info(
    f"Beide Besetzungen kommen im Mittel mit **{curves['mean_psa']:.1f}** und **{curves['mean_mol']:.1f}** Spuren aus; es geht nur um "
    f"das Timing. Zu jeder Phase warten nach dem momentanen Angebot {_span(sp)} der Lkw, nach dem verzögerten Angebot {_span(sm)}; "
    f"das Ziel sind {C.fmt_pct(alpha)}."
)
st.caption(
    f"Ein Live-Lauf ist kurz (etwa {sims['mol']['horizon'] / period:.0f} Zyklen): einzelne Phasen streuen deutlich um ihren wahren Wert, "
    "vor allem bei langer Periode. Die Studie unten mittelt je drei lange Läufe."
)

st.markdown("---")
st.subheader("📐 Wie schnell darf die Welle sein?")
study_a, study_amp = nearest(C.STUDY_A, a), nearest(C.STUDY_AMP, amp)
st.markdown(
    f"Wartewahrscheinlichkeit je Phase (Spanne von der kleinsten bis zur größten Phase, Punkt: Mittel) für beide Besetzungen über "
    f"verschiedene Perioden; Angebot {study_a}, Amplitude {C.fmt_pct(study_amp)}, Ziel {C.fmt_pct(pre['study_alpha'])}, Raster 1 min. "
    f"Je Zelle {pre['study_reps']} Läufe à {C.fmt_int(pre['study_customers'])} Lkw."
)
st.plotly_chart(build_study_chart(pre, study_a, study_amp), width="stretch", key=f"study_{study_a}_{study_amp}")
header = "| Periode | nach momentanem Angebot | nach verzögertem Angebot |\n|---|---|---|\n"
body = ""
for p in C.STUDY_PERIOD:
    cp, cm = study_cell(pre, study_a, study_amp, p, 1, "psa"), study_cell(pre, study_a, study_amp, p, 1, "mol")
    body += f"| {period_label(p)} | {_span(cp)}, {cp['missed']} von {len(cp['pw'])} Phasen verfehlt | {_span(cm)}, {cm['missed']} von {len(cm['pw'])} Phasen verfehlt |\n"
st.markdown(header + body)
cell_p, cell_m = study_cell(pre, study_a, study_amp, period, 1, "psa"), study_cell(pre, study_a, study_amp, period, 1, "mol")
st.info(
    f"Bei Periode {period_label(period)} (Angebot {study_a}, Amplitude {C.fmt_pct(study_amp)}): nach dem momentanen Angebot warten je Phase "
    f"{_span(cell_p)}, nach dem verzögerten {_span(cell_m)}, bei {cell_p['mean_lanes']:.1f} gegen {cell_m['mean_lanes']:.1f} Spuren im Mittel."
)
if cell_m["se"] is not None:
    st.caption(
        f"Rauschen: der größte Standardfehler einer Phase beträgt {100 * max(x for x in cell_m['se']):.1f} Prozentpunkte (verzögertes Angebot) "
        f"und {100 * max(x for x in cell_p['se']):.1f} (momentanes Angebot); Unterschiede darunter sind Zufall."
    )

st.markdown("---")
st.subheader("🔬 Warum ist das momentane Angebot so schlecht?")
st.markdown(
    "Das verzögerte Angebot hinkt dem momentanen um etwa eine Abfertigungsdauer hinterher. Die Wurzelregel arbeitet mit einem Puffer von "
    "wenigen √a: ein Versatz in dieser Größe zerstört die Sicherheitsstufe."
)
st.plotly_chart(build_offset_chart(period), width="stretch", key=f"offset_{period}")
st.info(
    f"Bei Periode {period_label(period)} und Amplitude {amp_pct} % beträgt der größte Versatz **{curves['offset_sqrt']:.2f}·√a**; "
    f"das verzögerte Angebot ist um {curves['lag_min']:.1f} min verschoben. Je schneller die Welle, desto größer der Versatz; bei sehr "
    "schnellen Wellen glättet das verzögerte Angebot die Welle fast ganz weg, und der Versatz nähert sich der ganzen Amplitude der "
    "Welle (A·√a)."
)

st.markdown("---")
st.subheader("🔬 Was kostet das Planungsraster?")
st.markdown(
    "Spurzahlen lassen sich in der Praxis nur in Schichtblöcken ändern. Gilt im Block das Maximum, sinkt der Anteil Wartender weit unter "
    "das Ziel: die Spuren stehen bereit, werden aber nicht gebraucht."
)
st.plotly_chart(build_raster_chart(pre, study_a, study_amp, period), width="stretch", key=f"raster_{study_a}_{study_amp}_{period}")
cells = {r: study_cell(pre, study_a, study_amp, period, r, "mol") for r in C.STUDY_RASTER}
base = cells[1]["mean_lanes"]
st.info(
    f"Bei Periode {period_label(period)} (Angebot {study_a}, Amplitude {C.fmt_pct(study_amp)}, Besetzung nach dem verzögerten Angebot): "
    f"Raster 1 min {cells[1]['mean_lanes']:.1f} Spuren (im Mittel {C.fmt_pct(cells[1]['mean'])} Wartende), Raster 15 min "
    f"{cells[15]['mean_lanes']:.1f} (+{100 * (cells[15]['mean_lanes'] / base - 1):.1f} %, {C.fmt_pct(cells[15]['mean'])}), Raster 60 min "
    f"{cells[60]['mean_lanes']:.1f} (+{100 * (cells[60]['mean_lanes'] / base - 1):.1f} %, {C.fmt_pct(cells[60]['mean'])})."
)

st.markdown("---")
st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Abfertigungsdauer exponentiell** | Das verzögerte Angebot hängt von der Verteilung der Dauer ab (nicht nur vom Mittel): bei anderer Streuung ist die Verschiebung eine andere. | **[M/G/1, Kingman-Näherung](https://sebastianhanisch-mg1-kingman-demo.streamlit.app/)** |
| **Die Welle ist bekannt und regelmäßig** | Reale Lasten sind nur geschätzt; Prognosefehler erzeugen zusätzliche Streuung, die hier fehlt. | kein Folgestück |
| **Unendliche Geduld** | Mit Abwanderung (Stück 4) ändert sich die Kennzahl; die hier gerechnete Besetzung gilt nur für Erlang C. | kein Folgestück |
| **Ein Gate** | Wellen laufen durch mehrere Stationen (Gate, Kran, Stapel) und verändern sich dabei. | **Jackson-Netze** (Folgestück) |
| **Alle Lkw gleich wichtig** | Eilige Lkw brauchen Vorfahrt; das verschiebt das Warten zwischen den Klassen. | **Prioritätsklassen** (Folgestück) |
| **Spurzahl ohne Kosten und ohne Wechselaufwand** | Wechsel sind teuer: hier nur über das Raster abgebildet, nicht optimiert. | kein Folgestück |
"""
)
st.caption(
    "Verwandt im Portfolio: [square-root-staffing-demo](https://sebastianhanisch-square-root-staffing-demo.streamlit.app/) (Stück 5), "
    "[erlang-a-demo](https://sebastianhanisch-erlang-a-demo.streamlit.app/) (Stück 4), "
    "[mmc-queue-demo](https://sebastianhanisch-mmc-queue-demo.streamlit.app/) (Stück 3), "
    "[mm1-queue-demo](https://sebastianhanisch-mm1-queue-demo.streamlit.app/) (Stück 1) und die Hafen-Demo "
    "[truck-appointment-demo](https://sebastianhanisch-truck-appointment-demo.streamlit.app/) (Terminvergabe für Lkw: dort planen "
    "Termine die Ankünfte, hier schwankt die Last von selbst)."
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell.** $M_t/M/c_t$: nichtstationärer Poisson-Prozess mit Rate $\lambda(t) = a\mu\bigl(1 + A\sin(2\pi t/P)\bigr)$, exponentielle
Abfertigung mit Rate $\mu$, $c(t)$ Spuren, eine FIFO-Schlange, unendliche Geduld.

**Momentanes Angebot** (PSA): $a(t) = \lambda(t)/\mu$.

**Verzögertes Angebot** (MOL): $m(t) = \int_0^\infty \lambda(t - s)\,e^{-\mu s}\,ds$, die mittlere Zahl beschäftigter Server im Modell mit
unendlich vielen Servern $M_t/M/\infty$; sie löst $m'(t) = \lambda(t) - \mu\,m(t)$. Für die Sinuswelle mit $\omega = 2\pi/P$:
$$m(t) = a\Bigl(1 + \frac{A}{\sqrt{1 + (\omega/\mu)^2}}\,\sin\bigl(\omega t - \arctan(\omega/\mu)\bigr)\Bigr),$$
also um den Faktor $1/\sqrt{1 + (\omega/\mu)^2}$ gedämpft und um $\arctan(\omega/\mu)/\omega$ verschoben.

**Besetzung.** Zu jeder Minute die kleinste ganze Zahl $c > $ Angebot mit Erlang-C-Wartewahrscheinlichkeit
$C(c, \text{Angebot}) \le \alpha$ (Jennings, Mandelbaum, Massey und Whitt 1996 nennen das verzögerte Angebot als Grundlage der
Besetzung, Feldman et al. 2008 iterieren sie für allgemeine Fälle). Mit Raster $w$: $c$ im Block ist das Maximum der Minuten-Werte.

**Warum PSA scheitert.** Ändert sich das Angebot um $\dot a$ je Minute, beträgt der Versatz zum verzögerten Angebot etwa $\dot a/\mu$,
also $\dot a/(\mu\sqrt a)$ in Einheiten von $\sqrt a$ gegenüber der Sicherheitsstufe von ein bis zwei.

**Simulation.** Kandidaten-Ankünfte mit der Höchstrate $\lambda_{\max}$, jeder mit Wahrscheinlichkeit $\lambda(t)/\lambda_{\max}$ angenommen
(Ausdünnung); die Spurzahl wechselt je Minute, Wartende rücken sofort nach, sinkt die Spurzahl unter die Zahl der Beschäftigten,
beenden diese ihre Abfertigung. Wartewahrscheinlichkeit je Phase = Anteil der Ankünfte der Phase, die nicht sofort bedient werden.

Implementiert in `tva_formulas.py` (Angebote, Besetzung, numerische Kontrolle), `tva_simulation.py` (Ausdünnung, zeitvariable Spuren),
`tva_evaluation.py` (Kurven, Stabilität, Studie), `generate_precomputed.py` (vorgerechnete Studie).
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html))."
)
