# components/probe_panel.py
from __future__ import annotations
from dataclasses import asdict
from typing import Dict
from dash import html, dcc, Input, Output, State, no_update
import dash_bootstrap_components as dbc

from auto_provision import provision_probe
from probe_discovery import ProbeInfo, ProbeDiscovery

# ---------------- UI ----------------
ProbePanel = dbc.Card(
    dbc.CardBody([
        html.Div(className="d-flex justify-content-between align-items-center mb-2", children=[
            html.H5("Probes (auto-discovery)", className="mb-0"),
            html.Small(id="probes-status", className="text-muted")
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Label("Auto-provision new probes"),
                dcc.Checklist(id="auto-prov-enabled", options=[{"label": " Enabled", "value": "on"}],
                              value=["on"], inputStyle={"marginRight": "0.35rem"})
            ], width=6),
            dbc.Col([
                dbc.Label("Push interval (ms)"),
                dcc.Input(id="prov-interval-ms", type="number", min=500, step=100, value=5000)
            ], width=6),
        ], className="gy-2"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Provision token (optional)"),
                dcc.Input(id="prov-token", type="text", value="", placeholder="X-Token to send to hub")
            ], width=12)
        ], className="gy-2"),
        html.Div(className="mt-2 d-flex gap-2", children=[
            html.Button("Provision ALL now", id="btn-provision-all", className="btn btn-primary btn-sm"),
            html.Button("Refresh list", id="btn-refresh-probes", className="btn btn-secondary btn-sm"),
        ]),
        html.Hr(),
        dcc.Loading(dbc.ListGroup(id="probes-list"), type="default"),
        dcc.Interval(id="probes-interval", interval=4000, n_intervals=0)
    ]),
    className="h-100"
)

# -------------- Callbacks --------------
def register_probe_callbacks(app, discovery: ProbeDiscovery, server_base: str):
    """
    Wire up callbacks for the probe panel.
    - Polls discovery to show current probes
    - One-click "Provision ALL" that posts server_base to each probe /provision
    """
    def _probe_cards(probes: Dict[str, ProbeInfo]):
        if not probes:
            return [dbc.ListGroupItem("(no probes found yet)")]
        items = []
        for host, info in sorted(probes.items(), key=lambda kv: kv[1].name.lower()):
            line = html.Div([
                html.Strong(info.name),
                html.Span(
                    [" ", dbc.Badge("ID", color="secondary", className="ms-2 me-1"), html.Code(info.name)],
                    className="d-inline-block"
                ),
                html.Small(f" — {info.ip or info.host}:{info.port}", className="text-muted ms-2 d-inline-block"),
            ])
            items.append(dbc.ListGroupItem(line))
        return items

    @app.callback(
        Output("probes-list", "children"),
        Output("probes-status", "children"),
        Input("probes-interval", "n_intervals"),
        Input("btn-refresh-probes", "n_clicks"),
        prevent_initial_call=False
    )
    def _refresh_list(_n, _click):
        probes = discovery.list_probes()
        status = f"{len(probes)} discovered"
        return _probe_cards(probes), status

    @app.callback(
        Output("btn-provision-all", "children"),
        Input("btn-provision-all", "n_clicks"),
        State("prov-token", "value"),
        State("prov-interval-ms", "value"),
        State("auto-prov-enabled", "value"),
        prevent_initial_call=True
    )
    def _provision_all(n, token, interval_ms, auto_vals):
        if not n:
            return no_update
        token = token or ""
        interval = max(500, int(interval_ms or 5000))
        count = 0
        ok = 0
        for host, info in discovery.list_probes().items():
            count += 1
            try:
                if provision_probe(info.host, info.port, server_base, token=token, interval_ms=interval):
                    ok += 1
            except Exception:
                pass
        return f"Provisioned {ok}/{count}"
