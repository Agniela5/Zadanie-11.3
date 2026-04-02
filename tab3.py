import dash
from dash import dcc, html
import plotly.graph_objects as go
import pandas as pd

def render_tab(df):
    dff = df.copy()
    
    # Mapowanie dni tygodnia
    dff['day_of_week'] = dff['tran_date'].dt.day_name()
    day_map = {
        'Monday': 'Poniedziałek', 'Tuesday': 'Wtorek', 'Wednesday': 'Środa',
        'Thursday': 'Czwartek', 'Friday': 'Piątek', 'Saturday': 'Sobota', 'Sunday': 'Niedziela'}
    
    dff['day_of_week'] = dff['day_of_week'].map(day_map)
    days_order = ['Poniedziałek', 'Wtorek', 'Środa', 'Czwartek', 'Piątek', 'Sobota', 'Niedziela']
    
    # Grupowanie - używamy dff, gdzie są polskie nazwy
    grouped_dow = dff[dff['total_amt'] > 0].groupby(['day_of_week', 'Store_type'])['total_amt'].sum().unstack().reindex(days_order).fillna(0)

    fig_dow = go.Figure()
    for col in grouped_dow.columns:
        fig_dow.add_trace(go.Bar(x=grouped_dow.index, y=grouped_dow[col], name=col))

    fig_dow.update_layout(title='Kiedy sprzedajemy najwięcej? (Dni tygodnia)', barmode='group')

    layout = html.Div([
        html.H1('Analiza Kanałów Sprzedaży', style={'textAlign': 'center'}),
        
        html.Div([
            dcc.Graph(id='bar-dow-store', figure=fig_dow)
        ], style={'width': '100%'}),

        html.Div([
            html.H3('Kim są klienci w danym kanale?', style={'textAlign': 'center'}),
            dcc.Dropdown(
                id='demographics-dropdown',
                options=[
                    {'label': 'Płeć klientów', 'value': 'Gender'},
                    {'label': 'Kraj pochodzenia', 'value': 'country'}],
                value='Gender',
                style={'width': '50%', 'margin': 'auto'}),
            dcc.Graph(id='bar-demographics-store')
        ], style={'marginTop': '50px'})
    ])
    return layout