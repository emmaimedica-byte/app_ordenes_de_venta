from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from contextlib import asynccontextmanager
from datetime import datetime
from nicegui import ui

from app.database import create_db_and_tables, engine
from app.models.orden import OrdenVenta, EstadoOrden, HistorialOrden

from app.repositories.orden_repository import OrdenRepository
from app.services.orden_service import OrdenService

from app.services.dashboard_service import DashboardService

from app.ui.layout import crear_layout
from app.ui.tablero import crear_tablero
from app.ui.handheld import crear_handheld

# ----------------------------------------------------
#  CONTROL DE ESTADO GLOBAL PARA TIEMPO REAL
# ----------------------------------------------------
estado_global = {
    "ultima_actualizacion": datetime.now(),
    "ultima_ov_movida": None
}

def notificar_cambio_global(orden_id: int = None):
    estado_global["ultima_actualizacion"] = datetime.now()
    estado_global["ultima_ov_movida"] = orden_id

# ----------------------------------------------------
#  CICLO DE VIDA Y FASTAPI
# ----------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(title="Sistema de Seguimiento de Órdenes de Venta", lifespan=lifespan)

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)

orden_repository = OrdenRepository()
orden_service = OrdenService(orden_repository)

dashboard_service = DashboardService()



# Configuración con paleta de colores completa para cada etapa:
# (Enum, Titulo, Icono, Color_Texto_Icono, Bg_Header, Border_Card, Badge_Color)
ESTADOS_CONFIG = [
    (EstadoOrden.LOGISTICA, "📋 Logística", "assignment", "blue-600", "bg-blue-50 border-blue-200", "border-l-4 border-blue-500", "blue-8"),
    (EstadoOrden.ALMACEN_SURTIDO, "📦 Almacén", "inventory_2", "amber-600", "bg-amber-50 border-amber-200", "border-l-4 border-amber-500", "amber-8"),
    (EstadoOrden.EMBARQUES_REVISION, "🚛 Embarques", "local_shipping", "purple-600", "bg-purple-50 border-purple-200", "border-l-4 border-purple-500", "purple-8"),
    (EstadoOrden.CALIDAD_LIBERACION, "🔬 Calidad", "verified", "teal-600", "bg-teal-50 border-teal-200", "border-l-4 border-teal-500", "teal-8"),
    (EstadoOrden.TRANSPORTE_ENTREGA, "🚚 Transporte", "commute", "indigo-600", "bg-indigo-50 border-indigo-200", "border-l-4 border-indigo-500", "indigo-8"),
    (EstadoOrden.ADMINISTRACION_COMPLETADO, "✅ Administración", "check_circle", "green-600", "bg-green-50 border-green-200", "border-l-4 border-green-600", "green-8"),
]

