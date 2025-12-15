from dash import html, dcc, Output, Input, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import pandas as pd, os, datetime
from urllib.parse import quote

CSV_FILE = os.getenv('CSV_FILE', 'temperature_log.csv')

# --- Gauge Card ---
GaugeCard = dbc.Card(
    dbc.CardBody([
        html.H5(
            [
                'Current Temperature',
                html.Span(' 🟢 LIVE', id='live-badge',
                          className='ms-2 text-success small fw-bold')
            ],
            className='card-title'
        ),
        dcc.Graph(id='temp-gauge', style={'height': '230px'})
    ]),
    className='h-100 gauge-card'
)

# --- Metrics Row ---
MetricsRow = dbc.Row([
    dbc.Col(
        dbc.Card(dbc.CardBody([
            html.H6('Connected Probes'),
            html.H2(id='metric-probes', className='fw-bold')
        ]), className='h-100'), width=4),
    dbc.Col(
        dbc.Card(dbc.CardBody([
            html.H6('Last Update'),
            html.H2(id='metric-lastupdate', className='fw-bold',
                    style={'fontSize': '1.5rem'})
        ]), className='h-100'), width=4),
    dbc.Col(
        dbc.Card(dbc.CardBody([
            html.H6('Logging Status'),
            html.H2(id='metric-logging',
                    className='fw-bold text-success')
        ]), className='h-100'), width=4)
], className='g-3 mb-3')

# --- Graph Card ---
GraphCard = dbc.Card(
    dbc.CardBody([
        dbc.Row([
            dbc.Col(html.H5('Temperature History'), width='auto'),
            dbc.Col(
                dbc.Select(
                    id='time-range-selector',
                    options=[
                        {'label': '🕐 Last Hour', 'value': '1h'},
                        {'label': '🕕 Last 6 Hours', 'value': '6h'},
                        {'label': '📅 Last 24 Hours', 'value': '24h'},
                        {'label': '📆 Last Week', 'value': '7d'},
                        {'label': '📊 Last Month', 'value': '30d'},
                        {'label': '🌍 All Time', 'value': 'all'}
                    ],
                    value='24h',
                    size='sm',
                    className='w-auto'
                ),
                width='auto',
                className='ms-auto'
            )
        ], className='mb-2 align-items-center'),
        html.Small(id='time-range-info', className='text-muted d-block mb-2'),
        dcc.Graph(id='graph-temp', style={'height': '360px'}),
        html.Div(
            dbc.Button('📥 Download CSV', id='download-btn',
                       color='secondary', size='sm',
                       className='mt-2'),
            className='text-end'
        ),
        html.Small(id='heartbeat', className='text-muted mt-2 d-block'),
        dcc.Interval(id='dash-refresh', interval=5000, n_intervals=0)
    ]),
    className='h-100 graph-card'
)

# --- Dashboard Layout ---
DashboardLayout = html.Div([
    MetricsRow,
    dbc.Row([
        dbc.Col(GaugeCard, width=4),
        dbc.Col(GraphCard, width=8)
    ], className='g-3 align-items-stretch')
])


