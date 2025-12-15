from dash import html, dcc, Output, Input, no_update
import dash_bootstrap_components as dbc
import datetime

DevicesLayout = html.Div([
    html.H4('Connected Probes'),
    dcc.Interval(id='device-refresh', interval=5000, n_intervals=0),
    html.Div(id='device-grid', className='row g-3')
])

def register_devices_callbacks(app, finder):
    @app.callback(Output('device-grid', 'children'), Input('device-refresh', 'n_intervals'))
    def update_devices(_):
        try:
            probes = (finder.list_probes() or {}).values()
            cards = []
            now = datetime.datetime.now()
            for p in probes:
                # Handle both dicts and object-style probes
                if isinstance(p, dict):
                    props = p.get('properties', {}) or {}
                    name = p.get('name') or props.get('name') or props.get('id') or p.get('id') or 'Unknown'
                    ip = p.get('ip') or p.get('host') or 'N/A'
                    port = p.get('port', 80)
                    last = p.get('last_seen')
                else:
                    props = getattr(p, 'properties', {}) or {}
                    name = getattr(p, 'name', None) or getattr(p, 'id', None) or props.get('name') or props.get('id') or 'Unknown'
                    ip = getattr(p, 'ip', None) or getattr(p, 'host', None) or 'N/A'
                    port = getattr(p, 'port', 80)
                    last = getattr(p, 'last_seen', None)

                delta = ''
                status_color = 'secondary'
                if last:
                    try:
                        if isinstance(last, (int, float)):
                            dt = datetime.datetime.fromtimestamp(last)
                        else:
                            dt = datetime.datetime.fromisoformat(str(last))
                        seconds = (now - dt).total_seconds()
                        if seconds < 15:
                            status_color = 'success'
                            delta = 'Just now'
                        elif seconds < 60:
                            status_color = 'warning'
                            delta = f'{int(seconds)} s ago'
                        else:
                            status_color = 'danger'
                            delta = f'{int(seconds // 60)} min ago'
                    except Exception:
                        pass

                card = dbc.Col(dbc.Card(dbc.CardBody([
                    html.H6(name, className='fw-bold mb-1'),
                    html.Small(f'{ip}:{port}', className='text-muted'),
                    html.Div(html.Span(f'● {delta or "Unknown"}', className=f'status-dot text-{status_color} fw-bold mt-2'))
                ]), className='h-100 probe-card'), width=12, lg=4, md=6)
                cards.append(card)

            if not cards:
                return [dbc.Alert('No probes discovered yet.', color='secondary')]
            return cards
        except Exception:
            return [dbc.Alert('Discovery service unavailable.', color='danger')]
