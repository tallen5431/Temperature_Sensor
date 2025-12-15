from dash import html, dcc, Output, Input, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import pandas as pd, os, datetime

CSV_FILE = os.getenv('CSV_FILE', 'temperature_log.csv')

GaugeCard = dbc.Card(
    dbc.CardBody([
        html.H5(['Current Temperature', html.Span(' 🟢 LIVE', id='live-badge', className='ms-2 text-success small fw-bold')], className='card-title'),
        dcc.Graph(id='temp-gauge', style={'height': '230px'})
    ]), className='h-100 gauge-card'
)

MetricsRow = dbc.Row([
    dbc.Col(dbc.Card(dbc.CardBody([
        html.H6('Connected Probes'), html.H2(id='metric-probes', className='fw-bold')
    ]), className='h-100'), width=4),
    dbc.Col(dbc.Card(dbc.CardBody([
        html.H6('Last Update'), html.H2(id='metric-lastupdate', className='fw-bold', style={'fontSize': '1.5rem'})
    ]), className='h-100'), width=4),
    dbc.Col(dbc.Card(dbc.CardBody([
        html.H6('Logging Status'), html.H2(id='metric-logging', className='fw-bold text-success')
    ]), className='h-100'), width=4)
], className='g-3 mb-3')

GraphCard = dbc.Card(
    dbc.CardBody([
        html.H5('Temperature History'),
        dcc.Graph(id='graph-temp', style={'height': '360px'}),
        html.Small(id='heartbeat', className='text-muted mt-2 d-block'),
        dcc.Interval(id='dash-refresh', interval=5000, n_intervals=0)
    ]), className='h-100 graph-card'
)

DashboardLayout = html.Div([
    MetricsRow,
    dbc.Row([
        dbc.Col(GaugeCard, width=4),
        dbc.Col(GraphCard, width=8)
    ], className='g-3 align-items-stretch')
])

def register_dashboard_callbacks(app, finder, cfg):
    @app.callback(
        Output('temp-gauge', 'figure'),
        Output('graph-temp', 'figure'),
        Output('metric-probes', 'children'),
        Output('metric-lastupdate', 'children'),
        Output('metric-logging', 'children'),
        Output('heartbeat', 'children'),
        Input('dash-refresh', 'n_intervals')
    )
    def update_dashboard(_):
        try:
            df = pd.read_csv(CSV_FILE)
            if df.empty:
                raise ValueError('No data')
            row = df.tail(1).iloc[0]
            t_c = float(row['temperature_c'])
            t_f = float(row['temperature_f'])
            ts = row['timestamp']
            gauge = go.Figure(go.Indicator(
                mode='gauge+number',
                value=t_c,
                number={'suffix': ' °C'},
                gauge={'axis': {'range': [0, 100]}, 'bar': {'color': '#00bcd4'}},
                domain={'x': [0, 1], 'y': [0, 1]}
            ))
            gauge.update_layout(margin=dict(t=10,b=30,l=10,r=10), height=250, paper_bgcolor='rgba(0,0,0,0)', font_color='white')
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['temperature_c'], mode='lines', name='°C'))
            fig.update_layout(margin=dict(t=20,b=20,l=0,r=10),template='plotly_dark',xaxis_title='Time',yaxis_title='Temp °C')
            probes = len((finder.list_probes() or {}))
            logging_status = 'ON' if cfg.get('pull_enabled', True) else 'OFF'
            last_dt = datetime.datetime.fromisoformat(ts)
            delta = (datetime.datetime.now() - last_dt).total_seconds()
            hb = f'Last sync {int(delta)} s ago' if delta < 60 else f'Last sync {int(delta//60)} min ago'
            if delta < 10:
                hb += ' ✓'
            return gauge, fig, probes, ts, logging_status, hb
        except Exception:
            empty = go.Figure()
            empty.update_layout(template='plotly_dark',paper_bgcolor='rgba(0,0,0,0)',xaxis={'visible':False},yaxis={'visible':False})
            return empty, empty, '0', '(no data)', 'OFF', 'No signal'