# ----------------------------------------------------
# 5. INTERFAZ GRÁFICA NICEGUI
# ----------------------------------------------------
@ui.page('/')
def main_page():
    filtro_texto = {'val': ''}
    version_cliente_tablero = {'ultima_vista': None}
    version_cliente_metrics = {'ultima_vista': None}

    tab_panels, tab_kanban, tab_handheld, tab_metrics = crear_layout()

    with tab_panels:

        # ====================================================
        # PESTAÑA 1: TABLERO GENERAL (CON COLORES DINÁMICOS)
        # ====================================================
        crear_tablero(
            tab_kanban=tab_kanban,
            filtro_texto=filtro_texto,
            version_cliente_tablero=version_cliente_tablero,
            estado_global=estado_global,
            orden_service=orden_service,
            orden_repository=orden_repository,
            notificar_cambio_global=notificar_cambio_global,
            estados_config=ESTADOS_CONFIG,
        )

        # ====================================================
        # PESTAÑA 2: MÓDULO PARA HANDHELD / ESCÁNER
        # ====================================================
        crear_handheld(
            tab_handheld=tab_handheld,
            orden_service=orden_service,
            orden_repository=orden_repository,
            notificar_cambio_global=notificar_cambio_global,
            estados_config=ESTADOS_CONFIG,
        )

        # ====================================================
        # PESTAÑA 3: DASHBOARD DE MÉTRICAS Y KPIS
        # ====================================================
        with ui.tab_panel(tab_metrics):

            def render_dashboard():
                contenedor_metrics.clear()
                with Session(engine) as session:
                    ordenes = orden_repository.obtener_todas(
                        session
                    )

                metricas = dashboard_service.calcular_metricas(
                    ordenes
                )

                total_ordenes = metricas["total_ordenes"]
                activas = metricas["activas"]
                completadas = metricas["completadas"]
                alertas = metricas["alertas"]

                distribucion = dashboard_service.calcular_distribucion_por_etapa(
                    ordenes
                )

                with contenedor_metrics:
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        ui.label('📈 Indicadores Clave de Operación (KPIs)').classes('text-xl font-bold text-blue-900')
                        ui.label('🟢 En Vivo').classes('text-xs bg-green-100 text-green-800 font-bold px-2.5 py-1 rounded-full border border-green-300')

                    with ui.row().classes('w-full gap-4 mb-6'):
                        with ui.card().classes('flex-1 p-4 bg-blue-50 border-l-4 border-blue-600 shadow-xs hover:scale-105 transition-transform'):
                            ui.label('Total Órdenes').classes('text-xs font-semibold text-gray-500 uppercase')
                            ui.label(str(total_ordenes)).classes('text-3xl font-extrabold text-blue-900')

                        with ui.card().classes('flex-1 p-4 bg-amber-50 border-l-4 border-amber-500 shadow-xs hover:scale-105 transition-transform'):
                            ui.label('En Proceso').classes('text-xs font-semibold text-gray-500 uppercase')
                            ui.label(str(activas)).classes('text-3xl font-extrabold text-amber-700')

                        with ui.card().classes('flex-1 p-4 bg-green-50 border-l-4 border-green-600 shadow-xs hover:scale-105 transition-transform'):
                            ui.label('Completadas').classes('text-xs font-semibold text-gray-500 uppercase')
                            ui.label(str(completadas)).classes('text-3xl font-extrabold text-green-800')

                        with ui.card().classes('flex-1 p-4 bg-red-50 border-l-4 border-red-500 shadow-xs hover:scale-105 transition-transform'):
                            ui.label('Alertas (>24h)').classes('text-xs font-semibold text-gray-500 uppercase')
                            ui.label(str(alertas)).classes('text-3xl font-extrabold text-red-700')

                    conteo_etapas = [
                        distribucion.get(estado.value, 0)
                        for estado in EstadoOrden
                    ]
                    nombres_etapas = [titulo for _, titulo, _, _, _, _, _ in ESTADOS_CONFIG]

                    ui.label('📊 Distribución de Órdenes por Etapa').classes('text-base font-bold text-gray-700 mt-2 mb-2')

                    echart_config = {
                        'xAxis': {'type': 'category', 'data': nombres_etapas, 'axisLabel': {'rotate': 15}},
                        'yAxis': {'type': 'value'},
                        'series': [{'data': conteo_etapas, 'type': 'bar', 'itemStyle': {'color': '#3B82F6'}}],
                        'tooltip': {'trigger': 'axis'}
                    }
                    ui.echart(echart_config).classes('w-full h-80 bg-white p-4 rounded-lg border shadow-xs')

                    ui.button('Actualizar Métricas', icon='refresh', on_click=render_dashboard)\
                        .classes('mt-4 bg-primary text-white font-bold hover:scale-105 transition-transform')

                version_cliente_metrics['ultima_vista'] = estado_global['ultima_actualizacion']

            def verificar_cambios_metrics():
                if version_cliente_metrics['ultima_vista'] != estado_global['ultima_actualizacion']:
                    render_dashboard()

            ui.timer(3.0, verificar_cambios_metrics)

            contenedor_metrics = ui.column().classes('w-full')
            render_dashboard()

ui.run_with(
    app,
    storage_secret='secreto_ordenes_venta_2026'
)

if __name__ in {"__main__", "__mp_main__"}:
    import uvicorn
    uvicorn.run("app.main:app", host="172.16.31.105", port=8072, reload=True)