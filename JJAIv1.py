import dash
from dash import dcc, html
import dash.dependencies as dd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz

# Initialize Dash app
app = dash.Dash(__name__)
server = app.server  # For deployment

# Function to fetch stock and options data
def fetch_data(ticker, expiration_date, start_time, end_time):
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
    
    data = stock.history(start=start_time, end=end_time, interval='5m')
    
    return data, top_calls_oi, top_puts_oi, top_calls_vol, top_puts_vol

# Function to fetch historical data for additional charts
def fetch_chart_data(ticker, interval='1h'):
    stock = yf.Ticker(ticker)
    end_time = datetime.now(pytz.timezone('US/Eastern'))
    start_time = end_time - timedelta(days=1)
    data = stock.history(start=start_time, end=end_time, interval=interval)
    return data

# Function to create small charts
def create_chart(ticker):
    data = fetch_chart_data(ticker)
    fig = go.Figure()
    if not data.empty:
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name=ticker
        ))
    fig.update_layout(
        title=ticker,
        xaxis_title='',
        yaxis_title='',
        plot_bgcolor='black',
        paper_bgcolor='black',
        font=dict(color='white', size=6),
        xaxis=dict(showgrid=True, showticklabels=True, tickformat='%H:%M', dtick=7200000),
        yaxis=dict(showgrid=True, showticklabels=True),
        margin=dict(l=1, r=5, t=20, b=0)
    )
    return fig

# Layout
app.layout = html.Div(
    style={'backgroundColor': 'black', 'color': 'white', 'padding': '20px', 'display': 'flex', 'flexDirection': 'column'},
    children=[
        # Title at the top (Centered)
        html.H1('Best Trading Zones', 
                style={'textAlign': 'center', 'color': 'white', 'marginBottom': '20px'}),

        # Sidebar for filtering options on the left side
        html.Div(
            style={
                'width': '200px', 
                'backgroundColor': 'black', 
                'padding': '10px', 
                'display': 'flex', 
                'flexDirection': 'column',
                'alignItems': 'center',
                'borderRight': '2px solid white',
                'height': '100vh'
            },
            children=[
                html.H3('Filter Options', style={'color': 'white'}),
                html.Button("1D", id="filter-1d", n_clicks=0, style={'margin': '5px', 'backgroundColor': 'gray', 'color': 'white'}),
                html.Button("1W", id="filter-1w", n_clicks=0, style={'margin': '5px', 'backgroundColor': 'gray', 'color': 'white'}),
                html.Button("1M", id="filter-1m", n_clicks=0, style={'margin': '5px', 'backgroundColor': 'gray', 'color': 'white'}),
                html.Button("Scale Up", id="scale-up", n_clicks=0, style={'margin': '5px', 'backgroundColor': 'gray', 'color': 'white'}),
                html.Button("Scale Down", id="scale-down", n_clicks=0, style={'margin': '5px', 'backgroundColor': 'gray', 'color': 'white'}),
                dcc.Input(id="symbol-input", type="text", debounce=True, placeholder="Enter ticker", style={'margin': '10px', 'color': 'black'}),
                dcc.DatePickerSingle(
                    id='expiration-date-picker',
                    min_date_allowed=datetime.today(),
                    max_date_allowed=datetime.today() + timedelta(days=365),
                    date=datetime.today().strftime('%Y-%m-%d'),
                    display_format='YYYY-MM-DD',
                    style={'margin': '8px'}
                ),
            ]
        ),
        
        # Main content for charts (top small charts and main chart area)
        html.Div(
            style={'flex': 1, 'marginLeft': '10px'}, 
            children=[
                # Small Charts at the top
                html.Div(
                    children=[
                        dcc.Graph(
                            id='chart-NQ',
                            figure=create_chart('NQ=F'),
                            style={'width': '24%', 'display': 'inline-block', 'height': '220px', 'border': '1px solid white', 'padding': '0px'}
                        ),
                        dcc.Graph(
                            id='chart-ES',
                            figure=create_chart('ES=F'),
                            style={'width': '24%', 'display': 'inline-block', 'height': '220px', 'border': '1px solid white', 'padding': '0px'}
                        ),
                        dcc.Graph(
                            id='chart-RY',
                            figure=create_chart('RY=F'),
                            style={'width': '24%', 'display': 'inline-block', 'height': '220px', 'border': '1px solid white', 'padding': '0px'}
                        ),
                        dcc.Graph(
                            id='chart-YM',
                            figure=create_chart('YM=F'),
                            style={'width': '24%', 'display': 'inline-block', 'height': '220px', 'border': '1px solid white', 'padding': '0px'}
                        )
                    ],
                    style={'textAlign': 'center', 'marginBottom': '10px', 'display': 'flex', 'justifyContent': 'center'}
                ),

                # Main chart below the small charts
                dcc.Graph(id='options-graph')
            ]
        )
    ]
)

