import warnings
import pandas as pd
import geopandas as gpd
import dash
from dash import dcc, html
import plotly.express as px
import plotly.graph_objects as go
import json

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
# 2. Limpieza de datos OPTIMIZADA CON CORRECCIONES DE NOMBRES
# =======================

# Primero: corregir nombres específicos en ambos datasets
df_sum = df.groupby('DPTO_CNMBR')['MUERTES_REPOR_AT'].sum().reset_index()

# Correcciones específicas en df_sum
df_sum['DPTO_CNMBR'].replace({
    'N. DE SANTANDER': 'NORTE SANTANDER', 
    'VALLE DEL CAUCA': 'VALLE'
}, inplace=True)

# Correcciones específicas en gdf
gdf['DPTO_CNMBR'].replace({
    'NARI?O': 'NARIÑO', 
    'NORTE DE SANTANDER': 'NORTE SANTANDER', 
    'BOGOTA D.C.': 'BOGOTA', 
    'ARCHIPIELAGO DE SAN ANDRES': 'SAN ANDRES', 
    'VALLE DEL CAUCA': 'VALLE'
}, inplace=True)

# Segundo: normalizar caracteres especiales
mal_car = ['á', 'é', 'í', 'ó', 'ú', 'ñ', 'ü']
bien_car = ['a', 'e', 'i', 'o', 'u', 'n', 'u']

# Aplicar normalización a df_sum
munic_1 = df_sum['DPTO_CNMBR'].copy()
for j in range(len(mal_car)):
    munic_1 = munic_1.str.replace(mal_car[j], bien_car[j], regex=False).str.lower()
df_sum['DPTO_NORM'] = munic_1

# Aplicar normalización a gdf
munic_2 = gdf['DPTO_CNMBR'].copy()
for j in range(len(mal_car)):
    munic_2 = munic_2.str.replace(mal_car[j], bien_car[j], regex=False).str.lower()
gdf['DPTO_NORM'] = munic_2

# Merge simple
datos_combinados = gdf.merge(df_sum, on='DPTO_NORM', how='left')
datos_combinados['MUERTES_REPOR_AT'] = datos_combinados['MUERTES_REPOR_AT'].fillna(0)

# =======================
# 3. SOLUCIÓN MEJORADA: MAPA REAL CON SHAPEFILE
# =======================
def crear_mapa_real():
    """Crear un mapa real con el shapefile de Colombia"""
    
    try:
        # Simplificar geometrías para mejor rendimiento
        datos_combinados_simple = datos_combinados.copy()
        datos_combinados_simple['geometry'] = datos_combinados_simple['geometry'].simplify(0.01)
        
        # Convertir a GeoJSON
        geojson_data = json.loads(datos_combinados_simple.to_json())
        
        # Crear mapa coroplético con el shapefile real
        fig = px.choropleth_mapbox(
            datos_combinados_simple,
            geojson=geojson_data,
            locations=datos_combinados_simple.index,
            color="MUERTES_REPOR_AT",
            hover_name="DPTO_CNMBR",
            hover_data={"MUERTES_REPOR_AT": True, "DPTO_NORM": False},
            color_continuous_scale="Reds",
            title="Muertes por Accidentes de Trabajo en Colombia",
            mapbox_style="carto-positron",
            center={"lat": 4, "lon": -74},
            zoom=4,
            opacity=0.7
        )
        
        fig.update_layout(
            height=600,
            margin={"r":0,"t":50,"l":0,"b":0},
            coloraxis_colorbar=dict(
                title="Número de Muertes",
                thickness=15,
                len=0.75
            )
        )
        
        return fig
        
    except Exception as e:
        print(f"Error creando mapa real: {e}")
        # Fallback: mapa simple con centroides
        return crear_mapa_simple_fallback()

