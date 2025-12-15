import pandas as pd
from pathlib import Path
from dash import html, dcc, Input, Output, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objs as go

# ---- UI section -------------------------------------------------------------
GraphSection = dbc.Card(
    dbc.CardBody([
        html.H5("Temperature Graph"),
        html.Div(id="probe-badges", className="mb-2"),
        dcc.Graph(id="temp-graph", config={"displayModeBar": False}),
    ])
)

# ---- Helpers ----------------------------------------------------------------

def _safe_read(csv_file: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(csv_file)
        for col in ("timestamp", "temperature_c", "temperature_f"):
            if col not in df.columns:
                return pd.DataFrame(columns=["timestamp","temperature_c","temperature_f","probe_id"])  # empty
        if "probe_id" not in df.columns:
            df["probe_id"] = "(default)"
        return df
    except Exception:
        return pd.DataFrame(columns=["timestamp","temperature_c","temperature_f","probe_id"])  # empty


def _build_figure(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    if df.empty:
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=20, r=10, t=10, b=30),
            height=360,
            showlegend=False,
            xaxis_title="Time",
            yaxis_title="Temperature (°C)",
        )
        return fig

    df = df.copy()
    df["_ts"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.sort_values(["probe_id", "_ts"]).drop(columns=["_ts"])

    for pid, chunk in df.groupby("probe_id"):
        label = str(pid).strip() if pd.notna(pid) and str(pid).strip() else "(default)"
        fig.add_trace(go.Scatter(
            x=chunk["timestamp"], y=chunk["temperature_c"],
            mode="lines+markers",
            name=label,
            line=dict(width=2),
            marker=dict(size=6),
            hovertemplate=(
                "<b>%{text}</b><br>"  # probe id
                "%{x|%Y-%m-%d %H:%M:%S}<br>"
                "%{y:.2f} °C<extra></extra>"
            ),
            text=[label] * len(chunk),
        ))

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=10, t=10, b=30),
        height=360,
        legend_title_text="Probe",
        xaxis_title="Time",
        yaxis_title="Temperature (°C)",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(zeroline=False)
    return fig


def _badge_row(df: pd.DataFrame):
    if df.empty:
        return html.Small("(no data yet)", className="text-muted")

    last_by_probe = (
        df.assign(_ts=pd.to_datetime(df["timestamp"], errors="coerce"))
          .sort_values(["probe_id","_ts"]).groupby("probe_id").tail(1)
    )
    badges = []
    for _, row in last_by_probe.iterrows():
        pid = str(row.get("probe_id", "(default)"))
        ts  = str(row.get("timestamp", ""))
        c   = row.get("temperature_c", None)
        label = f"{pid} — {ts}"
        title = f"Last: {c:.2f}°C at {ts}" if c is not None else label
        badges.append(dbc.Badge(label, color="info", className="me-2 mb-2", title=title))
    return html.Div(badges)


# ---- Callbacks --------------------------------------------------------------

def register_callbacks(app, csv_path: Path):
    @app.callback(
        Output("temp-graph", "figure"),
        Output("probe-badges", "children"),
        Input("ui-refresh", "n_intervals"),
        prevent_initial_call=False,
    )
    def _refresh(_n):
        df = _safe_read(csv_path)
        return _build_figure(df), _badge_row(df)
