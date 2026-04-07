"""
Dash-Dashboard: Kraftstoffpreis-Verlauf für Tankstellen im Raum Tostedt.
Erreichbar unter http://<mac-ip>:8050 im lokalen Netzwerk.

Aggregationslogik:
  Tag, Woche  → alle Messpunkte (Rohdaten)
  Monat       → Tagesdurchschnitt
  Jahr        → Wochendurchschnitt
"""
from datetime import datetime, timedelta

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback, dash_table, dcc, html
from sqlalchemy import func

from db import Price, Station, get_session

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

FUEL_OPTIONS = [
    {"label": "Super E5",  "value": "e5"},
    {"label": "Super E10", "value": "e10"},
    {"label": "Diesel",    "value": "diesel"},
]

RANGE_OPTIONS = [
    {"label": "Tag",   "value": "day"},
    {"label": "Woche", "value": "week"},
    {"label": "Monat", "value": "month"},
    {"label": "Jahr",  "value": "year"},
]

RANGE_DELTA = {
    "day":   timedelta(days=1),
    "week":  timedelta(weeks=1),
    "month": timedelta(days=30),
    "year":  timedelta(days=365),
}

FUEL_LABEL = {"e5": "Super E5", "e10": "Super E10", "diesel": "Diesel"}

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

CARD = {
    "background": "#ffffff",
    "borderRadius": "12px",
    "padding": "20px",
    "boxShadow": "0 1px 4px rgba(0,0,0,.08)",
}

LABEL = {
    "fontSize": "11px",
    "fontWeight": "600",
    "letterSpacing": "0.6px",
    "textTransform": "uppercase",
    "color": "#888",
    "marginBottom": "10px",
    "display": "block",
}

RADIO_ITEM = {"display": "block", "padding": "5px 0", "cursor": "pointer", "fontSize": "14px"}

# ---------------------------------------------------------------------------
# Hilfsfunktion: Aggregation je nach Zeitraum
# ---------------------------------------------------------------------------

def _get_trace_data(s, sid: str, fuel_type: str, time_range: str, since: datetime):
    """
    Gibt (x_werte, y_werte) zurück.
    Tag/Woche: Rohdaten
    Monat:     Tagesdurchschnitt
    Jahr:      Wochendurchschnitt
    """
    fuel_col = getattr(Price, fuel_type)

    if time_range in ("day", "week"):
        rows = (
            s.query(Price.recorded_at, fuel_col)
            .filter(Price.station_id == sid, Price.recorded_at >= since)
            .filter(fuel_col.isnot(None))
            .order_by(Price.recorded_at)
            .all()
        )
        return [r[0] for r in rows], [r[1] for r in rows]

    elif time_range == "month":
        # Tagesdurchschnitt: nach Datum gruppieren
        rows = (
            s.query(
                func.date(Price.recorded_at).label("day"),
                func.avg(fuel_col).label("avg_price"),
            )
            .filter(Price.station_id == sid, Price.recorded_at >= since)
            .filter(fuel_col.isnot(None))
            .group_by(func.date(Price.recorded_at))
            .order_by(func.date(Price.recorded_at))
            .all()
        )
        return [r[0] for r in rows], [round(r[1], 3) for r in rows]

    else:  # year
        # Wochendurchschnitt: nach ISO-Kalenderwoche gruppieren
        rows = (
            s.query(
                func.strftime("%Y-%W", Price.recorded_at).label("week"),
                func.avg(fuel_col).label("avg_price"),
            )
            .filter(Price.station_id == sid, Price.recorded_at >= since)
            .filter(fuel_col.isnot(None))
            .group_by(func.strftime("%Y-%W", Price.recorded_at))
            .order_by(func.strftime("%Y-%W", Price.recorded_at))
            .all()
        )
        return [r[0] for r in rows], [round(r[1], 3) for r in rows]


# ---------------------------------------------------------------------------
# App-Layout
# ---------------------------------------------------------------------------

