# app.py
import warnings
import pandas as pd
import geopandas as gpd
import numpy as np
import dash
from dash import dcc, html
import plotly.express as px
import json
import os

warnings.filterwarnings("ignore")

# =======================
# 1. Cargar datos
# =======================
# Rutas
shapefile_path = "data/COLOMBIA/COLOMBIA.shp"
csv_path = "data/Estadísticas_Riesgos_Laborales_Positiva_2024_20250912.csv"
geojson_path = "data/colombia_simplificado.geojson"

# --- Si no existe el geojson simplificado, lo creamos ---
if not os.path.exists(geojson_path):
    gdf = gpd.read_file(shapefile_path, encoding="utf-8")
    # simplificación para hacerlo más liviano
    gdf["geometry"] = gdf["geometry"].simplify(0.01, preserve_topology=True)
    gdf.to_file(geojson_path, driver="GeoJSON")

# Cargar datos preprocesados
gdf = gpd.read_file(geojson_path)
df = pd.read_csv(csv_path)

# =======================
# 2. Limpieza de datos
# =======================
def sum_por_departamento(df, column_name):
    return df.groupby('DPTO_CNMBR')[column_name].sum().reset_index()

df_sum = sum_por_departamento(df, 'MUERTES_REPOR_AT')

# Normalizar nombres para merge
mal_car = ['á', 'é', 'í', 'ó', 'ú', 'ñ', 'ü']
bien_car = ['a', 'e', 'i', 'o', 'u', 'n', 'u']

munic_1 = df_sum['DPTO_CNMBR']
munic_2 = gdf['DPTO_CNMBR']

for j in range(len(mal_car)):
    munic_1 = munic_1.str.replace(mal_car[j], bien_car[j]).str.lower()
    munic_2 = munic_2.str.replace(mal_car[j], bien_car[j]).str.lower()

df_sum['DPTO_CNMBR'] = munic_1
gdf['DPTO_CNMBR'] = munic_2

Datos_tot = pd.merge(gdf, df_sum, on="DPTO_CNMBR", how="outer")

# Convertir el GeoDataFrame a geojson para px.choropleth
geojson = json.loads(Datos_tot.to_json())

# =======================
# 3. Inicializar app
# =======================
app = dash.Dash(__name__)
server = app.server   # necesario para Render

# =======================
# 4. Layout
# =======================
app.layout = html.Div([
    html.H1("Muertes por Accidentes de Trabajo en Colombia", style={'textAlign': 'center'}),

    # --- Dropdown para departamentos ---
    dcc.Dropdown(
        id='dropdown-depto',
        options=[{'label': dept.title(), 'value': dept} for dept in df_sum['DPTO_CNMBR'].unique()],
        value='bogota',  # valor inicial
        clearable=False
    ),

    # --- Mapa ---
    dcc.Graph(id='mapa-muertes'),

    # --- Gráfico de barras por departamento ---
    dcc.Graph(id='grafico-depto')
])

# =======================
# 5. Callbacks
# =======================
@app.callback(
    dash.dependencies.Output('mapa-muertes', 'figure'),
    [dash.dependencies.Input('dropdown-depto', 'value')]
)
def actualizar_mapa(depto_seleccionado):
    fig_mapa = px.choropleth(
        Datos_tot,
        geojson=geojson,
        locations="DPTO_CNMBR",            # columna en el DataFrame
        featureidkey="properties.DPTO_CNMBR",  # columna en el geojson
        color="MUERTES_REPOR_AT",
        hover_name="DPTO_CNMBR",
        color_continuous_scale="Reds",
        title="Muertes por Accidentes de Trabajo en Colombia"
    )
    fig_mapa.update_geos(fitbounds="locations", visible=False)

    # Resaltar el departamento seleccionado
    seleccionado = Datos_tot[Datos_tot["DPTO_CNMBR"] == depto_seleccionado]
    if not seleccionado.empty:
        centroide = seleccionado.geometry.centroid.iloc[0]
        fig_mapa.add_scattergeo(
            lon=[centroide.x],
            lat=[centroide.y],
            text=[depto_seleccionado],
            mode="markers+text",
            marker=dict(size=12, color="blue"),
            textposition="top center"
        )
    return fig_mapa


@app.callback(
    dash.dependencies.Output('grafico-depto', 'figure'),
    [dash.dependencies.Input('dropdown-depto', 'value')]
)
def actualizar_barras(depto_seleccionado):
    filtro = df_sum[df_sum['DPTO_CNMBR'] == depto_seleccionado]
    if filtro.empty:
        return px.bar(title="Sin datos disponibles")
    fig = px.bar(
        filtro,
        x="DPTO_CNMBR",
        y="MUERTES_REPOR_AT",
        title=f"Muertes reportadas en {depto_seleccionado.title()}",
        labels={"MUERTES_REPOR_AT": "Número de muertes"}
    )
    return fig

# =======================
# 6. Run
# =======================
if __name__ == '__main__':
    app.run_server(host="0.0.0.0", port=8080, debug=True)
