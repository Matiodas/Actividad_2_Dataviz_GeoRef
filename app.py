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
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go

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

# Preparar datos para el top 10
top_10 = df_sum.nlargest(10, 'MUERTES_REPOR_AT').copy()
top_10['DPTO_CNMBR'] = top_10['DPTO_CNMBR'].str.title()

# =======================
# 3. Inicializar app
# =======================
app = dash.Dash(__name__)
server = app.server   # necesario para Render

# =======================
# 4. Layout
# =======================
app.layout = html.Div([
    html.H1("Muertes por Accidentes de Trabajo en Colombia (2024)", 
            style={"textAlign": "center", "marginBottom": "20px"}),
    
    # Acordeón con información contextual
    html.Div([
        html.Div([
            html.H2("Acerca de este análisis", 
                   style={"cursor": "pointer", "margin": "0", "padding": "10px", 
                          "backgroundColor": "#f1f1f1", "border": "1px solid #ddd"}),
            html.Div([
                html.H3("Dataset Utilizado"),
                html.P("Este análisis utiliza dos fuentes principales de datos:"),
                html.Ul([
                    html.Li("Shapefile del DANE: Contiene las delimitaciones geográficas de los 32 departamentos de Colombia, con información de códigos y nombres departamentales."),
                    html.Li("Estadísticas de Riesgos Laborales (2024): Dataset suministrado por el gobierno a través de la compañía 'Positiva Compañía de Seguros S.A.', con 58,586 registros que incluyen variables como número de trabajadores, muertes reportadas por accidentes de trabajo, nuevas pensiones por invalidez e incapacidades permanentes.")
                ]),
                html.P("El período analizado corresponde a reportes del año 2024, sin embargo los datos fueron actualizados hasta este año 2025, con datos agregados a nivel departamental."),
                
                html.H3("Fuente de datos"),
                html.P([
                    "Datos suministrados desde: ",
                    html.A("https://www.datos.gov.co/Salud-y-Protecci-n-Social/Estad-sticas-Riesgos-Laborales-Positiva-2024/kwqa-xugj/about_data",
                          href="https://www.datos.gov.co/Salud-y-Protecci-n-Social/Estad-sticas-Riesgos-Laborales-Positiva-2024/kwqa-xugj/about_data",
                          target="_blank")
                ]),
                
                html.H3("Objetivo del análisis"),
                html.P("Identificar en qué departamento de Colombia se presenta el mayor número de accidentes laborales e intentar hallar una explicación para dicha situación."),
                
                html.H3("Evaluación de Resultados"),
                html.H4("Dispersión geográfica"),
                html.Ul([
                    html.Li("Concentración alta: Los valores absolutos más altos corresponden a Valle del Cauca (815), Antioquia (1,476) y Bogotá (2,372)."),
                    html.Li("Incidencia media: Las cifras de departamentos como Bolívar (142), Cundinamarca (525) y Santander (499) son intermedias."),
                    html.Li("Baja incidencia: Las cifras más reducidas se encuentran en los departamentos de la Amazonía (Guainía: 8, Amazonas: 11, Vaupés: 4).")
                ]),
                
                html.H4("Tendencias por región"),
                html.P("Es notoria una división territorial:"),
                html.Ul([
                    html.Li("Región Andina: El 70 % de las muertes reportadas pertenecen a esta región."),
                    html.Li("Regiones del Pacífico y el Caribe: Valores promedio, a excepción de los de Magdalena (323) y el Atlántico (179)."),
                    html.Li("Zona Amazónica: Presencia mínima, abarcando menos del 2% de la totalidad nacional.")
                ]),
                
                html.H4("Componentes explicativos"),
                html.P("Esta distribución es equivalente a:"),
                html.Ul([
                    html.Li("Número de habitantes y tamaño de la fuerza laboral"),
                    html.Li("Concentración de actividades industriales y de manufactura"),
                    html.Li("Existencia de sectores que tienen un alto riesgo (minería, manufactura y construcción)")
                ]),
                
                html.H3("Relevancia de la georreferenciación en investigaciones sociales"),
                html.P("El análisis espacial por medio de georreferenciación muestra su importancia esencial:"),
                html.Ol([
                    html.Li("Priorización de intervenciones: Permite identificar áreas críticas para centrar recursos y políticas públicas en materia de seguridad laboral."),
                    html.Li("Entendimiento de contextos regionales: Los patrones espaciales contribuyen a comprender la manera en que los problemas sociales se ven afectados por elementos geográficos, culturales y económicos."),
                    html.Li("Comunicación efectiva: Los mapas comunican datos complejos de forma intuitiva, lo que ayuda a los actores públicos y privados a tomar decisiones."),
                    html.Li("Análisis multivariable: El análisis causal se beneficia de la incorporación de datos demográficos, económicos y sociales con la variable en cuestión.")
                ]),
                
                html.H3("Conclusión"),
                html.P("La georreferenciación se establece como un instrumento esencial para convertir datos en información que pueda ser utilizada, mostrando no solo dónde tienen lugar los problemas, sino también indicando por qué persisten ciertos patrones de desigualdad territorial.")
            ], id="acordeon-content", style={"display": "none", "padding": "15px", "border": "1px solid #ddd", "borderTop": "none"})
        ], id="acordeon")
    ], style={"marginBottom": "20px"}),
    
    # Estadísticas principales
    html.Div([
        html.Div([
            html.H2("10,361", style={"fontSize": "2.5em", "margin": "0", "color": "#e74c3c"}),
            html.P("Total de Muertes Reportadas", style={"margin": "0", "fontWeight": "bold"})
        ], style={"textAlign": "center", "padding": "15px", "backgroundColor": "#f9f9f9", "borderRadius": "5px", "flex": "1", "margin": "0 10px"}),
        
        html.Div([
            html.H2("33", style={"fontSize": "2.5em", "margin": "0", "color": "#3498db"}),
            html.P("Departamentos Analizados", style={"margin": "0", "fontWeight": "bold"})
        ], style={"textAlign": "center", "padding": "15px", "backgroundColor": "#f9f9f9", "borderRadius": "5px", "flex": "1", "margin": "0 10px"})
    ], style={"display": "flex", "justifyContent": "center", "marginBottom": "20px"}),
    
    # Dropdown
    html.Div([
        html.Label("Selecciona un departamento:", style={"fontWeight": "bold", "marginBottom": "5px"}),
        dcc.Dropdown(
            id="dropdown-depto",
            options=[{"label": dept.title(), "value": dept} for dept in df_sum["DPTO_CNMBR"].unique()],
            value="bogota",
            clearable=False,
            style={"marginBottom": "20px"}
        )
    ], style={"width": "50%", "margin": "0 auto 20px"}),
    
    # Mapa y gráfico de departamento seleccionado
    html.Div([
        html.Div([
            dcc.Graph(id="mapa-muertes")
        ], style={"width": "60%", "display": "inline-block", "verticalAlign": "top"}),
        
        html.Div([
            dcc.Graph(id="grafico-depto")
        ], style={"width": "38%", "display": "inline-block", "verticalAlign": "top"})
    ]),
    
    # Gráfico de top 10
    html.Div([
        dcc.Graph(
            id="top-10-grafico",
            figure=px.bar(
                top_10, 
                x='MUERTES_REPOR_AT', 
                y='DPTO_CNMBR',
                orientation='h',
                title='Top 10 Departamentos con Más Muertes por Accidentes Laborales',
                labels={'MUERTES_REPOR_AT': 'Número de Muertes', 'DPTO_CNMBR': 'Departamento'},
                color='MUERTES_REPOR_AT',
                color_continuous_scale='Reds'
            ).update_layout(
                yaxis={'categoryorder': 'total ascending'},
                height=500
            )
        )
    ], style={"marginTop": "30px"})
])

