from dash import html, dcc, Output, Input, no_update
import dash_bootstrap_components as dbc
import datetime

DevicesLayout = html.Div([
    html.H4('Connected Probes'),
    dcc.Interval(id='device-refresh', interval=5000, n_intervals=0),
    html.Div(id='device-grid', className='row g-3')
])

def register_devices_callbacks(app, finder, cfg):
    @app.callback(Output('device-grid', 'children'), Input('device-refresh', 'n_intervals'))
    def update_devices(_):
        try:
            probes = (finder.list_probes() or {}).values()
            cards = []
            now = datetime.datetime.now()
            probe_names = cfg.get('probe_names', {})
            for p in probes:
                # Handle both dicts and object-style probes
                if isinstance(p, dict):
                    props = p.get('properties', {}) or {}
                    name = p.get('name') or props.get('name') or props.get('id') or p.get('id') or 'Unknown'
                    probe_id = props.get('id') or p.get('probe_id') or p.get('id')
                    ip = p.get('ip') or p.get('host') or 'N/A'
                    port = p.get('port', 80)
                    last = p.get('last_seen')
                else:
                    props = getattr(p, 'properties', {}) or {}
                    name = getattr(p, 'name', None) or getattr(p, 'id', None) or props.get('name') or props.get('id') or 'Unknown'
                    probe_id = props.get('id') or getattr(p, 'probe_id', None) or getattr(p, 'id', None)
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

                # Build display elements with friendly names
                friendly_name = probe_names.get(probe_id, None) if probe_id else None
                if friendly_name:
                    # Show friendly name as primary, with probe_id as secondary
                    title_elements = [html.H6(friendly_name, className='fw-bold mb-1')]
                    if probe_id != name:
                        title_elements.append(html.Small(f'{name} (ID: {probe_id})', className='text-info d-block mb-1'))
                    else:
                        title_elements.append(html.Small(f'ID: {probe_id}', className='text-info d-block mb-1'))
                else:
                    # No friendly name, use original logic
                    title_elements = [html.H6(name, className='fw-bold mb-1')]
                    # Show probe_id if it differs from name (fixes ID mismatch issue)
                    if probe_id and probe_id != name:
                        title_elements.append(html.Small(f'ID: {probe_id}', className='text-info d-block mb-1'))

                card = dbc.Col(dbc.Card(dbc.CardBody([
                    *title_elements,
                    html.Small(f'{ip}:{port}', className='text-muted'),
                    html.Div(html.Span(f'● {delta or "Unknown"}', className=f'status-dot text-{status_color} fw-bold mt-2'))
                ]), className='h-100 probe-card'), width=12, lg=4, md=6)
                cards.append(card)

            if not cards:
                return [dbc.Alert('No probes discovered yet.', color='secondary')]
            return cards
        except Exception as e:
            import traceback
            error_msg = f'Discovery service error: {str(e)}'
            print(f'[devices_panel] {error_msg}\n{traceback.format_exc()}')
            return [dbc.Alert(error_msg, color='danger')]
