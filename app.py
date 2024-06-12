import dash
from dash import dcc, html
from dash.dependencies import Input, Output

# Importowanie skryptów
import GetAllSymbols
#import GetChartLastRequest
#import Obliczenia_SMA
#import select_instrument

app = dash.Dash(__name__)

# Layout aplikacji
app.layout = html.Div([
    html.Div([
        html.Button('Uruchom GetAllSymbols', id='btn-GetAllSymbols', n_clicks=0, className='button'),
        # html.Button('Uruchom GetChartLastRequest', id='btn-GetChartLastRequest', n_clicks=0, className='button'),
        # html.Button('Uruchom Obliczenia_SMA', id='btn-Obliczenia_SMA', n_clicks=0, className='button'),
        # html.Button('Uruchom select_instrument', id='btn-select_instrument', n_clicks=0, className='button')
    ], className='button-container'),
    html.Div(id='output-container')
])

# Callbacki do uruchamiania skryptów
@app.callback(
    Output('output-container', 'children'),
    [Input('btn-GetAllSymbols', 'n_clicks')]
)
def run_script(nGetAllSymbols):
    ctx = dash.callback_context
    if not ctx.triggered:
        button_id = 'None'
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'btn-GetAllSymbols':
        result = GetAllSymbols.main()
    # elif button_id == 'btn-GetChartLastRequest':
    #     result = GetChartLastRequest.main()
    # elif button_id == 'btn-Obliczenia_SMA':
    #     result = Obliczenia_SMA.main()
    # elif button_id == 'btn-select_instrument':
    #     result = select_instrument.main()
    else:
        result = 'Naciśnij przycisk, aby uruchomić skrypt'

    return f'Wynik: {result}'

if __name__ == '__main__':
    app.run_server(debug=True)
