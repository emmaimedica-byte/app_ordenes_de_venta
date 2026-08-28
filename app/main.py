from fastapi import FastAPI
from sqlmodel import Session, select
from contextlib import asynccontextmanager
from datetime import datetime
from nicegui import ui

from app.database import create_db_and_tables, engine
from app.models.orden import OrdenVenta, EstadoOrden, HistorialOrden

# ----------------------------------------------------
# 1. CONTROL DE ESTADO GLOBAL PARA TIEMPO REAL
# ----------------------------------------------------
estado_global = {
    "ultima_actualizacion": datetime.now(),
    "ultima_ov_movida": None
}

def notificar_cambio_global(orden_id: int = None):
    estado_global["ultima_actualizacion"] = datetime.now()
    estado_global["ultima_ov_movida"] = orden_id

# ----------------------------------------------------
# 2. CICLO DE VIDA Y FASTAPI
# ----------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(title="Sistema de Seguimiento de Órdenes de Venta", lifespan=lifespan)

# ----------------------------------------------------
# 3. FUNCIONES AUXILIARES
# ----------------------------------------------------
def registrar_historial(session: Session, orden_id: int, estado_nuevo: str, estado_anterior: str = None, operador: str = "Operador General", obs: str = None):
    historial_entry = HistorialOrden(
        orden_id=orden_id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        usuario_operador=operador,
        observaciones=obs
    )
    session.add(historial_entry)

# ----------------------------------------------------
# 4. CONFIGURACIÓN DEL FLUJO DE TRABAJO
# ----------------------------------------------------
ESTADOS_ORDENADOS = [
    EstadoOrden.LOGISTICA,
    EstadoOrden.ALMACEN_SURTIDO,
    EstadoOrden.EMBARQUES_REVISION,
    EstadoOrden.CALIDAD_LIBERACION,
    EstadoOrden.TRANSPORTE_ENTREGA,
    EstadoOrden.ADMINISTRACION_COMPLETADO,
]

ESTADOS_CONFIG = [
    (EstadoOrden.LOGISTICA, "📋 Logística", "blue-500", "assignment"),
    (EstadoOrden.ALMACEN_SURTIDO, "📦 Almacén", "amber-500", "inventory_2"),
    (EstadoOrden.EMBARQUES_REVISION, "🚛 Embarques", "purple-500", "local_shipping"),
    (EstadoOrden.CALIDAD_LIBERACION, "🔬 Calidad", "teal-500", "verified"),
    (EstadoOrden.TRANSPORTE_ENTREGA, "🚚 Transporte", "indigo-500", "commute"),
    (EstadoOrden.ADMINISTRACION_COMPLETADO, "✅ Administración", "green-600", "check_circle"),
]

