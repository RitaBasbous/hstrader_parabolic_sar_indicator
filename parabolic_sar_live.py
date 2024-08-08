from hstrader import HsTrader
from hstrader.models import Tick, Event, Resolution
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta
import os
from dotenv import load_dotenv
import logging
import asyncio
import threading
from psar import PSAR
psar=PSAR()
# Enable logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Get the CLIENT_ID and CLIENT_SECRET from the environment variables
id = os.getenv('CLIENT_ID')
secret = os.getenv('CLIENT_SECRET')

# Initialize the HsTrader client with the client ID and secret
client = HsTrader(id, secret)

symbol = client.get_symbol('EURUSD')
data = client.get_market_history(symbol=symbol.id, resolution=Resolution.M1)

# Create a DataFrame from the retrieved data
df = pd.DataFrame([bar.model_dump() for bar in data])
df['time'] = pd.to_datetime(df['time'])
df.set_index('time', inplace=True)

# Update the DataFrame with PSAR trend values
df['psar'] = df.apply(lambda x: psar.calc_psar(x['high'], x['low']), axis=1)
df['Trend'] = psar.trend_list[:len(df)]

psar_bull = df.loc[df['Trend'] == 1]['psar']
psar_bear = df.loc[df['Trend'] == 0]['psar']
fig = go.FigureWidget()
candlestick = go.Candlestick(x=[df.index], open=[df['open']], high=[df['high']], low=[df['low']], close=[df['close']], name='Candlestick')
fig.add_trace(candlestick)
# Add PSAR bull scatter
fig.add_trace(go.Scatter(x=psar_bull.index, y=psar_bull, mode='markers',
                         name='Up Trend', marker=dict(color='green', size=2)))

# Add PSAR bear scatter
fig.add_trace(go.Scatter(x=psar_bear.index, y=psar_bear, mode='markers',
                         name='Down Trend', marker=dict(color='red', size=2)))
app = Dash(__name__)
app.layout = html.Div([dcc.Graph(id='live-update-graph', figure=fig),
                       dcc.Interval(id='Interval', interval=1 * 1000, n_intervals=0)])
CANDLE_INTERVAL = timedelta(minutes=1)
data = {
    'x': list(df.index),
    'open': list(df['open']),
    'high': list(df['high']),
    'low': list(df['low']),
    'close': list(df['close'])
}


@client.subscribe(Event.MARKET)
async def on_market(tick: Tick):
    global data, df

    if tick.symbol_id == symbol.id:
        tick_time = pd.to_datetime(tick.time)
        if not data['x']:
            data['x'].append(tick_time)
            data['open'].append(data['close'][-1])
            data['high'].append(tick.bid)
            data['low'].append(tick.bid)
            data['close'].append(tick.bid)
        elif tick_time >= data['x'][-1] + CANDLE_INTERVAL:
            data['x'].append(tick_time)
            data['open'].append(data['close'][-1])
            data['high'].append(tick.bid)
            data['low'].append(tick.bid)
            data['close'].append(tick.bid)
        else:
            data['low'][-1] = min(tick.bid, data['low'][-1])
            data['high'][-1] = max(tick.bid, data['high'][-1])
            data['close'][-1] = tick.bid

        df = pd.DataFrame({
            'time': data['x'],
            'open': data['open'],
            'high': data['high'],
            'low': data['low'],
            'close': data['close']
        }).set_index('time')

        # Calculate PSAR and trend list
        psar_values = []
        trend_values = []
        for i, row in df.iterrows():
            x = psar.calc_psar(row['high'], row['low'])
            psar_values.append(x)
            trend_values.append(psar.trend)  # Use the last trend value

        df['psar'] = psar_values
        df['Trend'] = trend_values

        

@app.callback(Output('live-update-graph', 'figure'), Input('Interval', 'n_intervals'))
def update_graph_live(n):
    psar_bull = df.loc[df['Trend'] == 1]['psar']
    psar_bear = df.loc[df['Trend'] == 0]['psar']
    with fig.batch_update():
        fig.data[0].x = data['x']
        fig.data[0].open = data['open']
        fig.data[0].high = data['high']
        fig.data[0].low = data['low']
        fig.data[0].close = data['close']
        fig.data[1].x = psar_bull.index
        fig.data[1].y = psar_bull
        fig.data[2].x = psar_bear.index
        fig.data[2].y = psar_bear

    return fig


def run_dash():
    app.run_server(debug=False, use_reloader=False)




if __name__ == '__main__':
    dash_thead = threading.Thread(target=run_dash)
    dash_thead.start()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.start_async())
