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

# Function to fetch stock and options data
def fetch_data(ticker, expiration_date):
    stock = yf.Ticker(ticker)
    
    try:
        calls = stock.option_chain(expiration_date).calls
        puts = stock.option_chain(expiration_date).puts
    except Exception as e:
        print(f"Error fetching options data: {e}")
        return None, None, None, None, None
    
    top_calls_oi = calls.nlargest(5, 'openInterest')[['strike', 'openInterest']]
    top_puts_oi = puts.nlargest(5, 'openInterest')[['strike', 'openInterest']]
    top_calls_vol = calls.nlargest(5, 'volume')[['strike', 'volume']]
    top_puts_vol = puts.nlargest(5, 'volume')[['strike', 'volume']]
    
    end_time = datetime.now(pytz.timezone('US/Eastern')).replace(hour=16, minute=5, second=0, microsecond=0)
    start_time = end_time - timedelta(days=10)  
    data = stock.history(start=start_time, end=end_time, interval='5m')
    
    return data, top_calls_oi, top_puts_oi, top_calls_vol, top_puts_vol

# Layout
app.layout = html.Div(
    style={'backgroundColor': 'black', 'color': 'white', 'padding': '20px'},  
    children=[
        # Main title
        html.H1(id="title", style={'textAlign': 'center'}),

        # Title displaying close price and time
        html.Div(
            id="close-price-title", 
            children=[],  # This will be dynamically updated with the close price info
            style={'textAlign': 'center', 'fontSize': '10px', 'marginTop': '10px'}
        ),

        dcc.Input(id="symbol-input", type="text", debounce=True, placeholder="Enter ticker", 
                  style={'textAlign': 'left', 'margin': '10px'}),

        # Date picker for expiration date
        dcc.DatePickerSingle(
            id='expiration-date-picker',
            min_date_allowed=datetime.today(),
            max_date_allowed=datetime.today() + timedelta(days=365),
            date=datetime.today().strftime('%Y-%m-%d'),
            display_format='YYYY-MM-DD',
            style={'textAlign': 'center', 'margin': '8px'}
        ),

        # Buttons to scale Y-axis
        html.Div([
            html.Button("Scale Up", id="scale-up", n_clicks=0, style={'margin': '5px'}),
            html.Button("Scale Down", id="scale-down", n_clicks=0, style={'margin': '5px'}),
        ], style={'textAlign': 'center'}),

        dcc.Interval(id='interval', interval=60000, n_intervals=0),
        dcc.Graph(id='options-graph')
    ]
)

@app.callback(
    [dd.Output('title', 'children'),
     dd.Output('close-price-title', 'children'),
     dd.Output('options-graph', 'figure')],
    [dd.Input('interval', 'n_intervals'),
     dd.Input('symbol-input', 'value'),
     dd.Input('expiration-date-picker', 'date'),
     dd.Input('scale-up', 'n_clicks'),
     dd.Input('scale-down', 'n_clicks')]
)
def update_graph(_, ticker, expiration_date, scale_up_clicks, scale_down_clicks):
    if not ticker:
        return "Please select ticker", "", go.Figure()  
    
    if not expiration_date:
        expiration_date = datetime.today().strftime('%Y-%m-%d')

    try:
        datetime.strptime(expiration_date, '%Y-%m-%d')  
    except ValueError:
        return "Invalid date format. Please use 'YYYY-MM-DD'", "", go.Figure()  
    
    data, top_calls_oi, top_puts_oi, top_calls_vol, top_puts_vol = fetch_data(ticker, expiration_date)
    
    if data is None:
        return f"Error fetching data for {ticker} with expiration {expiration_date}", "", go.Figure()

    # Get the latest close price and timestamp
    latest_close = data['Close'].iloc[-1]
    close_time = data.index[-1].strftime('%Y-%m-%d %H:%M')

    # Title including latest close price
    title = f"Target Price Zones to Trade {ticker}"

    # Second title displaying latest close price and time
    close_price_title = f"Latest price of {ticker} at {close_time} was ${latest_close:.2f}"

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=data.index, y=data['Close'], mode='lines', name='Price', 
        line=dict(color='white', width=2)
    ))

    for _, row in top_calls_oi.iterrows():
        fig.add_hline(y=row['strike'], line=dict(color='green', width=1), annotation_text=f"{row['strike']}")
    for _, row in top_puts_oi.iterrows():
        fig.add_hline(y=row['strike'], line=dict(color='red', width=1), annotation_text=f"{row['strike']}")
    for _, row in top_calls_vol.iterrows():
        fig.add_hline(y=row['strike'], line=dict(color='blue', width=1), annotation_text=f"{row['strike']}")
    for _, row in top_puts_vol.iterrows():
        fig.add_hline(y=row['strike'], line=dict(color='yellow', width=1), annotation_text=f"{row['strike']}")

    # --- Y-Axis Scaling Logic ---
    y_min = data['Close'].min()
    y_max = data['Close'].max()
    scale_factor = 0.05  # Adjust how much it scales per click

    # Apply Y-axis scaling based on button clicks
    scale_change = (scale_up_clicks - scale_down_clicks) * scale_factor
    y_range = [(y_min - y_min * scale_change), (y_max + y_max * scale_change)]

    # Update layout
    fig.update_layout(
        xaxis=dict(
            title="Time", 
            rangeslider=dict(visible=True),
            type="date",
            showspikes=True, spikecolor="grey", spikemode="across",
            fixedrange=False  # Allow zooming on X axis
        ),
        yaxis=dict(
            title="Price",
            range=y_range,  # Adjusted Y-axis range
            showspikes=True, spikecolor="grey", spikemode="across",
            fixedrange=False  # Allow zooming on Y axis as well
        ),
        dragmode="pan",  # Pan mode to move around the chart
        plot_bgcolor='black',
        paper_bgcolor='black',
        font=dict(color='white'),
        margin=dict(l=40, r=40, t=40, b=40),
        hovermode="closest",
        updatemenus=[{
            "buttons": [
                {"args": ["xaxis.range", [data.index.min(), data.index.max()]], "label": "Reset Zoom", "method": "relayout"},
                {"args": ["xaxis.range", [data.index.max() - timedelta(days=1), data.index.max()]], "label": "1D", "method": "relayout"},
                {"args": ["xaxis.range", [data.index.max() - timedelta(days=7), data.index.max()]], "label": "1W", "method": "relayout"},
                {"args": ["xaxis.range", [data.index.max() - timedelta(days=30), data.index.max()]], "label": "1M", "method": "relayout"},
            ],
            "direction": "down",
            "showactive": True,
        }]
    )

    return title, close_price_title, fig


if __name__ == '__main__':
    app.run_server(debug=True, host='127.0.0.1', port=8050)
