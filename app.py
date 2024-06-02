import dash
from dash import dcc, html, Input, Output
import pandas as pd
import os

app = dash.Dash(__name__)

# Layout aplikacji
app.layout = html.Div([
    dcc.Interval(id='interval-component', interval=5*60*1000, n_intervals=0),  # Odświeżanie co 5 minut
    dcc.Dropdown(id='instrument-dropdown', options=[], value=None),
    html.Div(id='alerts'),
    html.Div(id='instrument-info')
])

@app.callback(
    Output('instrument-dropdown', 'options'),
    Input('interval-component', 'n_intervals')
)
def update_dropdown(n_intervals):
    files = os.listdir('processed')
    latest_file = max(files, key=lambda x: os.path.getctime(os.path.join('processed', x)))
    df = pd.read_csv(os.path.join('processed', latest_file))
    
    options = [{'label': i, 'value': i} for i in df['INSTRUMENT'].unique()]
    return options

@app.callback(
    Output('alerts', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_alerts(n_intervals):
    files = os.listdir('processed')
    latest_file = max(files, key=lambda x: os.path.getctime(os.path.join('processed', x)))
    df = pd.read_csv(os.path.join('processed', latest_file))
    
    alerts = df[df['mean'] > 10]  # Przykładowy alert, gdy średnia > 10
    alert_components = [html.Div(f"Alert: {row['INSTRUMENT']} - {row['mean']}") for index, row in alerts.iterrows()]
    return alert_components

@app.callback(
    Output('instrument-info', 'children'),
    Input('instrument-dropdown', 'value')
)
def display_instrument_info(instrument):
    if not instrument:
        return "Select an instrument to see details."
    
    # Pobieranie dodatkowych informacji z API
    url = f'https://api.example.com/instruments/{instrument}'
    response = requests.get(url)
    data = response.json()
    
    info_components = [
        html.Div(f"Name: {data['name']}"),
        html.Div(f"Description: {data['description']}"),
        # Dodaj inne informacje
    ]
    
    return info_components

if __name__ == '__main__':
    app.run_server(debug=True)
