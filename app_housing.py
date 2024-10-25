import os

from dash import Dash, html, dash_table, dcc
#import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px

fname = "calafornia_housing.csv"
fpath = os.path.join(os.path.expanduser('~'), 'Downloads', fname)
df = pd.read_csv(fpath, skipinitialspace=True, encoding='utf-8')

# Identify float columns and round them to 2 decimal places
float_cols = df.select_dtypes(include=['float', 'float64']).columns
df[float_cols] = df[float_cols].round(2)

app = Dash(__name__)

app.layout = [
    html.Div(f"{fname} data"),
    dash_table.DataTable(data=df.to_dict('records'), page_size=10),
    dcc.Graph(
        figure=px.density_mapbox(
            df,
            lat='Latitude',
            lon='Longitude',
            z='Population',
            radius=10,
            center=dict(lat=df['Latitude'].mean(), lon=df['Longitude'].mean()),
            zoom=4,
            mapbox_style="carto-darkmatter",  # Dark map style
            title="Population Density Map"
        ).update_layout(
            template='plotly_dark',          # Apply Plotly dark template
            title={'x':0.5}                  # Center the title
        )
    )
]

if __name__ == "__main__":
    app.run_server(debug=True)