import requests
import pandas as pd
from datetime import date, timedelta

import dash
from dash import Dash, html, dcc, Output, Input, State, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
from pyproj import Transformer
import dash_leaflet as dl

from dash_table.Format import Format, Scheme

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Initial position and radius
initial_lat = 52.45
initial_lon = -2.15
initial_radius = 20  # in km

app.layout = dbc.Container([
    html.H1("Rainfall Data Explorer", className="text-center"),

    # Row containing button and summary
    dbc.Row([
        dbc.Col([
            dbc.Button(
                "Show/Hide Selection Controls",
                id="toggle-button",
                color="dark",
                n_clicks=0,
                className="me-2"
            ),
            html.Div(
                id="selection-summary",
                className="d-inline-block align-middle",
                style={
                    "padding": "6px 12px",
                    "border": "1px solid #ccc",
                    "border-radius": "4px",
                    "background-color": "#f8f9fa"
                }
            )
        ], width=12)
    ], className="mb-3"),

    dbc.Collapse(
        id="collapse",
        is_open=True,
        children=[
            dbc.Row([
                dbc.Col([
                    html.H4("Select Location"),
                    dbc.Label("Latitude:"),
                    dbc.Input(id="latitude-input", type="number", value=initial_lat, step=0.0001),
                    html.Br(),
                    dbc.Label("Longitude:"),
                    dbc.Input(id="longitude-input", type="number", value=initial_lon, step=0.0001),
                    html.Br(),
                    dl.Map(center=[initial_lat, initial_lon], zoom=8, children=[
                        dl.TileLayer(),
                        dl.Circle(
                            center=[initial_lat, initial_lon],
                            radius=initial_radius * 1000,  # Convert km to meters
                            id='location-circle',
                            color='blue',
                            fillColor='blue',
                            fillOpacity=0.2,
                        ),
                    ], style={'width': '100%', 'height': '50vh'}, id="map"),
                ], width=6),

                dbc.Col([
                    html.H4("Parameters"),
                    dbc.Label("Radius (km):"),
                    dbc.Input(id="radius-input", type="number", value=initial_radius, min=1, max=200, step=1),
                    html.Br(),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Start Date:"),
                            dcc.DatePickerSingle(
                                id="start-date-picker",
                                date=(date.today() - timedelta(days=0)),
                                display_format='DD/MM/YYYY'
                            ),
                        ], width=6),
                        dbc.Col([
                            dbc.Label("End Date:"),
                            dcc.DatePickerSingle(
                                id="end-date-picker",
                                date=date.today(),
                                display_format='DD/MM/YYYY'
                            ),
                        ], width=6),
                    ]),
                    dbc.Button(
                        "Fetch Data",
                        id="fetch-data-button",
                        color="success",
                        className="mt-3"
                    ),
                    html.Div(id="message", style={"marginTop": "10px", "color": "slategray"})
                ], width=6)
            ])
        ]
    ),

    dbc.Row([
        dbc.Col([
            html.H4("Aggregated Data Table"),
            dcc.Loading(
                id="loading-table",
                type="default",
                children=dash_table.DataTable(
                    id="data-table",
                    page_size=10,
                    sort_action='native',
                    sort_by=[{"column_id": "total_rainfall", "direction": "desc"}]
                )
            )
        ], width=12)
    ]),

    dbc.Row([
        dbc.Col([
            html.H4("Rainfall Data Map"),
            dcc.Loading(
                id="loading-map",
                type="default",
                children=dcc.Graph(id="rainfall-map")
            )
        ], width=12)
    ])
])

# Callback to update circle center when latitude and longitude inputs change
@app.callback(
    Output('location-circle', 'center'),
    [Input('latitude-input', 'value'),
     Input('longitude-input', 'value')]
)
def update_circle_center(lat, lon):
    if lat is None or lon is None:
        return dash.no_update
    else:
        return [lat, lon]

# Callback to update circle radius when radius input changes
@app.callback(
    Output('location-circle', 'radius'),
    Input('radius-input', 'value')
)
def update_radius(radius):
    if radius is None:
        return dash.no_update
    else:
        return radius * 1000  # Convert km to meters

# Callback to control the collapse and update summary
@app.callback(
    [Output("collapse", "is_open"),
     Output("selection-summary", "children")],
    [Input("toggle-button", "n_clicks"),
     Input("fetch-data-button", "n_clicks"),
     Input("latitude-input", "value"),
     Input("longitude-input", "value"),
     Input("radius-input", "value"),
     Input("start-date-picker", "date"),
     Input("end-date-picker", "date")],
    [State("collapse", "is_open")]
)
def toggle_collapse(toggle_n_clicks, fetch_n_clicks, lat, lon, radius, start_date, end_date, is_open):
    ctx = dash.callback_context

    # Create summary text
    if lat is not None and lon is not None:
        summary = f"({lat:.2f}, {lon:.2f}) +{radius}km | {start_date} to {end_date}"
    else:
        summary = "No location selected"

    if not ctx.triggered:
        return is_open, summary

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == "toggle-button":
        return not is_open, summary
    elif button_id == "fetch-data-button":
        return False, summary
    else:
        return is_open, summary

