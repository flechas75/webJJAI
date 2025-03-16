import dash
from dash import dcc, html
import dash.dependencies as dd
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz

# Initialize Dash app
app = dash.Dash(__name__)
server = app.server  # For deployment

# Define the ticker symbol
ticker = "QQQ"

def fetch_data():
    stock = yf.Ticker(ticker)
    expiration_date = '2025-03-21'
    calls = stock.option_chain(expiration_date).calls
    puts = stock.option_chain(expiration_date).puts
    
    # Get top strikes by open interest and volume
    top_calls_oi = calls.nlargest(5, 'openInterest')[['strike', 'openInterest']]
    top_puts_oi = puts.nlargest(5, 'openInterest')[['strike', 'openInterest']]
    top_calls_vol = calls.nlargest(5, 'volume')[['strike', 'volume']]
    top_puts_vol = puts.nlargest(5, 'volume')[['strike', 'volume']]
    
    # Fetch historical data
    end_time = datetime.now().replace(second=0, microsecond=0)
    start_time = end_time - timedelta(days=2)
    data = stock.history(start=start_time, end=end_time, interval='1h')
    return data, top_calls_oi, top_puts_oi, top_calls_vol, top_puts_vol

# Layout
app.layout = html.Div([
    html.H1("QQQ Options & Historical Data", style={'textAlign': 'center'}),
    dcc.Interval(id='interval', interval=60000, n_intervals=0),
    dcc.Graph(id='options-graph')
])

@app.callback(
    dd.Output('options-graph', 'figure'),
    [dd.Input('interval', 'n_intervals')]
)
def update_graph(_):
    data, top_calls_oi, top_puts_oi, top_calls_vol, top_puts_vol = fetch_data()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='Price'))
    
    for _, row in top_calls_oi.iterrows():
        fig.add_hline(y=row['strike'], line=dict(color='green'), annotation_text=f"Call OI {row['strike']}")
    for _, row in top_puts_oi.iterrows():
        fig.add_hline(y=row['strike'], line=dict(color='red'), annotation_text=f"Put OI {row['strike']}")
    for _, row in top_calls_vol.iterrows():
        fig.add_hline(y=row['strike'], line=dict(color='blue'), annotation_text=f"Call Vol {row['strike']}")
    for _, row in top_puts_vol.iterrows():
        fig.add_hline(y=row['strike'], line=dict(color='purple'), annotation_text=f"Put Vol {row['strike']}")
    
    fig.update_layout(title=f"QQQ Options Analysis", xaxis_title="Time", yaxis_title="Price")
    return fig

if __name__ == '__main__':
    app.run_server(debug=True, host='127.0.0.1', port=8050)

