import dash
from dash import dcc, html
import dash.dependencies as dd
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Initialize Dash app
app = dash.Dash(__name__)
server = app.server  # For deployment

# Function to fetch data based on symbol and expiration date
def fetch_data(ticker, expiration_date):
    stock = yf.Ticker(ticker)
    
    try:
        # Try to fetch the options data for the given expiration date
        calls = stock.option_chain(expiration_date).calls
        puts = stock.option_chain(expiration_date).puts
    except Exception as e:
        print(f"Error fetching options data: {e}")
        return None, None, None, None, None
    
    # Get top strikes by open interest and volume
    top_calls_oi = calls.nlargest(5, 'openInterest')[['strike', 'openInterest']]
    top_puts_oi = puts.nlargest(5, 'openInterest')[['strike', 'openInterest']]
    top_calls_vol = calls.nlargest(5, 'volume')[['strike', 'volume']]
    top_puts_vol = puts.nlargest(5, 'volume')[['strike', 'volume']]
    
    # Fetch historical data
    end_time = datetime.now().replace(second=0, microsecond=0)
    start_time = end_time - timedelta(days=2)
    data = stock.history(start=start_time, end=end_time, interval='5m')
    return data, top_calls_oi, top_puts_oi, top_calls_vol, top_puts_vol

# Layout
app.layout = html.Div(
    style={'backgroundColor': 'black', 'color': 'white', 'padding': '20px'},  # Keep the rest of the layout white text on black background
    children=[
        html.H1(id="title", style={'textAlign': 'center'}),
        dcc.Input(id="symbol-input", type="text", debounce=True, style={'textAlign': 'center', 'margin': '10px'}),
        html.Div("Please select ticker", style={'textAlign': 'left', 'fontSize': 8}),
        
        # New input field for expiration date
        dcc.Input(
            id='expiration-date-input',
            type='text',
            debounce=True,
            placeholder='YYYY-MM-DD',  # Placeholder text
            style={'textAlign': 'center', 'margin': '10px'}
        ),
        
        dcc.Interval(id='interval', interval=60000, n_intervals=0),
        dcc.Graph(id='options-graph')
    ]
)

@app.callback(
    [dd.Output('title', 'children'),
     dd.Output('options-graph', 'figure')],
    [dd.Input('interval', 'n_intervals'),
     dd.Input('symbol-input', 'value'),
     dd.Input('expiration-date-input', 'value')]  # Capture expiration date input
)
def update_graph(_, ticker, expiration_date):
    if not ticker:
        return "Please select ticker", go.Figure()  # Return an empty figure if no ticker is provided
    
    # If no expiration date is provided, set the default expiration date
    if not expiration_date:
        expiration_date = '2025-03-21'  # Default expiration date if not provided

    # Validate the expiration date format
    try:
        datetime.strptime(expiration_date, '%Y-%m-%d')  # Validate date format
    except ValueError:
        return "Invalid date format. Please use 'YYYY-MM-DD'", go.Figure()  # Return error message if invalid
    
    # Fetch data using the given expiration date
    data, top_calls_oi, top_puts_oi, top_calls_vol, top_puts_vol = fetch_data(ticker, expiration_date)
    
    if data is None:
        return f"Error fetching data for {ticker} with expiration {expiration_date}", go.Figure()

    # Update the title
    title = f"{ticker} Best Zones to Trade for {expiration_date}"
    
    # Create the figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='markers', name='Price', 
                             marker=dict(symbol='star', color='white', size=8)))

    for _, row in top_calls_oi.iterrows():
        fig.add_hline(y=row['strike'], line=dict(color='green'), annotation_text=f" {row['strike']}")
    for _, row in top_puts_oi.iterrows():
        fig.add_hline(y=row['strike'], line=dict(color='red'), annotation_text=f"{row['strike']}")
    for _, row in top_calls_vol.iterrows():
        fig.add_hline(y=row['strike'], line=dict(color='blue'), annotation_text=f"{row['strike']}")
    for _, row in top_puts_vol.iterrows():
        fig.add_hline(y=row['strike'], line=dict(color='purple'), annotation_text=f" {row['strike']}")
    
    # Set background color for the graph only
    fig.update_layout(
        title=f"{ticker} Analysis for {expiration_date}", 
        xaxis_title="Time", 
        yaxis_title="Price", 
        plot_bgcolor='black',  # Set graph background color
        paper_bgcolor='black',  # Set paper background color (outer region)
        font_color='white'  # Set text color to white
    )
    return title, fig

if __name__ == '__main__':
    app.run_server(debug=True, host='127.0.0.1', port=8050)
