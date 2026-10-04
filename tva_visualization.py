"""Plotly-Abbildungen der Demo zu zeitvariablen Ankünften: momentanes gegen verzögertes Angebot, Spurzahlen beider Staffelungen,
Wartewahrscheinlichkeit je Phase, Studie über die Periode, Versatz in √a, Planungsraster. Achsen sind gesperrt (fixedrange), damit
Touch-Geräte beim Scrollen nicht zoomen."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import tva_constants as C
import tva_formulas as F

PSA_COLOR = "#e45756"
MOL_COLOR = "#54a24b"
OFFER_COLOR = "#4c78a8"
TARGET_COLOR = "#f58518"


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height, legend_y=-0.25, top=10):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=top, b=10), legend=dict(orientation="h", y=legend_y),
                      plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def period_label(period):
    """Lesbare Periode: 20 min, 1 h, 4 h, 24 h."""
    return f"{period} min" if period < 60 else f"{period // 60} h"


def build_offer_chart(curves, period):
    """Momentanes Angebot λ(t)/μ und verzögertes Angebot m(t) über einen Zyklus: das verzögerte Angebot ist gedämpft und verschoben."""
    ts = curves["t"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ts, y=curves["momentary"], mode="lines", line=dict(color=PSA_COLOR, width=2.5),
                             name="momentanes Angebot λ(t)/μ"))
    fig.add_trace(go.Scatter(x=ts, y=curves["mol"], mode="lines", line=dict(color=MOL_COLOR, width=2.5),
                             name="verzögertes Angebot m(t)"))
    fig.update_xaxes(title_text=f"Zeit im Zyklus (Minuten, Periode {period_label(period)})", range=[0, period])
    fig.update_yaxes(title_text="Angebot (Erlang)")
    return _base(fig, 320)


def build_staffing_chart(curves, period):
    """Spurzahl über einen Zyklus für beide Staffelungen (Treppen)."""
    ts = curves["t"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ts, y=curves["c_psa"], mode="lines", line_shape="hv", line=dict(color=PSA_COLOR, width=2.5),
                             name="Spuren nach momentanem Angebot"))
    fig.add_trace(go.Scatter(x=ts, y=curves["c_mol"], mode="lines", line_shape="hv", line=dict(color=MOL_COLOR, width=2.5, dash="dash"),
                             name="Spuren nach verzögertem Angebot"))
    fig.update_xaxes(title_text="Zeit im Zyklus (Minuten)", range=[0, period])
    fig.update_yaxes(title_text="Spuren")
    return _base(fig, 320)


def build_wait_chart(wait_psa, wait_mol, alpha, period):
    """Simulierte Wartewahrscheinlichkeit je Phase des Zyklus für beide Staffelungen gegen das Ziel (Phasen ohne Ankunft entfallen)."""
    width = period / len(wait_psa)
    xs = [(k + 0.5) * width for k in range(len(wait_psa))]
    fig = go.Figure()
    for ys, label, color in ((wait_psa, "nach momentanem Angebot", PSA_COLOR), (wait_mol, "nach verzögertem Angebot", MOL_COLOR)):
        pts = [(x, y) for x, y in zip(xs, ys) if y is not None]
        fig.add_trace(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts], mode="lines+markers", line=dict(color=color, width=2.5),
                                 name=label, hovertemplate="%{x:.0f} min: %{y:.1%}<extra>" + label + "</extra>"))
    fig.add_hline(y=alpha, line=dict(color=TARGET_COLOR, width=2, dash="dash"), annotation_text=f"Ziel {alpha:.0%}",
                  annotation_position="top left")
    fig.update_xaxes(title_text="Phase im Zyklus (Minuten)", range=[0, period])
    fig.update_yaxes(title_text="Anteil der Lkw, die warten müssen", tickformat=".0%", rangemode="tozero")
    return _base(fig, 340, top=30)


def build_study_chart(precomputed, a, amp, raster=1):
    """Spanne der Wartewahrscheinlichkeit über die Phasen (kleinster bis größter Wert, Punkt = Mittel) je Periode für beide Staffelungen;
    waagerecht das Ziel."""
    from tva_evaluation import study_cell

    fig = go.Figure()
    for kind, label, color, shift in (("psa", "nach momentanem Angebot", PSA_COLOR, -0.12), ("mol", "nach verzögertem Angebot", MOL_COLOR, 0.12)):
        cells = [study_cell(precomputed, a, amp, p, raster, kind) for p in C.STUDY_PERIOD]
        xs = [i + shift for i in range(len(cells))]
        fig.add_trace(go.Scatter(x=xs, y=[c["mean"] for c in cells], mode="markers", marker=dict(color=color, size=9), name=label,
                                 error_y=dict(type="data", symmetric=False, array=[c["max"] - c["mean"] for c in cells],
                                              arrayminus=[c["mean"] - c["min"] for c in cells], color=color, thickness=3, width=6),
                                 hovertemplate="Mittel %{y:.1%}<extra>" + label + "</extra>"))
    fig.add_hline(y=precomputed["study_alpha"], line=dict(color=TARGET_COLOR, width=2, dash="dash"),
                  annotation_text=f"Ziel {precomputed['study_alpha']:.0%}", annotation_position="top left")
    fig.update_xaxes(title_text="Periode der Welle", tickmode="array", tickvals=list(range(len(C.STUDY_PERIOD))),
                     ticktext=[period_label(p) for p in C.STUDY_PERIOD], range=[-0.5, len(C.STUDY_PERIOD) - 0.5])
    fig.update_yaxes(title_text="Wartewahrscheinlichkeit je Phase (Spanne)", tickformat=".0%", rangemode="tozero")
    return _base(fig, 360, top=30)


def build_offset_chart(current_period):
    """Versatz zwischen momentanem und verzögertem Angebot in Einheiten von √a über der Periode, für drei Amplituden (Formel)."""
    periods = [5, 10, 20, 30, 45, 60, 90, 120, 180, 240, 360, 480, 720, 1440]
    fig = go.Figure()
    for amp, color in ((0.3, "#9ecae1"), (0.5, "#4c78a8"), (0.7, "#08306b")):
        fig.add_trace(go.Scatter(x=periods, y=[F.offset_in_sqrt_units(100, amp, p) for p in periods], mode="lines+markers",
                                 line=dict(color=color, width=2.5), name=f"Amplitude {amp:.0%}",
                                 hovertemplate="Periode %{x} min: %{y:.2f}·√a<extra>" + f"Amplitude {amp:.0%}</extra>"))
    fig.add_vline(x=current_period, line=dict(color="#888", width=1, dash="dot"))
    fig.update_xaxes(title_text="Periode der Welle (Minuten, log)", type="log", tickmode="array",
                     tickvals=[5, 20, 60, 240, 1440], ticktext=["5", "20", "60", "240", "1440"])
    fig.update_yaxes(title_text="Versatz in Einheiten von √a", rangemode="tozero")
    return _base(fig, 340)


def build_raster_chart(precomputed, a, amp, period):
    """Mittlere Spurzahl und mittlerer Anteil Wartender je Planungsraster (Staffelung nach verzögertem Angebot, Ziel 20 %)."""
    from tva_evaluation import study_cell

    cells = [study_cell(precomputed, a, amp, period, r, "mol") for r in C.STUDY_RASTER]
    labels = [f"{r} min" for r in C.STUDY_RASTER]
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Mittlere Spurzahl", "Mittlerer Anteil Wartender"), horizontal_spacing=0.14)
    fig.add_trace(go.Bar(x=labels, y=[c["mean_lanes"] for c in cells], marker_color=MOL_COLOR, showlegend=False,
                         hovertemplate="%{x}: %{y:.1f} Spuren<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Bar(x=labels, y=[c["mean"] for c in cells], marker_color=OFFER_COLOR, showlegend=False,
                         hovertemplate="%{x}: %{y:.1%}<extra></extra>"), row=1, col=2)
    fig.add_hline(y=precomputed["study_alpha"], line=dict(color=TARGET_COLOR, width=2, dash="dash"), row=1, col=2)
    fig.update_xaxes(title_text="Planungsraster", row=1, col=1)
    fig.update_xaxes(title_text="Planungsraster", row=1, col=2)
    fig.update_yaxes(rangemode="tozero", row=1, col=1)
    fig.update_yaxes(tickformat=".0%", rangemode="tozero", row=1, col=2)
    _base(fig, 340, top=40)
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    return fig
