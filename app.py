import warnings
import pandas as pd
import geopandas as gpd
import numpy as np
import dash
from dash import dcc, html
import plotly.express as px
import plotly.graph_objects as go

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

munic_1 = df_sum['DPTO_CNMBR'].copy()
munic_2 = gdf['DPTO_CNMBR'].copy()

for j in range(len(mal_car)):
    munic_1 = munic_1.str.replace(mal_car[j], bien_car[j], regex=False).str.lower()
    munic_2 = munic_2.str.replace(mal_car[j], bien_car[j], regex=False).str.lower()

df_sum['DPTO_CNMBR_NORM'] = munic_1
gdf['DPTO_CNMBR_NORM'] = munic_2

# Hacer el merge
Datos_tot = gdf.merge(df_sum, left_on='DPTO_CNMBR_NORM', right_on='DPTO_CNMBR_NORM', how='left')

# Llenar NaN con 0 para las muertes
Datos_tot['MUERTES_REPOR_AT'] = Datos_tot['MUERTES_REPOR_AT'].fillna(0)

# =======================
# 3. Preparar datos para Plotly
# =======================
def crear_mapa_plotly(gdf):
    """Crear un mapa coroplético usando Plotly"""
    
    # Crear figura
    fig = go.Figure()
    
    # Agregar trazas para cada departamento
    for idx, row in gdf.iterrows():
        # Obtener las coordenadas del polígono
        if row.geometry.geom_type == 'Polygon':
            coords = list(row.geometry.exterior.coords)
            lons = [coord[0] for coord in coords]
            lats = [coord[1] for coord in coords]
        elif row.geometry.geom_type == 'MultiPolygon':
            lons = []
            lats = []
            for polygon in row.geometry.geoms:
                coords = list(polygon.exterior.coords)
                lons.extend([coord[0] for coord in coords])
                lats.extend([coord[1] for coord in coords])
                lons.append(None)  # Separador entre polígonos
                lats.append(None)
        else:
            continue
        
        # Agregar el polígono al mapa
        fig.add_trace(go.Scattergeo(
            lon=lons,
            lat=lats,
            mode='lines',
            line=dict(width=1, color='black'),
            fill='toself',
            fillcolor='lightblue',
            name=row['DPTO_CNMBR_NORM'],
            text=f"{row['DPTO_CNMBR_NORM'].title()}: {int(row['MUERTES_REPOR_AT'])} muertes",
            hoverinfo='text'
        ))
    
    # Configurar el layout del mapa
    fig.update_layout(
        title_text='Muertes por Accidentes de Trabajo en Colombia',
        showlegend=False,
        geo=dict(
            scope='south america',
            showland=True,
            landcolor='rgb(243, 243, 243)',
            countrycolor='rgb(204, 204, 204)',
            showcountries=True,
            showsubunits=True,
            subunitcolor='rgb(255, 255, 255)',
            center=dict(lat=4, lon=-74),  # Centro de Colombia
            projection_scale=5
        ),
        height=600
    )
    
    return fig

# =======================
# 4. Inicializar app
# =======================
app = dash.Dash(__name__)
server = app.server

# =======================
# 5. Layout
# =======================
app.layout = html.Div([
    html.H1("Muertes por Accidentes de Trabajo en Colombia", 
            style={'textAlign': 'center', 'marginBottom': 30}),
    
    # Información sobre los datos
    html.Div([
        html.P("Selecciona un departamento para ver detalles específicos"),
    ], style={'textAlign': 'center', 'marginBottom': 20}),

    # --- Dropdown para departamentos ---
    html.Div([
        dcc.Dropdown(
            id='dropdown-depto',
            options=[{'label': dept.title(), 'value': dept} for dept in sorted(df_sum['DPTO_CNMBR_NORM'].unique())],
            value='bogota',
            clearable=False,
            style={'width': '50%', 'margin': '0 auto'}
        ),
    ], style={'textAlign': 'center', 'marginBottom': 30}),
    
    # --- Mapa ---
    dcc.Graph(id='mapa-muertes'),
    
    # --- Gráfico de barras por departamento ---
    dcc.Graph(id='grafico-depto'),
    
    # --- Estadísticas resumen ---
    html.Div(id='estadisticas-resumen', style={'marginTop': 30, 'padding': 20})
])

# =======================
# 6. Callbacks
# =======================
@app.callback(
    dash.dependencies.Output('mapa-muertes', 'figure'),
    [dash.dependencies.Input('dropdown-depto', 'value')]
)
def actualizar_mapa(depto_seleccionado):
    return crear_mapa_plotly(Datos_tot)

@app.callback(
    dash.dependencies.Output('grafico-depto', 'figure'),
    [dash.dependencies.Input('dropdown-depto', 'value')]
)
def actualizar_barras(depto_seleccionado):
    filtro = df_sum[df_sum['DPTO_CNMBR_NORM'] == depto_seleccionado]
    
    if filtro.empty:
        fig = go.Figure()
        fig.update_layout(
            title="Sin datos disponibles para este departamento",
            xaxis_title="Departamento",
            yaxis_title="Muertes Reportadas"
        )
        return fig
    
    fig = px.bar(
        filtro,
        x="DPTO_CNMBR_NORM",
        y="MUERTES_REPOR_AT",
        title=f"Muertes reportadas en {depto_seleccionado.title()}",
        labels={
            "MUERTES_REPOR_AT": "Número de muertes",
            "DPTO_CNMBR_NORM": "Departamento"
        }
    )
    
    fig.update_layout(
        xaxis_title="Departamento",
        yaxis_title="Muertes Reportadas"
    )
    
    return fig

@app.callback(
    dash.dependencies.Output('estadisticas-resumen', 'children'),
    [dash.dependencies.Input('dropdown-depto', 'value')]
)
def actualizar_estadisticas(depto_seleccionado):
    # Estadísticas generales
    total_muertes = df_sum['MUERTES_REPOR_AT'].sum()
    promedio_muertes = df_sum['MUERTES_REPOR_AT'].mean()
    max_muertes = df_sum['MUERTES_REPOR_AT'].max()
    depto_max = df_sum.loc[df_sum['MUERTES_REPOR_AT'].idxmax(), 'DPTO_CNMBR_NORM']
    
    # Estadísticas del departamento seleccionado
    depto_data = df_sum[df_sum['DPTO_CNMBR_NORM'] == depto_seleccionado]
    if not depto_data.empty:
        muertes_depto = depto_data['MUERTES_REPOR_AT'].iloc[0]
        porcentaje = (muertes_depto / total_muertes * 100) if total_muertes > 0 else 0
    else:
        muertes_depto = 0
        porcentaje = 0
    
    return html.Div([
        html.H3("Estadísticas Resumen"),
        html.P(f"Total de muertes en Colombia: {int(total_muertes)}"),
        html.P(f"Promedio de muertes por departamento: {promedio_muertes:.1f}"),
        html.P(f"Departamento con más muertes: {depto_max.title()} ({int(max_muertes)})"),
        html.P(f"Muertes en {depto_seleccionado.title()}: {int(muertes_depto)} ({porcentaje:.1f}% del total)")
    ], style={'backgroundColor': '#f9f9f9', 'padding': '20px', 'borderRadius': '10px'})

# =======================
# 7. Run
# =======================
if __name__ == '__main__':
    app.run_server(host="0.0.0.0", port=8080, debug=True)
