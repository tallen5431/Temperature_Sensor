from __future__ import annotations
import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
from pathlib import Path

# --- Public UI section -------------------------------------------------------
GraphSection = dbc.Card(
    dbc.CardBody([
        html.H5("Temperature Graph"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Time range"),
                dcc.Dropdown(
                    id="range-select",
                    options=[
                        {"label": "Last 15 min", "value": "15m"},
                        {"label": "Last 1 hour", "value": "1h"},
                        {"label": "Last 6 hours", "value": "6h"},
                        {"label": "Last 24 hours", "value": "24h"},
                        {"label": "All", "value": "all"}
                    ],
                    value="1h",
                    clearable=False,
                )
            ], width=6),
            dbc.Col([
                dbc.Label("Auto refresh (sec)"),
                dcc.Input(id="graph-refresh-sec", type="number", min=1, step=1, value=5)
            ], width=6),
        ], className="gy-2"),
        dcc.Graph(id="temp-graph", figure=go.Figure()),
        dcc.Interval(id="graph-interval", interval=5000, n_intervals=0)
    ])
)

# --- Helpers ----------------------------------------------------------------

def _load_df(csv_file: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(csv_file)
        if df.empty:
            return pd.DataFrame(columns=["timestamp", "temperature_c", "temperature_f"])  # empty
        # parse timestamp
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
        return df
    except Exception:
        return pd.DataFrame(columns=["timestamp", "temperature_c", "temperature_f"])  # empty


def _filter_range(df: pd.DataFrame, range_key: str) -> pd.DataFrame:
    if df.empty or range_key == "all":
        return df
    now = df["timestamp"].max()
    if pd.isna(now):
        return df
    mapping = {
        "15m": pd.Timedelta(minutes=15),
        "1h": pd.Timedelta(hours=1),
        "6h": pd.Timedelta(hours=6),
        "24h": pd.Timedelta(hours=24),
    }
    delta = mapping.get(range_key)
    if not delta:
        return df
    return df[df["timestamp"] >= (now - delta)]


def _downsample(df: pd.DataFrame, target_max_points: int = 1500) -> pd.DataFrame:
    if df.empty:
        return df
    n = len(df)
    if n <= target_max_points:
        return df
    # Evenly sample indices to keep performance smooth
    idx = (pd.np.linspace(0, n - 1, target_max_points)).astype(int)  # type: ignore
    return df.iloc[idx]


def _make_figure(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not df.empty:
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["temperature_c"],
            mode="lines", name="Temp °C"
        ))
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["temperature_f"],
            mode="lines", name="Temp °F", yaxis="y2"
        ))
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=40),
            xaxis_title="Time",
            yaxis=dict(title="°C"),
            yaxis2=dict(title="°F", overlaying="y", side="right"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
    else:
        fig.update_layout(
            annotations=[dict(text="No data yet", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)]
        )
    return fig

# --- Callback registration ---------------------------------------------------

def register_callbacks(app, csv_file: Path):
    @app.callback(
        Output("temp-graph", "figure"),
        Output("graph-interval", "interval"),
        Input("graph-interval", "n_intervals"),
        Input("range-select", "value"),
        Input("graph-refresh-sec", "value"),
        prevent_initial_call=False,
    )
    def _update_graph(_n, range_key, refresh_sec):
        df = _load_df(csv_file)
        df = _filter_range(df, range_key or "1h")
        df = _downsample(df, 1500)
        fig = _make_figure(df)
        interval_ms = max(1, int(refresh_sec or 5)) * 1000
        return fig, interval_ms