@app.callback(
    [Output("data-table", "data"),
     Output("data-table", "columns"),
     Output("rainfall-map", "figure"),
     Output("message", "children")],
    [Input("fetch-data-button", "n_clicks")],
    [State("latitude-input", "value"),
     State("longitude-input", "value"),
     State("radius-input", "value"),
     State("start-date-picker", "date"),
     State("end-date-picker", "date")],
    prevent_initial_call=True
)
def fetch_data(n_clicks, lat, lon, radius, start_date, end_date):
    if lat is None or lon is None:
        return dash.no_update, dash.no_update, dash.no_update, "Please enter valid latitude and longitude."
    else:
        try:
            print(f"Fetching data for position: lat={lat}, lon={lon}, radius={radius}, start_date={start_date}, end_date={end_date}")

            # Convert lat, lon to easting, northing (British National Grid)
            transformer_to_bng = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
            easting, northing = transformer_to_bng.transform(lon, lat)

            # Get the list of stations
            st_l = r"https://environment.data.gov.uk/hydrology/id/stations"
            params = {
                "observedProperty": "rainfall",
                "easting": str(easting),
                "northing": str(northing),
                "dist": str(radius),
                "_limit": "100000"
            }

            st_response = requests.get(st_l, params=params)
            st_response.raise_for_status()
            st_r = st_response.json()
            st_items = st_r.get("items", [])
            n_st_items = len(st_items)

            if n_st_items == 0:
                return dash.no_update, dash.no_update, dash.no_update, "No stations found in the specified area."

            st_df = pd.DataFrame(st_items)
            if st_df.empty:
                return dash.no_update, dash.no_update, dash.no_update, "No stations found in the specified area."

            # Fetch rainfall data for each station
            val_df = pd.DataFrame()
            for st_rf in st_df["stationReference"]:
                link = (
                    f"https://environment.data.gov.uk/flood-monitoring/data/readings?"
                    f"parameter=rainfall&_view=full&startdate={start_date}&enddate={end_date}"
                    f"&_limit=10000&stationReference={st_rf}"
                )
                data_response = requests.get(link)
                data_response.raise_for_status()
                data = data_response.json()
                data_items = data.get("items", [])
                if data_items:
                    data_df = pd.json_normalize(data_items)
                    val_df = pd.concat([val_df, data_df], ignore_index=True)

            if val_df.empty:
                return dash.no_update, dash.no_update, dash.no_update, "No rainfall data found for the specified dates and area."

            # Clean and aggregate data
            val_df["value"] = pd.to_numeric(val_df["value"], errors='coerce')
            val_df = val_df.dropna(subset=["value"])
            val_df = val_df[(val_df["value"] <= 100) & (val_df["value"] >= 0)]
            val_df_grouped = val_df.groupby("measure.stationReference")["value"].sum().reset_index()
            val_df_grouped.rename(columns={"measure.stationReference": "stationReference", "value": "total_rainfall"}, inplace=True)

            # Merge station data with rainfall data
            merged_df = pd.merge(st_df, val_df_grouped, on="stationReference", how="left")
            merged_df["total_rainfall"] = merged_df["total_rainfall"].fillna(0)

            # Round total_rainfall to 1 decimal place
            merged_df["total_rainfall"] = merged_df["total_rainfall"].round(1)

            # Prepare table data
            table_columns = [
                {"name": "Label", "id": "label"},
                {"name": "Station Reference", "id": "stationReference"},
                {"name": "Easting", "id": "easting"},
                {"name": "Northing", "id": "northing"},
                {"name": "Total Rainfall (mm)", "id": "total_rainfall",
                 "type": "numeric",
                 "format": Format(precision=1, scheme=Scheme.fixed)}
            ]

            table_data = merged_df[["label", "stationReference", "easting", "northing", "total_rainfall"]].to_dict('records')

            # Convert easting and northing to latitude and longitude
            easting = merged_df["easting"].astype(float)
            northing = merged_df["northing"].astype(float)
            transformer_to_wgs84 = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
            lon_arr, lat_arr = transformer_to_wgs84.transform(easting.values, northing.values)
            merged_df["lon"] = lon_arr
            merged_df["lat"] = lat_arr

            # Create map figure with sequential color scale and less colorful base map
            fig = px.scatter_mapbox(
                merged_df,
                lat="lat",
                lon="lon",
                hover_name="label",
                hover_data={"total_rainfall": True, "lat": False, "lon": False},
                color="total_rainfall",
                size="total_rainfall",
                color_continuous_scale=px.colors.sequential.Blues,
                size_max=15,
                zoom=8
            )
            # Set the mapbox style to a less colorful one
            fig.update_layout(mapbox_style="carto-positron")
            fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

            # Sort table data by total_rainfall descending
            table_data.sort(key=lambda x: x["total_rainfall"], reverse=True)

            return table_data, table_columns, fig, f"Found {len(merged_df)} stations and {len(val_df)} rainfall readings."

        except Exception as e:
            print(f"An error occurred: {e}")
            return dash.no_update, dash.no_update, dash.no_update, f"An error occurred: {str(e)}"

if __name__ == "__main__":
    app.run_server(debug=True)