# Callback for scaling charts and filtering data
@app.callback(
    [dd.Output('options-graph', 'figure'),
     dd.Output('chart-NQ', 'style'),
     dd.Output('chart-ES', 'style'),
     dd.Output('chart-RY', 'style'),
     dd.Output('chart-YM', 'style')],
    [dd.Input('symbol-input', 'value'),
     dd.Input('expiration-date-picker', 'date'),
     dd.Input('filter-1d', 'n_clicks'),
     dd.Input('filter-1w', 'n_clicks'),
     dd.Input('filter-1m', 'n_clicks'),
     dd.Input('scale-up', 'n_clicks'),
     dd.Input('scale-down', 'n_clicks')]
)
def update_charts(ticker, expiration_date, filter_1d, filter_1w, filter_1m, scale_up, scale_down):
    ctx = dash.callback_context

    if not ticker:
        return go.Figure(), [{'height': '220px'}]* 4

    # Handle time filtering based on button clicks
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == 'filter-1d':
            start_time = datetime.now(pytz.timezone('US/Eastern')) - timedelta(days=1)
            end_time = datetime.now(pytz.timezone('US/Eastern'))
        elif button_id == 'filter-1w':
            start_time = datetime.now(pytz.timezone('US/Eastern')) - timedelta(weeks=1)
            end_time = datetime.now(pytz.timezone('US/Eastern'))
        elif button_id == 'filter-1m':
            start_time = datetime.now(pytz.timezone('US/Eastern')) - timedelta(weeks=4)
            end_time = datetime.now(pytz.timezone('US/Eastern'))
        else:
            start_time = datetime.now(pytz.timezone('US/Eastern')) - timedelta(days=1)
            end_time = datetime.now(pytz.timezone('US/Eastern'))
    
    # Fetch main chart data
    data, top_calls_oi, top_puts_oi, top_calls_vol, top_puts_vol = fetch_data(ticker, expiration_date, start_time, end_time)
    if data is None or data.empty:
        return go.Figure(), {'height': '220px'} * 4

    # Create the main chart figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='Price', line=dict(color='white', width=2)))
    
    for strike in top_calls_oi['strike']:
        fig.add_hline(y=strike, line=dict(color='green', width=1), annotation_text=f" {strike}")
    for strike in top_puts_oi['strike']:
        fig.add_hline(y=strike, line=dict(color='red', width=1), annotation_text=f"{strike}")
    
    fig.update_layout(
        title=ticker,
        xaxis_title='Time',
        yaxis_title='Price',
        plot_bgcolor='black',
        paper_bgcolor='black',
        font=dict(color='white'),
        xaxis_rangeslider_visible=False
    )

    # Scaling logic for small charts
    new_style = {'width': '24%', 'display': 'inline-block', 'height': '250px', 'border': '1px solid white'}
    
    if scale_up:
        new_style['height'] = '300px'
    
    if scale_down:
        new_style['height'] = '180px'
    
    return fig, [new_style]*4

if __name__ == '__main__':
    app.run_server(debug=True)