# ----------------------------------------------------
# 5. INTERFAZ GRÁFICA NICEGUI
# ----------------------------------------------------
@ui.page('/')
def main_page():
    ui.colors(primary='#1E3A8A', secondary='#3B82F6', accent='#10B981')

    # CSS + JavaScript para actualizar los temporizadores automáticamente
    ui.add_head_html('''
        <style>
            @keyframes resaltarEntrada {
                0% { transform: scale(0.85); opacity: 0.3; }
                50% { transform: scale(1.03); opacity: 0.9; }
                100% { transform: scale(1); opacity: 1; }
            }
            .animacion-entrada {
                animation: resaltarEntrada 0.4s ease-out forwards;
            }
            .tarjeta-ov {
                transition: all 0.25s ease-in-out;
            }
            .tarjeta-ov:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
        </style>

        <script>
            function actualizarTemporizadores() {
                const elementos = document.querySelectorAll('.badge-tiempo[data-iso]');
                const ahora = new Date();

                elementos.forEach(el => {
                    const isoFecha = el.getAttribute('data-iso');
                    if (!isoFecha) return;

                    const fechaOrden = new Date(isoFecha);
                    const diffMs = ahora - fechaOrden;
                    const diffHoras = diffMs / (1000 * 60 * 60);

                    el.className = 'badge-tiempo text-xs px-2 py-0.5 rounded-full transition-colors duration-300 ';

                    if (diffHoras < 4) {
                        const mins = Math.max(0, Math.floor(diffMs / (1000 * 60)));
                        el.innerText = `⏱️ ${mins} min`;
                        el.className += 'bg-green-100 text-green-800 border border-green-300';
                    } else if (diffHoras < 24) {
                        const hrs = Math.floor(diffHoras);
                        el.innerText = `⏳ ${hrs} hrs`;
                        el.className += 'bg-amber-100 text-amber-800 border border-amber-400';
                    } else {
                        const dias = Math.floor(diffHoras / 24);
                        el.innerText = `🚨 ${dias} día(s)`;
                        el.className += 'bg-red-100 text-red-800 font-bold border border-red-500';
                    }
                });
            }

            setInterval(actualizarTemporizadores, 10000);
            document.addEventListener("DOMContentLoaded", actualizarTemporizadores);
        </script>
    ''')

    filtro_texto = {'val': ''}
    version_cliente_tablero = {'ultima_vista': None}
    version_cliente_metrics = {'ultima_vista': None}

    # Encabezado principal
    with ui.header().classes('items-center justify-between bg-primary text-white p-3 shadow-md'):
        with ui.row().classes('items-center gap-2'):
            ui.icon('local_shipping', size='md')
            ui.label('Seguimiento de Órdenes de Venta').classes('text-lg md:text-xl font-bold')
        ui.label('Red: 172.16.31.105:8072').classes('text-xs opacity-80 bg-blue-900 px-3 py-1 rounded-full hidden md:block')

    # Pestañas
    with ui.tabs().classes('w-full bg-blue-50 border-b') as tabs:
        tab_kanban = ui.tab('Tablero General', icon='dashboard')
        tab_handheld = ui.tab('Modo Handheld / Escáner', icon='qr_code_scanner')
        tab_metrics = ui.tab('Dashboard & KPIs', icon='analytics')

    with ui.tab_panels(tabs, value=tab_kanban).classes('w-full bg-slate-50 p-2'):
        
        # ====================================================
        # PESTAÑA 1: TABLERO GENERAL
        # ====================================================
        with ui.tab_panel(tab_kanban):
            
            def refrescar_tablero():
                contenedor_tablero.clear()
                with contenedor_tablero:
                    render_columnas()
                version_cliente_tablero['ultima_vista'] = estado_global['ultima_actualizacion']
                ui.run_javascript('actualizarTemporizadores();')

            def verificar_cambios_tablero():
                if version_cliente_tablero['ultima_vista'] != estado_global['ultima_actualizacion']:
                    refrescar_tablero()

            ui.timer(2.0, verificar_cambios_tablero)

            def cambiar_estado_orden(orden_id: int, mover_adelante: bool = True):
                with Session(engine) as session:
                    orden = session.get(OrdenVenta, orden_id)
                    if not orden:
                        return
                    
                    idx_actual = ESTADOS_ORDENADOS.index(orden.estado)
                    nuevo_idx = idx_actual + 1 if mover_adelante else idx_actual - 1
                    
                    if 0 <= nuevo_idx < len(ESTADOS_ORDENADOS):
                        estado_anterior = orden.estado.value
                        orden.estado = ESTADOS_ORDENADOS[nuevo_idx]
                        orden.actualizado_en = datetime.now()
                        
                        registrar_historial(
                            session,
                            orden.id,
                            orden.estado.value,
                            estado_anterior,
                            "Operador Tablero",
                            "Avanzó de etapa" if mover_adelante else "Regresó de etapa"
                        )
                        session.add(orden)
                        session.commit()
                        
                        ui.notify(f'🚀 OV {orden.numero_ov} movida a {orden.estado.value}', type='info')
                        notificar_cambio_global(orden.id)
                        refrescar_tablero()

            def crear_nueva_ov():
                num_ov = input_ov.value or ''
                cliente_nombre = input_cliente.value or ''

                if not num_ov.strip():
                    ui.notify('Ingresa un número de OV válido', type='warning')
                    return
                
                with Session(engine) as session:
                    existente = session.exec(select(OrdenVenta).where(OrdenVenta.numero_ov == num_ov.strip())).first()
                    if existente:
                        ui.notify(f'La OV {num_ov} ya existe', type='negative')
                        return
                    
                    nueva = OrdenVenta(numero_ov=num_ov.strip(), cliente=cliente_nombre.strip() or "Cliente General")
                    session.add(nueva)
                    session.commit()
                    session.refresh(nueva)
                    
                    registrar_historial(session, nueva.id, nueva.estado.value, None, "Admin / Recepción", "Alta de Orden")
                    session.commit()
                    id_creada = nueva.id

                ui.notify(f'✨ OV {num_ov} registrada con éxito', type='positive')
                
                input_ov.value = ''
                input_cliente.value = ''
                
                notificar_cambio_global(id_creada)
                refrescar_tablero()

            def ver_historial_modal(orden_id: int):
                with Session(engine) as session:
                    orden = session.get(OrdenVenta, orden_id)
                    historial = session.exec(
                        select(HistorialOrden)
                        .where(HistorialOrden.orden_id == orden_id)
                        .order_by(HistorialOrden.fecha_registro.desc())
                    ).all()

                    with ui.dialog() as dialog, ui.card().classes('w-full max-w-lg p-6 animacion-entrada'):
                        ui.label(f'📜 Trazabilidad de {orden.numero_ov}').classes('text-lg font-bold text-blue-900 mb-1')
                        ui.label(f'Cliente: {orden.cliente}').classes('text-sm text-gray-600 mb-4')
                        
                        with ui.column().classes('w-full gap-3 max-h-80 overflow-y-auto'):
                            for item in historial:
                                with ui.card().classes('w-full p-3 bg-slate-50 border-l-4 border-blue-500 shadow-none'):
                                    with ui.row().classes('justify-between items-center w-full'):
                                        ui.label(f"➡️ {item.estado_nuevo}").classes('font-bold text-sm text-slate-800')
                                        ui.label(item.fecha_registro.strftime('%d/%m/%Y %H:%M:%S')).classes('text-xs text-gray-400')
                                    
                                    if item.estado_anterior:
                                        ui.label(f"Origen: {item.estado_anterior}").classes('text-xs text-gray-500')
                                    
                                    ui.label(f"👤 {item.usuario_operador}").classes('text-xs text-blue-800 mt-1 font-semibold')
                                    if item.observaciones:
                                        ui.label(f"💬 {item.observaciones}").classes('text-xs text-gray-600 italic')

                        ui.button('Cerrar', on_click=dialog.close).classes('mt-4 self-end bg-gray-500 text-white')
                    dialog.open()

            # Panel Superior
            with ui.row().classes('w-full mb-4 gap-4 items-center justify-between bg-white p-4 rounded-lg border shadow-xs'):
                with ui.row().classes('items-center gap-2 flex-1 max-w-md'):
                    ui.icon('search', size='sm').classes('text-gray-400')
                    
                    def filtrar_y_actualizar(e):
                        texto = (e.value or '').lower().strip()
                        filtro_texto['val'] = texto
                        refrescar_tablero()

                    input_buscar = ui.input(
                        placeholder='Buscar por OV o Cliente...',
                        on_change=filtrar_y_actualizar
                    ).classes('w-full').props('dense outlined clearable')

                with ui.row().classes('items-center gap-2 flex-1 justify-end'):
                    input_ov = ui.input(placeholder='Ej: OV-1001').classes('w-32').props('dense outlined')
                    input_cliente = ui.input(placeholder='Cliente').classes('w-44').props('dense outlined')
                    ui.button('Crear OV', icon='add', on_click=crear_nueva_ov)\
                        .classes('bg-secondary text-white font-bold')

            # Renderizado de Columnas Kanban
            def render_columnas():
                with Session(engine) as session:
                    todas_ordenes = session.exec(select(OrdenVenta)).all()

                if filtro_texto['val']:
                    query = filtro_texto['val']
                    todas_ordenes = [
                        o for o in todas_ordenes 
                        if query in (o.numero_ov or '').lower() or query in (o.cliente or '').lower()
                    ]

                with ui.row().classes('w-full overflow-x-auto gap-4 p-2 items-start'):
                    for estado, titulo, color, icono in ESTADOS_CONFIG:
                        ordenes_etapa = [o for o in todas_ordenes if o.estado == estado]
                        
                        with ui.column().classes('min-w-[280px] max-w-[320px] bg-slate-100 p-3 rounded-lg border shadow-sm'):
                            with ui.row().classes('w-full justify-between items-center mb-3'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon(icono).classes(f'text-{color}')
                                    ui.label(titulo).classes('font-bold text-gray-800')
                                ui.badge(str(len(ordenes_etapa)), color='blue-8').classes('rounded-full')

                            if not ordenes_etapa:
                                ui.label('Sin órdenes').classes('text-xs text-gray-400 italic py-4 text-center w-full')
                            else:
                                for orden in ordenes_etapa:
                                    es_recien_movida = (orden.id == estado_global["ultima_ov_movida"])
                                    clase_animacion = "animacion-entrada ring-2 ring-blue-400" if es_recien_movida else ""
                                    iso_fecha = orden.actualizado_en.isoformat()

                                    with ui.card().classes(f'tarjeta-ov w-full p-3 mb-2 bg-white rounded border shadow-xs {clase_animacion}'):
                                        with ui.row().classes('justify-between items-center w-full'):
                                            ui.label(orden.numero_ov).classes('font-bold text-blue-900 text-base')
                                            
                                            badge_timer = ui.label('calculando...').classes('badge-tiempo text-xs px-2 py-0.5 rounded-full')
                                            badge_timer.props(f'data-iso="{iso_fecha}"')

                                            ui.button(icon='visibility', on_click=lambda o_id=orden.id: ver_historial_modal(o_id))\
                                                .props('flat round dense color=grey-7').tooltip('Ver historial')

                                        ui.label(f'👤 {orden.cliente}').classes('text-xs text-gray-600 mb-2')
                                        
                                        with ui.row().classes('w-full justify-between items-center pt-2 border-t border-gray-100'):
                                            if orden.estado != EstadoOrden.LOGISTICA:
                                                ui.button(icon='arrow_back', on_click=lambda o_id=orden.id: cambiar_estado_orden(o_id, False))\
                                                    .props('flat round dense color=grey-7')
                                            else:
                                                ui.element('div')
                                            
                                            if orden.estado != EstadoOrden.ADMINISTRACION_COMPLETADO:
                                                ui.button(icon='arrow_forward', on_click=lambda o_id=orden.id: cambiar_estado_orden(o_id, True))\
                                                    .props('flat round dense color=primary')

            contenedor_tablero = ui.column().classes('w-full')
            refrescar_tablero()

        # ====================================================
        # PESTAÑA 2: MÓDULO PARA HANDHELD / ESCÁNER
        # ====================================================
        with ui.tab_panel(tab_handheld):
            with ui.column().classes('w-full max-w-md mx-auto items-center p-2 gap-4'):
                
                ui.label('📱 Módulo de Escaneo Rápido').classes('text-xl font-bold text-blue-900')
                ui.label('Escanea el código de barras para mover la orden a la etapa seleccionada.')\
                    .classes('text-xs text-gray-500 text-center')

                opciones_etapas = {e.value: titulo for e, titulo, _, _ in ESTADOS_CONFIG}
                select_etapa = ui.select(
                    options=opciones_etapas,
                    value=EstadoOrden.ALMACEN_SURTIDO.value,
                    label='Mover orden hacia la etapa:'
                ).classes('w-full text-lg')

                input_operador_hh = ui.input(
                    label='Operador / Handheld ID',
                    placeholder='Ej. Operador Handheld #1'
                ).classes('w-full').props('outlined')
                input_operador_hh.value = "Handheld Almacén"

                input_escaneo = ui.input(
                    label='📷 Escanear Código OV',
                    placeholder='Apunte con el escáner láser...'
                ).classes('w-full text-xl').props('outlined autofocus')

                resultado_card = ui.column().classes('w-full')

                def procesar_escaneo():
                    codigo = input_escaneo.value.strip()
                    if not codigo:
                        return
                    
                    estado_destino = select_etapa.value
                    nombre_op = input_operador_hh.value.strip() or "Handheld User"

                    with Session(engine) as session:
                        orden = session.exec(select(OrdenVenta).where(OrdenVenta.numero_ov == codigo)).first()
                        
                        resultado_card.clear()
                        with resultado_card:
                            if not orden:
                                ui.card().classes('w-full p-4 bg-red-100 border-l-8 border-red-500 text-red-900 shadow animacion-entrada')
                                ui.label('❌ ORDEN NO ENCONTRADA').classes('font-bold text-lg')
                                ui.label(f'No se encontró la OV "{codigo}". Primero créala en el Tablero General.').classes('text-xs')
                                ui.notify(f'OV {codigo} no existe', type='negative')
                            else:
                                estado_previo = orden.estado.value
                                orden.estado = EstadoOrden(estado_destino)
                                orden.operador_actual = nombre_op
                                orden.actualizado_en = datetime.now()

                                registrar_historial(
                                    session,
                                    orden.id,
                                    estado_destino,
                                    estado_previo,
                                    nombre_op,
                                    "Escaneo por Handheld"
                                )

                                session.add(orden)
                                session.commit()

                                ui.card().classes('w-full p-4 bg-green-100 border-l-8 border-green-500 text-green-900 shadow animacion-entrada')
                                ui.label('✅ ¡MOVIMIENTO REGISTRADO!').classes('font-bold text-lg')
                                ui.label(f'OV: {orden.numero_ov} | Cliente: {orden.cliente}').classes('text-sm font-semibold')
                                ui.label(f'De: {estado_previo} ➔ A: {estado_destino}').classes('text-xs font-semibold text-green-800 mt-1')
                                ui.notify(f'🚀 OV {codigo} movida a {estado_destino}', type='positive')

                                notificar_cambio_global(orden.id)

                    input_escaneo.value = ''
                    input_escaneo.run_method('focus')

                input_escaneo.on('keydown.enter', procesar_escaneo)

                ui.button('Procesar Escaneo', icon='qr_code', on_click=procesar_escaneo)\
                    .classes('w-full bg-green-600 text-white font-bold py-3 text-lg shadow-md hover:scale-105 transition-transform')

        # ====================================================
        # PESTAÑA 3: DASHBOARD DE MÉTRICAS Y KPIS (TIEMPO REAL AUTO)
        # ====================================================
        with ui.tab_panel(tab_metrics):
            
            def render_dashboard():
                contenedor_metrics.clear()
                with Session(engine) as session:
                    ordenes = session.exec(select(OrdenVenta)).all()

                total_ordenes = len(ordenes)
                completadas = len([o for o in ordenes if o.estado == EstadoOrden.ADMINISTRACION_COMPLETADO])
                activas = total_ordenes - completadas
                
                alertas = len([o for o in ordenes if o.estado != EstadoOrden.ADMINISTRACION_COMPLETADO and (datetime.now() - o.actualizado_en).total_seconds() > 86400])

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

                    conteo_etapas = [len([o for o in ordenes if o.estado == estado]) for estado, _, _, _ in ESTADOS_CONFIG]
                    nombres_etapas = [titulo for _, titulo, _, _ in ESTADOS_CONFIG]

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