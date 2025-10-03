# -*- coding: utf-8 -*-
"""
Dash App: Muertes por Accidentes de Trabajo en Colombia (2024)

Fuente datos:
- Shapefile DANE (Departamentos de Colombia)
- Estadísticas de Riesgos Laborales Positiva 2024
"""

import warnings
import geopandas as gpd
import pandas as pd
import numpy as np
import json
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px

warnings.filterwarnings("ignore")

# =======================
# 1. Cargar datos
# =======================
shapefile_path = "data/COLOMBIA/COLOMBIA.shp"
csv_path = "data/Estadísticas_Riesgos_Laborales_Positiva_2024_20250912.csv"

# Cargar shapefile y CSV
gdf = gpd.read_file(shapefile_path, encoding="utf-8")
df = pd.read_csv(csv_path, encoding="utf-8")

# =======================
# 2. Preprocesamiento
# =======================
def sum_por_departamento(df, column_name):
    return df.groupby("DPTO_CNMBR")[column_name].sum().reset_index()

df_sum = sum_por_departamento(df, "MUERTES_REPOR_AT")

# Reemplazar inconsistencias de nombres
df_sum["DPTO_CNMBR"].replace({
    "N. DE SANTANDER": "NORTE SANTANDER",
    "VALLE DEL CAUCA": "VALLE"
}, inplace=True)

gdf["DPTO_CNMBR"].replace({
    "NARI?O": "NARIÑO",
    "NORTE DE SANTANDER": "NORTE SANTANDER",
    "BOGOTA D.C.": "BOGOTA",
    "ARCHIPIELAGO DE SAN ANDRES": "SAN ANDRES",
    "VALLE DEL CAUCA": "VALLE"
}, inplace=True)

# Normalizar tildes
mal_car = ['á', 'é', 'í', 'ó', 'ú', 'ñ', 'ü']
bien_car = ['a', 'e', 'i', 'o', 'u', 'n', 'u']

def normalizar_texto(s):
    if pd.isna(s):
        return s
    s = s.lower()
    for i in range(len(mal_car)):
        s = s.replace(mal_car[i], bien_car[i])
    return s

df_sum["DPTO_CNMBR"] = df_sum["DPTO_CNMBR"].apply(normalizar_texto)
gdf["DPTO_CNMBR"] = gdf["DPTO_CNMBR"].apply(normalizar_texto)

# Merge
Datos_tot = pd.merge(gdf, df_sum, on="DPTO_CNMBR", how="outer")

# Simplificar geometría para Render
gdf_simplificado = gdf.copy()
gdf_simplificado["geometry"] = gdf_simplificado["geometry"].simplify(0.01, preserve_topology=True)
geojson = json.loads(gdf_simplificado.to_json())

# =======================
# 3. Inicializar app
# =======================
app = dash.Dash(__name__)
server = app.server   # necesario para Render

# =======================
# 4. Layout
# =======================
app.layout = html.Div([
    html.H1("Muertes por Accidentes de Trabajo en Colombia (2024)", style={"textAlign": "center"}),

    # Dropdown
    dcc.Dropdown(
        id="dropdown-depto",
        options=[{"label": dept.title(), "value": dept} for dept in df_sum["DPTO_CNMBR"].unique()],
        value="bogota",
        clearable=False
    ),

    # Mapa
    dcc.Graph(id="mapa-muertes"),

    # Gráfico de barras
    dcc.Graph(id="grafico-depto")
])

# =======================
# 5. Callbacks
# =======================
@app.callback(
    Output("mapa-muertes", "figure"),
    [Input("dropdown-depto", "value")]
)
def actualizar_mapa(depto_seleccionado):
    fig_mapa = px.choropleth(
        Datos_tot,
        geojson=geojson,
        locations="DPTO_CNMBR",
        featureidkey="properties.DPTO_CNMBR",
        color="MUERTES_REPOR_AT",
        hover_name="DPTO_CNMBR",
        color_continuous_scale="Reds",
        title="Muertes por Accidentes de Trabajo en Colombia"
    )
    fig_mapa.update_geos(fitbounds="locations", visible=False)

    # Resaltar seleccionado
    seleccionado = Datos_tot[Datos_tot["DPTO_CNMBR"] == depto_seleccionado]
    if not seleccionado.empty:
        centroide = seleccionado.geometry.centroid.iloc[0]
        fig_mapa.add_scattergeo(
            lon=[centroide.x],
            lat=[centroide.y],
            text=[depto_seleccionado.title()],
            mode="markers+text",
            marker=dict(size=12, color="blue"),
            textposition="top center"
        )
    return fig_mapa


@app.callback(
    Output("grafico-depto", "figure"),
    [Input("dropdown-depto", "value")]
)
def actualizar_barras(depto_seleccionado):
    filtro = df_sum[df_sum["DPTO_CNMBR"] == depto_seleccionado]
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
if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8080, debug=True)
