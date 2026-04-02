import pandas as pd
import datetime as dt
import dash
import os
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_auth
#import plotly as go
import plotly.graph_objects as go

import tab1
import tab2
import tab3

class db:
    def __init__(self):
        self.transactions = self.transaction_init()
        self.cc = pd.read_csv(r'db\country_codes.csv', index_col=0)
        self.customers = pd.read_csv(r'db\customers.csv', index_col=0)
        self.prod_info = pd.read_csv(r'db\prod_cat_info.csv')

    @staticmethod
    def transaction_init():
        src = r'db\transactions'
        dfs = []
        for filename in os.listdir(src):
            df = pd.read_csv(os.path.join(src, filename), index_col=0)
            dfs.append(df)
        transactions = pd.concat(dfs, ignore_index=True)

        def convert_dates(x):
            try:
                return dt.datetime.strptime(x, '%d-%m-%Y')
            except:
                return dt.datetime.strptime(x, '%d/%m/%Y')

        transactions['tran_date'] = transactions['tran_date'].apply(convert_dates)
        return transactions

    def merge(self):
        df = self.transactions.join(
            self.prod_info.drop_duplicates(subset=['prod_cat_code'])
            .set_index('prod_cat_code')['prod_cat'],
            on='prod_cat_code', how='left')
        df = df.join(
            self.prod_info.drop_duplicates(subset=['prod_sub_cat_code'])
            .set_index('prod_sub_cat_code')['prod_subcat'],
            on='prod_subcat_code', how='left')
        df = df.join(
            self.customers.join(self.cc, on='country_code')
            .set_index('customer_Id'),
            on='cust_id')
        self.merged = df

df = db()
df.merge()
print(df.merged.head())


#inicjalizacja aplikacji, wykorzystując dodatkowo zewnętrzny arkusz stylów.
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.config.suppress_callback_exceptions = True

# autoryzacja
#USERNAME_PASSWORD = [['user','pass']]
#auth = dash_auth.BasicAuth(app,USERNAME_PASSWORD)

#Layout
# widget do wyboru zakladek
#Wewnatrz umiescimy kolejny div, ktory zawieral bedzie juz docelowy widget. Ustalmy jego szerokosc na 80% 
#oraz parametr margin na 'auto'.

# zakladki

app.layout = html.Div([
    html.Div([
        dcc.Tabs(id='tabs', value='tab-1', children=[
            dcc.Tab(label='Sprzedaż globalna', value='tab-1'),
            dcc.Tab(label='Produkty', value='tab-2'),
            dcc.Tab(label='Kanały sprzedaży', value='tab-3')
        ]),
        html.Div(id='tabs-content')
    ], style={'width':'80%','margin':'auto'})
], style={'height':'100%'})



# Callbacks

#renderowanie zawartości aktywnej zakładki.

@app.callback(Output('tabs-content','children'), [Input('tabs','value')])
def render_content(tab):
    if tab == 'tab-1':
        return tab1.render_tab(df.merged)
    elif tab == 'tab-2':
        return tab2.render_tab(df.merged)
    elif tab == 'tab-3':
        return tab3.render_tab(df.merged) # dodanie 3 zakladki
    
# tab1 callbacks
@app.callback(Output('bar-sales','figure'),[Input('sales-range','start_date'),Input('sales-range','end_date')])
def tab1_bar_sales(start_date,end_date):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    truncated = df.merged[(df.merged['tran_date']>=start_date)&(df.merged['tran_date']<=end_date)]
    grouped = truncated[truncated['total_amt']>0].groupby([pd.Grouper(key='tran_date',freq='M'),'Store_type'])['total_amt'].sum().round(2).unstack()
    traces = []
    for col in grouped.columns:
        traces.append(go.Bar(x=grouped.index,y=grouped[col],name=col,hoverinfo='text',
        hovertext=[f'{y/1e3:.2f}k' for y in grouped[col].values]))
    data = traces
    fig = go.Figure(data=data,layout=go.Layout(title='Przychody',barmode='stack',legend=dict(x=0,y=-0.5)))
    return fig

#Tworzymy funkcję tab1_bar_sales, a następnie w oparciu o daty wybrane przez użytkownika zawężamy 
#DataFrame z transakcjami i generujemy wykres

# kartogram
@app.callback(Output('choropleth-sales','figure'),
            [Input('sales-range','start_date'),Input('sales-range','end_date')])
def tab1_choropleth_sales(start_date,end_date):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    truncated = df.merged[(df.merged['tran_date']>=start_date)&(df.merged['tran_date']<=end_date)]
    grouped = truncated[truncated['total_amt']>0].groupby('country')['total_amt'].sum().round(2)
    trace0 = go.Choropleth(colorscale='Viridis',reversescale=True,
                            locations=grouped.index,locationmode='country names',
                            z = grouped.values, colorbar=dict(title='Sales'))
    data = [trace0]
    fig = go.Figure(data=data,layout=go.Layout(title='Mapa',geo=dict(showframe=False,projection={'type':'natural earth'})))
    return fig

# poziomy wykres slupkowy
# jako input posłuży nam wybrana wartość z widgetu Dropdown, którą możemy znaleźć w obiekcie o id 'prod_dropdown'.
#Po wykonaniu odpowiednich przekształceń na połączonym DataFrame tworzymy wykres słupkowy i zwracamy go do obiektu
#o id 'barh-prod-subcat'.

## tab2 callbacks
@app.callback(Output('barh-prod-subcat','figure'),
            [Input('prod_dropdown','value')])
def tab2_barh_prod_subcat(chosen_cat):
    grouped = df.merged[(df.merged['total_amt']>0)&(df.merged['prod_cat']==chosen_cat)].pivot_table(index='prod_subcat',columns='Gender',values='total_amt',aggfunc='sum').assign(_sum=lambda x: x['F']+x['M']).sort_values(by='_sum').round(2)
    traces = []
    for col in ['F','M']:
        traces.append(go.Bar(x=grouped[col],y=grouped.index,orientation='h',name=col))
    data = traces
    fig = go.Figure(data=data,layout=go.Layout(barmode='stack',margin={'t':20,}))
    return fig

#tab3
@app.callback(Output('bar-demographics-store', 'figure'), [Input('demographics-dropdown', 'value')])
def tab3_demographics(chosen_demo):
    # unikalni klienci dla kazdego kanalu i wybranej cechy (kraj lub plec)
    grouped = df.merged.groupby(['Store_type', chosen_demo])['cust_id'].nunique().unstack()
    traces = []
    for col in grouped.columns:
        traces.append(go.Bar(x=grouped.index, y=grouped[col], name=str(col)))    
    # skumulowany wykres słupkowy 
    fig = go.Figure(
        data=traces, 
        layout=go.Layout(
            title=f'Liczba unikalnych klientów wg {chosen_demo}', 
            barmode='stack'))
    return fig



#Na końcu uruchamiamy serwer w trybie developerskim, który ułatwi nam wyłapanie powstałych błędów.
if __name__ == '__main__':
    app.run(debug=True, port=8051)