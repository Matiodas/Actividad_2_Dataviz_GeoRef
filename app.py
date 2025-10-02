import warnings
import pandas as pd
import geopandas as gpd
import dash
from dash import dcc, html
import plotly.express as px
import plotly.graph_objects as go

warnings.filterwarnings("ignore")

# =======================
# 1. Cargar datos CON MANEJO DE ERRORES
# =======================
try:
    shapefile_path = "data/COLOMBIA/COLOMBIA.shp"
    csv_path = "data/Estadísticas_Riesgos_Laborales_Positiva_2024_20250912.csv"
    
    gdf = gpd.read_file(shapefile_path, encoding="utf-8")
    df = pd.read_csv(csv_path)
    
    print("✅ Datos cargados correctamente")
    print(f"Shapefile: {gdf.shape}, CSV: {df.shape}")
    
except Exception as e:
    print(f"❌ Error cargando datos: {e}")
    # Crear datos de ejemplo para desarrollo
    gdf = gpd.GeoDataFrame({
        'DPTO_CNMBR': ['bogota', 'antioquia', 'valle', 'cundinamarca'],
        'geometry': [None, None, None, None]  # Geometrías dummy
    })
    df = pd.DataFrame({
        'DPTO_CNMBR': ['bogota', 'antioquia', 'valle', 'cundinamarca'],
        'MUERTES_REPOR_AT': [10, 25, 15, 8]
    })

# =======================
# 2. Limpieza de datos OPTIMIZADA
# =======================
def normalizar_texto(texto):
    if pd.isna(texto):
        return texto
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ñ': 'n', 'ü': 'u'
    }
    texto = str(texto).lower()
    for orig, repl in replacements.items():
        texto = texto.replace(orig, repl)
    return texto

# Procesar datos de manera eficiente
df_sum = df.groupby('DPTO_CNMBR')['MUERTES_REPOR_AT'].sum().reset_index()
df_sum['DPTO_NORM'] = df_sum['DPTO_CNMBR'].apply(normalizar_texto)
gdf['DPTO_NORM'] = gdf['DPTO_CNMBR'].apply(normalizar_texto)

# Merge simple
datos_combinados = gdf.merge(df_sum, on='DPTO_NORM', how='left')
datos_combinados['MUERTES_REPOR_AT'] = datos_combinados['MUERTES_REPOR_AT'].fillna(0)

# =======================
# 3. SOLUCIÓN SIMPLIFICADA PARA EL MAPA
# =======================
def crear_mapa_simple():
    """Crear un mapa simple y eficiente usando centroides"""
    
    # Calcular centroides de manera segura
    centroids = []
    for idx, row in datos_combinados.iterrows():
        try:
            if row.geometry and not row.geometry.is_empty:
                centroid = row.geometry.centroid
                centroids.append({
                    'depto': row['DPTO_NORM'],
                    'lat': centroid.y,
                    'lon': centroid.x,
                    'muertes': row['MUERTES_REPOR_AT']
                })
        except:
            continue
    
    if not centroids:
        # Fallback: crear datos de ejemplo
        centroids = [
            {'depto': 'bogota', 'lat': 4.7110, 'lon': -74.0721, 'muertes': 10},
            {'depto': 'antioquia', 'lat': 6.2442, 'lon': -75.5736, 'muertes': 25},
            {'depto': 'valle', 'lat': 3.4516, 'lon': -76.5320, 'muertes': 15}
        ]
    
    df_centroids = pd.DataFrame(centroids)
    
    # Crear mapa de burbujas (mucho más eficiente)
    fig = px.scatter_geo(
        df_centroids,
        lat='lat',
        lon='lon',
        size='muertes',
        hover_name='depto',
        hover_data={'muertes': True, 'lat': False, 'lon': False},
        size_max=30,
        title="Muertes por Accidentes de Trabajo en Colombia",
        projection='natural earth'
    )
    
    # Configurar el mapa para Colombia
    fig.update_geos(
        visible=False,
        resolution=50,
        showcountries=True,
        countrycolor="black",
        showsubunits=True,
        subunitcolor="blue",
        center=dict(lat=4, lon=-74),
        projection_scale=5
    )
    
    fig.update_layout(
        height=500,
        margin={"r":0,"t":50,"l":0,"b":0}
    )
    
    return fig