app = Dash(__name__, title="Fuel Tracker · Tostedt")
app.layout = html.Div([

    # ── Header ──────────────────────────────────────────────────────────────
    html.Div([
        html.Span("⛽", style={"fontSize": "22px"}),
        html.Div([
            html.H1("Fuel Tracker",
                    style={"margin": 0, "fontSize": "18px", "fontWeight": "600"}),
            html.Span("Raum Tostedt · Tankerkönig MTS-K",
                      style={"fontSize": "12px", "color": "#999"}),
        ]),
    ], style={
        "display": "flex", "alignItems": "center", "gap": "12px",
        "padding": "14px 24px", "background": "#fff",
        "borderBottom": "1px solid #eee", "marginBottom": "20px",
    }),

    # ── Hauptbereich ────────────────────────────────────────────────────────
    html.Div([

        # ── Seitenleiste ────────────────────────────────────────────────────
        html.Div([

            # Kraftstoff
            html.Div([
                html.Span("Kraftstoff", style=LABEL),
                dcc.RadioItems(
                    id="fuel-type",
                    options=FUEL_OPTIONS,
                    value="e10",
                    labelStyle=RADIO_ITEM,
                ),
            ], style={**CARD, "marginBottom": "16px"}),

            # Zeitraum
            html.Div([
                html.Span("Zeitraum", style=LABEL),
                dcc.RadioItems(
                    id="time-range",
                    options=RANGE_OPTIONS,
                    value="week",
                    labelStyle=RADIO_ITEM,
                ),
            ], style={**CARD, "marginBottom": "16px"}),

            # Tankstellen-Filter
            html.Div([
                html.Div([
                    html.Span("Tankstellen", style={**LABEL, "marginBottom": 0}),
                    html.Span("alle", id="btn-all",
                              style={"fontSize": "11px", "color": "#0070f3",
                                     "cursor": "pointer", "userSelect": "none"}),
                ], style={"display": "flex", "justifyContent": "space-between",
                          "alignItems": "center", "marginBottom": "10px"}),
                dcc.Checklist(
                    id="station-filter",
                    options=[],
                    value=[],
                    labelStyle={**RADIO_ITEM, "lineHeight": "1.4"},
                    inputStyle={"marginRight": "8px"},
                ),
            ], style=CARD),

        ], style={"width": "210px", "flexShrink": 0}),

        # ── Rechte Seite ────────────────────────────────────────────────────
        html.Div([

            # Chart + Hinweis zur Aggregation
            html.Div([
                html.Div(id="aggregation-hint", style={
                    "fontSize": "11px", "color": "#aaa",
                    "textAlign": "right", "marginBottom": "4px",
                }),
                dcc.Graph(
                    id="price-chart",
                    config={"displayModeBar": False},
                    style={"height": "380px"},
                ),
            ], style={**CARD, "marginBottom": "16px"}),

            # Stammdaten-Tabelle
            html.Div([
                html.Span("Stammdaten", style=LABEL),
                dash_table.DataTable(
                    id="station-table",
                    columns=[
                        {"name": "Marke",   "id": "brand"},
                        {"name": "Name",    "id": "name"},
                        {"name": "Adresse", "id": "address"},
                        {"name": "Ort",     "id": "place"},
                        {"name": "Entf.",   "id": "dist"},
                        {"name": "E5",      "id": "e5"},
                        {"name": "E10",     "id": "e10"},
                        {"name": "Diesel",  "id": "diesel"},
                    ],
                    sort_action="native",
                    style_table={"overflowX": "auto"},
                    style_cell={
                        "fontSize": "13px", "textAlign": "left",
                        "padding": "9px 14px", "border": "none",
                        "fontFamily": "inherit", "whiteSpace": "normal",
                    },
                    style_header={
                        "fontWeight": "600", "fontSize": "12px",
                        "background": "#f5f5f5", "border": "none",
                        "color": "#555",
                    },
                    style_data_conditional=[
                        {"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"},
                    ],
                ),
            ], style=CARD),

        ], style={"flex": 1, "minWidth": 0}),

    ], style={
        "display": "flex", "gap": "16px",
        "padding": "0 20px 24px 20px", "alignItems": "flex-start",
    }),

    # Intervall: sofort beim Laden + alle 15 min
    dcc.Interval(id="interval", interval=15 * 60 * 1000, n_intervals=0),

], style={
    "fontFamily": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, sans-serif",
    "background": "#f0f2f5",
    "minHeight": "100vh",
    "margin": 0,
})


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@callback(
    Output("station-filter", "options"),
    Output("station-filter", "value"),
    Input("interval", "n_intervals"),
    State("station-filter", "value"),
)
def refresh_station_list(_, current_selection):
    """Stationsliste aus DB laden; Benutzer-Auswahl beim Refresh erhalten."""
    with get_session() as s:
        stations = s.query(Station).order_by(Station.dist_km).all()

    options = [
        {"label": f"{st.brand}  ·  {st.place} ({st.dist_km:.1f} km)", "value": st.id}
        for st in stations
    ]
    all_ids = [st.id for st in stations]

    if not current_selection:
        return options, all_ids

    new = [i for i in all_ids if i not in current_selection]
    return options, current_selection + new