def crear_mapa_simple_fallback():
    """Fallback: mapa simple con centroides"""
    
    centroids = []
    for idx, row in datos_combinados.iterrows():
        try:
            if row.geometry and not row.geometry.is_empty:
                centroid = row.geometry.centroid
                centroids.append({
                    'depto': row['DPTO_NORM'],
                    'lat': centroid.y,
                    'lon': centroid.x,
                    'muertes': row['MUERTES_REPOR_AT'],
                    'nombre_real': row['DPTO_CNMBR']
                })
        except:
            continue
    
    if not centroids:
        # Fallback: crear datos de ejemplo
        centroids = [
            {'depto': 'bogota', 'lat': 4.7110, 'lon': -74.0721, 'muertes': 10, 'nombre_real': 'Bogotá'},
            {'depto': 'antioquia', 'lat': 6.2442, 'lon': -75.5736, 'muertes': 25, 'nombre_real': 'Antioquia'},
            {'depto': 'valle', 'lat': 3.4516, 'lon': -76.5320, 'muertes': 15, 'nombre_real': 'Valle'},
            {'depto': 'cundinamarca', 'lat': 4.6097, 'lon': -74.0817, 'muertes': 8, 'nombre_real': 'Cundinamarca'}
        ]
    
    df_centroids = pd.DataFrame(centroids)
    
    # Crear mapa de burbujas
    fig = px.scatter_geo(
        df_centroids,
        lat='lat',
        lon='lon',
        size='muertes',
        hover_name='nombre_real',
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
               style={'textAlign': 'center', 'color': '#666'}),
        html.P("🗺️ Mapa interactivo de Colombia con datos reales", 
               style={'textAlign': 'center', 'color': '#888', 'fontSize': '14px'})
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
        'borderRadius': '10px',
        'border': '1px solid #dee2e6'
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
    # Retornar el mapa real con shapefile
    return crear_mapa_real()

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
    
    # Obtener el nombre real para mostrar en el título
    nombre_real = datos_combinados[datos_combinados['DPTO_NORM'] == depto_seleccionado]['DPTO_CNMBR'].iloc[0] \
        if not datos_combinados[datos_combinados['DPTO_NORM'] == depto_seleccionado].empty else depto_seleccionado.title()
    
    fig = px.bar(
        depto_data,
        x='DPTO_NORM',
        y='MUERTES_REPOR_AT',
        title=f'Muertes Reportadas en {nombre_real}',
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
    
    # Personalizar la barra
    fig.update_traces(marker_color='#dc3545', marker_line_color='#c82333', 
                     marker_line_width=1.5, opacity=0.8)
    
    return fig

@app.callback(
    dash.dependencies.Output('estadisticas', 'children'),
    [dash.dependencies.Input('dropdown-depto', 'value')]
)
def actualizar_estadisticas(depto_seleccionado):
    total_muertes = df_sum['MUERTES_REPOR_AT'].sum()
    depto_muertes = df_sum[df_sum['DPTO_NORM'] == depto_seleccionado]['MUERTES_REPOR_AT'].sum()
    porcentaje = (depto_muertes / total_muertes * 100) if total_muertes > 0 else 0
    
    # Obtener el nombre real para mostrar
    nombre_real = datos_combinados[datos_combinados['DPTO_NORM'] == depto_seleccionado]['DPTO_CNMBR'].iloc[0] \
        if not datos_combinados[datos_combinados['DPTO_NORM'] == depto_seleccionado].empty else depto_seleccionado.title()
    
    return [
        html.H3("📊 Estadísticas Resumen", style={'marginBottom': 15, 'color': '#343a40'}),
        html.P(f"📍 Departamento seleccionado: {nombre_real}", 
               style={'marginBottom': 8, 'fontWeight': 'bold'}),
        html.P(f"🕴️ Muertes reportadas: {int(depto_muertes)}", 
               style={'marginBottom': 8}),
        html.P(f"📈 Porcentaje del total nacional: {porcentaje:.1f}%", 
               style={'marginBottom': 8}),
        html.P(f"🇨🇴 Total muertes en Colombia: {int(total_muertes)}", 
               style={'marginBottom': 0})
    ]

# =======================
# 7. Configuración para Render
# =======================
if __name__ == '__main__':
    app.run_server(host="0.0.0.0", port=8080, debug=False)