# =======================
# 4. Inicializar app
# =======================
app = dash.Dash(__name__)
server = app.server

# =======================
# 5. Layout OPTIMIZADO
# =======================
app.layout = html.Div([
    html.H1("Muertes por Accidentes de Trabajo en Colombia", 
            style={'textAlign': 'center', 'marginBottom': 20}),
    
    html.Div([
        html.P("Selecciona un departamento para ver detalles", 
               style={'textAlign': 'center', 'color': '#666'})
    ]),
    
    # Dropdown centrado
    html.Div([
        dcc.Dropdown(
            id='dropdown-depto',
            options=[{'label': dept.title(), 'value': dept} 
                    for dept in sorted(df_sum['DPTO_NORM'].unique())],
            value='bogota',
            clearable=False,
            style={'width': '300px', 'margin': '0 auto'}
        )
    ], style={'textAlign': 'center', 'marginBottom': 30}),
    
    # Mapa
    dcc.Graph(id='mapa-muertes'),
    
    # Gráfico de barras
    dcc.Graph(id='grafico-depto'),
    
    # Estadísticas
    html.Div(id='estadisticas', style={
        'marginTop': 30, 
        'padding': 20, 
        'backgroundColor': '#f8f9fa',
        'borderRadius': '10px'
    })
])

# =======================
# 6. Callbacks OPTIMIZADOS
# =======================
@app.callback(
    dash.dependencies.Output('mapa-muertes', 'figure'),
    [dash.dependencies.Input('dropdown-depto', 'value')]
)
def actualizar_mapa(depto_seleccionado):
    # Retornar el mapa simple (no depende del dropdown para mejor performance)
    return crear_mapa_simple()

@app.callback(
    dash.dependencies.Output('grafico-depto', 'figure'),
    [dash.dependencies.Input('dropdown-depto', 'value')]
)
def actualizar_barras(depto_seleccionado):
    depto_data = df_sum[df_sum['DPTO_NORM'] == depto_seleccionado]
    
    if depto_data.empty:
        fig = go.Figure()
        fig.update_layout(
            title="No hay datos disponibles para este departamento",
            xaxis_title="Departamento",
            yaxis_title="Muertes Reportadas"
        )
        return fig
    
    fig = px.bar(
        depto_data,
        x='DPTO_NORM',
        y='MUERTES_REPOR_AT',
        title=f'Muertes Reportadas en {depto_seleccionado.title()}',
        labels={
            'MUERTES_REPOR_AT': 'Número de Muertes',
            'DPTO_NORM': 'Departamento'
        }
    )
    
    fig.update_layout(
        xaxis_title="Departamento",
        yaxis_title="Muertes Reportadas",
        showlegend=False
    )
    
    return fig

@app.callback(
    dash.dependencies.Output('estadisticas', 'children'),
    [dash.dependencies.Input('dropdown-depto', 'value')]
)
def actualizar_estadisticas(depto_seleccionado):
    total_muertes = df_sum['MUERTES_REPOR_AT'].sum()
    depto_muertes = df_sum[df_sum['DPTO_NORM'] == depto_seleccionado]['MUERTES_REPOR_AT'].sum()
    porcentaje = (depto_muertes / total_muertes * 100) if total_muertes > 0 else 0
    
    return [
        html.H3("📊 Estadísticas Resumen", style={'marginBottom': 15}),
        html.P(f"📍 Departamento seleccionado: {depto_seleccionado.title()}"),
        html.P(f"🕴️ Muertes en {depto_seleccionado.title()}: {int(depto_muertes)}"),
        html.P(f"📈 Porcentaje del total: {porcentaje:.1f}%"),
        html.P(f"🇨🇴 Total muertes en Colombia: {int(total_muertes)}")
    ]

# =======================
# 7. Configuración para Render
# =======================
if __name__ == '__main__':
    app.run_server(host="0.0.0.0", port=8080, debug=False)  # debug=False en producción