# =======================
# 5. Callbacks
# =======================
@app.callback(
    Output("acordeon-content", "style"),
    [Input("acordeon", "n_clicks")],
    [State("acordeon-content", "style")]
)
def toggle_acordeon(n_clicks, current_style):
    if n_clicks is None:
        return current_style
    
    if current_style.get('display') == 'none':
        return {'display': 'block', 'padding': '15px', 'border': '1px solid #ddd', 'borderTop': 'none'}
    else:
        return {'display': 'none', 'padding': '15px', 'border': '1px solid #ddd', 'borderTop': 'none'}


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
    
    # Crear gráfico de barras con estilo mejorado
    fig = px.bar(
        filtro,
        x="DPTO_CNMBR",
        y="MUERTES_REPOR_AT",
        title=f"Muertes reportadas en {depto_seleccionado.title()}",
        labels={"MUERTES_REPOR_AT": "Número de muertes", "DPTO_CNMBR": "Departamento"},
        color_discrete_sequence=['#e74c3c']
    )
    
    # Mejorar el diseño
    fig.update_layout(
        xaxis_title="",
        yaxis_title="Número de Muertes",
        showlegend=False
    )
    
    # Añadir el valor numérico en las barras
    fig.update_traces(
        text=filtro['MUERTES_REPOR_AT'].values,
        textposition='outside'
    )
    
    return fig

# =======================
# 6. Run
# =======================
if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8080, debug=True)