@callback(
    Output("station-filter", "value", allow_duplicate=True),
    Input("btn-all", "n_clicks"),
    State("station-filter", "options"),
    prevent_initial_call=True,
)
def select_all(_, options):
    return [o["value"] for o in options]


@callback(
    Output("price-chart", "figure"),
    Output("station-table", "data"),
    Output("aggregation-hint", "children"),
    Input("fuel-type", "value"),
    Input("time-range", "value"),
    Input("station-filter", "value"),
    Input("interval", "n_intervals"),
)
def update_view(fuel_type, time_range, selected_ids, _):
    selected_ids = selected_ids or []
    since = datetime.now() - RANGE_DELTA[time_range]

    # Hinweistext je nach Aggregationsstufe
    hint_map = {
        "day":   "Rohdaten · alle Messpunkte",
        "week":  "Rohdaten · alle Messpunkte",
        "month": "Tagesdurchschnitt",
        "year":  "Wochendurchschnitt",
    }

    traces     = []
    table_rows = []

    with get_session() as s:
        all_stations = {st.id: st for st in s.query(Station).all()}

        for sid in selected_ids:
            st = all_stations.get(sid)
            if not st:
                continue

            x, y = _get_trace_data(s, sid, fuel_type, time_range, since)
            if x:
                traces.append({
                    "name": f"{st.brand} · {st.place}",
                    "x": x,
                    "y": y,
                })

            # Letzter bekannter Preis für die Tabelle
            last = (
                s.query(Price)
                .filter(Price.station_id == sid)
                .order_by(Price.recorded_at.desc())
                .first()
            )
            table_rows.append({
                "brand":   st.brand,
                "name":    st.name,
                "address": f"{st.street} {st.house_number}".strip(),
                "place":   f"{st.post_code} {st.place}",
                "dist":    f"{st.dist_km:.1f} km",
                "e5":      f"{last.e5:.3f} €"     if last and last.e5     else "–",
                "e10":     f"{last.e10:.3f} €"    if last and last.e10    else "–",
                "diesel":  f"{last.diesel:.3f} €" if last and last.diesel else "–",
            })

    # ── Chart aufbauen ──────────────────────────────────────────────────────
    fig = go.Figure()

    # Monat/Jahr: Balkendiagramm mit Linien-Overlay passt besser für Durchschnitte
    # Tag/Woche: klassisches Linien-Diagramm
    mode = "lines+markers" if time_range in ("day", "week") else "lines+markers"
    marker_size = 4 if time_range in ("day", "week") else 6

    for t in traces:
        fig.add_trace(go.Scatter(
            x=t["x"],
            y=t["y"],
            mode=mode,
            name=t["name"],
            line={"width": 2},
            marker={"size": marker_size},
            hovertemplate="%{y:.3f} €<extra>%{fullData.name}</extra>",
        ))

    if not traces:
        fig.add_annotation(
            text="Noch keine Daten für diesen Zeitraum.",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font={"size": 14, "color": "#aaa"},
        )

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin={"t": 10, "b": 50, "l": 70, "r": 20},
        legend={"orientation": "h", "y": -0.18, "font": {"size": 12}},
        yaxis={
            "title": FUEL_LABEL[fuel_type],
            "tickformat": ".3f",
            "ticksuffix": " €",
            "gridcolor": "#f0f0f0",
            "zeroline": False,
        },
        xaxis={"gridcolor": "#f0f0f0", "showgrid": True},
        hovermode="x unified",
        font={"family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"},
    )

    return fig, table_rows, hint_map[time_range]
