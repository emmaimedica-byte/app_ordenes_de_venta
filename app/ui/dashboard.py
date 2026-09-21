from nicegui import ui
from sqlmodel import Session

from app.database import engine
from app.models.orden import EstadoOrden


def crear_dashboard(
    tab_metrics,
    version_cliente_metrics,
    estado_global,
    dashboard_service,
    orden_repository,
    estados_config,
):
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
                    nombres_etapas = [titulo for _, titulo, _, _, _, _, _ in estados_config]

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