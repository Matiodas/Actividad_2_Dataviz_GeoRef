import warnings
import pandas as pd
import geopandas as gpd
import numpy as np
import dash
from dash import dcc, html
import plotly.express as px
import json

warnings.filterwarnings("ignore")

# =======================
# 1. Cargar datos
# =======================
shapefile_path = "data/COLOMBIA/COLOMBIA.shp"
csv_path = "data/Estadísticas_Riesgos_Laborales_Positiva_2024_20250912.csv"

gdf = gpd.read_file(shapefile_path, encoding="utf-8")
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

Datos_tot = pd.merge(gdf, df_sum, on="DPTO_CNMBR", how="left")

# Convertir el GeoDataFrame a formato GeoJSON para Plotly
Datos_tot_geojson = json.loads(Datos_tot.to_json())

# Crear un mapeo de nombres de departamento a índice
depto_to_index = {depto: idx for idx, depto in enumerate(Datos_tot['DPTO_CNMBR'])}

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
    # Crear el mapa coroplético usando el GeoJSON
    fig_mapa = px.choropleth(
        Datos_tot,
        geojson=Datos_tot_geojson,
        locations=Datos_tot.index,
        color="MUERTES_REPOR_AT",
        featureidkey="id",
        hover_name="DPTO_CNMBR",
        hover_data={"MUERTES_REPOR_AT": True},
        color_continuous_scale="Reds",
        title="Muertes por Accidentes de Trabajo en Colombia",
        labels={"MUERTES_REPOR_AT": "Muertes Reportadas"}
    )
    
    # Configurar el mapa
    fig_mapa.update_geos(
        fitbounds="locations", 
        visible=False,
        bgcolor='rgba(0,0,0,0)'
    )
    
    fig_mapa.update_layout(
        margin={"r":0,"t":30,"l":0,"b":0},
        height=500
    )

    # Resaltar el departamento seleccionado
    if depto_seleccionado in depto_to_index:
        depto_index = depto_to_index[depto_seleccionado]
        seleccionado = Datos_tot.iloc[depto_index]
        
        if hasattr(seleccionado.geometry, 'centroid'):
            centroide = seleccionado.geometry.centroid
            fig_mapa.add_scattergeo(
                lon=[centroide.x],
                lat=[centroide.y],
                text=[depto_seleccionado.title()],
                mode="markers+text",
                marker=dict(size=15, color="blue", symbol="circle"),
                textposition="top center",
                showlegend=False
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
        labels={
            "MUERTES_REPOR_AT": "Número de muertes",
            "DPTO_CNMBR": "Departamento"
        }
    )
    
    fig.update_layout(
        xaxis_title="Departamento",
        yaxis_title="Muertes Reportadas"
    )
    
    return fig

# =======================
# 6. Run
# =======================
if __name__ == '__main__':
    app.run_server(host="0.0.0.0", port=8080, debug=True)