# --- Callbacks ---
def register_dashboard_callbacks(app, finder, cfg):
    def filter_dataframe_by_time_range(df, time_range):
        """Filter dataframe based on selected time range."""
        if time_range == 'all' or df.empty:
            return df

        # Parse timestamps
        df['dt'] = pd.to_datetime(df['timestamp'])
        now = pd.Timestamp.now()

        # Calculate cutoff time based on range
        if time_range == '1h':
            cutoff = now - pd.Timedelta(hours=1)
        elif time_range == '6h':
            cutoff = now - pd.Timedelta(hours=6)
        elif time_range == '24h':
            cutoff = now - pd.Timedelta(hours=24)
        elif time_range == '7d':
            cutoff = now - pd.Timedelta(days=7)
        elif time_range == '30d':
            cutoff = now - pd.Timedelta(days=30)
        else:
            return df

        # Filter and return
        filtered = df[df['dt'] >= cutoff].copy()
        return filtered

    @app.callback(
        Output('temp-gauge', 'figure'),
        Output('graph-temp', 'figure'),
        Output('metric-probes', 'children'),
        Output('metric-lastupdate', 'children'),
        Output('metric-logging', 'children'),
        Output('heartbeat', 'children'),
        Output('time-range-info', 'children'),
        Input('dash-refresh', 'n_intervals'),
        Input('time-range-selector', 'value')
    )
    def update_dashboard(_, time_range):
        try:
            df = pd.read_csv(CSV_FILE)
            if df.empty:
                raise ValueError('No data')

            # Get latest reading for gauge (always use most recent)
            row = df.tail(1).iloc[0]
            t_c = float(row['temperature_c'])
            t_f = float(row['temperature_f'])
            ts = row['timestamp']

            # Gauge (always shows current temperature)
            gauge = go.Figure(go.Indicator(
                mode='gauge+number',
                value=t_c,
                number={'suffix': ' °C'},
                gauge={'axis': {'range': [0, 100]},
                       'bar': {'color': '#00bcd4'}},
                domain={'x': [0, 1], 'y': [0, 1]}
            ))
            gauge.update_layout(
                margin=dict(t=10, b=30, l=10, r=10),
                height=250,
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )

            # Filter data for graph based on time range
            df_filtered = filter_dataframe_by_time_range(df, time_range or '24h')

            # Create time range info message
            total_points = len(df)
            filtered_points = len(df_filtered)
            if time_range == 'all':
                range_info = f'Showing all {total_points:,} data points'
            else:
                range_labels = {
                    '1h': 'last hour',
                    '6h': 'last 6 hours',
                    '24h': 'last 24 hours',
                    '7d': 'last week',
                    '30d': 'last month'
                }
                range_info = f'Showing {filtered_points:,} of {total_points:,} data points ({range_labels.get(time_range, "selected range")})'

            # Graph with filtered data
            fig = go.Figure()
            if not df_filtered.empty:
                # Support multiple probes with different colors
                if 'probe_id' in df_filtered.columns:
                    probe_ids = df_filtered['probe_id'].unique()
                    colors = ['#00bcd4', '#ff6b6b', '#4ecdc4', '#45b7d1', '#f7b731', '#5f27cd']
                    for i, probe_id in enumerate(probe_ids):
                        probe_df = df_filtered[df_filtered['probe_id'] == probe_id]
                        if not probe_df.empty:
                            color = colors[i % len(colors)]
                            fig.add_trace(go.Scatter(
                                x=probe_df['timestamp'],
                                y=probe_df['temperature_c'],
                                mode='lines',
                                name=probe_id or 'Unknown',
                                line=dict(color=color, width=2)
                            ))
                else:
                    # No probe_id column, just plot all data
                    fig.add_trace(go.Scatter(
                        x=df_filtered['timestamp'],
                        y=df_filtered['temperature_c'],
                        mode='lines',
                        name='°C',
                        line=dict(color='#00bcd4', width=2)
                    ))

            fig.update_layout(
                margin=dict(t=20, b=20, l=0, r=10),
                template='plotly_dark',
                xaxis_title='Time',
                yaxis_title='Temp °C',
                hovermode='x unified',
                showlegend=True if 'probe_id' in df_filtered.columns and len(df_filtered['probe_id'].unique()) > 1 else False
            )

            # Metrics
            probes = len((finder.list_probes() or {}))
            logging_status = 'ON' if cfg.get('pull_enabled', True) else 'OFF'
            last_dt = datetime.datetime.fromisoformat(ts)
            delta = (datetime.datetime.now() - last_dt).total_seconds()
            hb = (f'Last sync {int(delta)} s ago'
                  if delta < 60 else
                  f'Last sync {int(delta//60)} min ago')
            if delta < 10:
                hb += ' ✓'

            return gauge, fig, probes, ts, logging_status, hb, range_info

        except Exception as e:
            empty = go.Figure()
            empty.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis={'visible': False},
                yaxis={'visible': False}
            )
            return empty, empty, '0', '(no data)', 'OFF', 'No signal', 'No data available'

    # --- CSV Download Button ---
    @app.callback(Output('download-btn', 'href'),
                  Input('dash-refresh', 'n_intervals'))
    def _csv_link(_):
        try:
            path = quote(str(CSV_FILE))
            return f'/download/{path}'
        except Exception:
            return None
