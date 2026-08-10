from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import Session, select
from contextlib import asynccontextmanager
from datetime import datetime
from nicegui import ui

from app.database import create_db_and_tables, get_session, engine
from app.models.orden import OrdenVenta, EstadoOrden
from app.schemas.orden import OrdenVentaCrear, OrdenVentaActualizarEstado

# ----------------------------------------------------
# 1. CICLO DE VIDA DE FASTAPI
# ----------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(title="Sistema de Seguimiento de Órdenes de Venta", lifespan=lifespan)

# ----------------------------------------------------
# 2. ENDPOINTS API REST (Handheld / Escáner / Sistemas Externos)
# ----------------------------------------------------
@app.get("/api/ping")
def ping():
    return {"status": "ok", "message": "API activa"}

@app.post("/api/ordenes", response_model=OrdenVenta)
def crear_orden_api(orden_in: OrdenVentaCrear, session: Session = Depends(get_session)):
    existente = session.exec(select(OrdenVenta).where(OrdenVenta.numero_ov == orden_in.numero_ov)).first()
    if existente:
        raise HTTPException(status_code=400, detail="La Orden de Venta ya existe.")
    
    nueva_orden = OrdenVenta(numero_ov=orden_in.numero_ov, cliente=orden_in.cliente)
    session.add(nueva_orden)
    session.commit()
    session.refresh(nueva_orden)
    return nueva_orden

@app.get("/api/ordenes", response_model=list[OrdenVenta])
def listar_ordenes_api(session: Session = Depends(get_session)):
    return session.exec(select(OrdenVenta)).all()

@app.patch("/api/ordenes/avanzar", response_model=OrdenVenta)
def actualizar_estado_api(datos: OrdenVentaActualizarEstado, session: Session = Depends(get_session)):
    orden = session.exec(select(OrdenVenta).where(OrdenVenta.numero_ov == datos.numero_ov)).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden de Venta no encontrada.")
    
    orden.estado = datos.nuevo_estado
    orden.actualizado_en = datetime.now()
    if datos.operador:
        orden.operador_actual = datos.operador
    if datos.observaciones:
        orden.observaciones = datos.observaciones
        
    session.add(orden)
    session.commit()
    session.refresh(orden)
    return orden

# ----------------------------------------------------
# 3. MAPPING DE ESTADOS DEL FLUJO
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
# 4. INTERFAZ GRÁFICA NICEGUI
# ----------------------------------------------------
@ui.page('/')
def main_page():
    ui.colors(primary='#1E3A8A', secondary='#3B82F6', accent='#10B981')

    # Header
    with ui.header().classes('items-center justify-between bg-primary text-white p-4 shadow-md'):
        with ui.row().classes('items-center gap-2'):
            ui.icon('local_shipping', size='md')
            ui.label('Seguimiento de Órdenes de Venta').classes('text-xl font-bold')
        ui.label('Red: 172.16.31.105:8072').classes('text-xs opacity-80 bg-blue-900 px-3 py-1 rounded-full')

    def refrescar_tablero():
        contenedor_tablero.clear()
        with contenedor_tablero:
            render_columnas()

    # Mover orden a siguiente/anterior estado
    def cambiar_estado_orden(orden_id: int, mover_adelante: bool = True):
        with Session(engine) as session:
            orden = session.get(OrdenVenta, orden_id)
            if not orden:
                return
            
            idx_actual = ESTADOS_ORDENADOS.index(orden.estado)
            nuevo_idx = idx_actual + 1 if mover_adelante else idx_actual - 1
            
            if 0 <= nuevo_idx < len(ESTADOS_ORDENADOS):
                orden.estado = ESTADOS_ORDENADOS[nuevo_idx]
                orden.actualizado_en = datetime.now()
                session.add(orden)
                session.commit()
                ui.notify(f'OV {orden.numero_ov} movida a {orden.estado.value}', type='info')
                refrescar_tablero()

    # Crear nueva OV
    def crear_nueva_ov(num_ov: str, cliente_nombre: str):
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
            
        ui.notify(f'OV {num_ov} registrada', type='positive')
        input_ov.value = ''
        input_cliente.value = ''
        refrescar_tablero()

    # Formulario
    with ui.card().classes('w-full m-4 p-4 shadow-sm bg-gray-50 border'):
        ui.label('➕ Registrar Nueva Órden de Venta').classes('text-md font-bold text-gray-700 mb-2')
        with ui.row().classes('w-full items-center gap-4'):
            input_ov = ui.input(placeholder='Ej: OV-1001').classes('flex-1')
            input_cliente = ui.input(placeholder='Nombre del Cliente').classes('flex-1')
            ui.button('Crear Orden', icon='add', on_click=lambda: crear_nueva_ov(input_ov.value, input_cliente.value))\
                .classes('bg-secondary text-white font-bold')

    # Renderizado del tablero
    def render_columnas():
        with Session(engine) as session:
            todas_ordenes = session.exec(select(OrdenVenta)).all()

        with ui.row().classes('w-full overflow-x-auto gap-4 p-2 items-start'):
            for estado, titulo, color, icono in ESTADOS_CONFIG:
                ordenes_etapa = [o for o in todas_ordenes if o.estado == estado]
                
                with ui.column().classes('min-w-[280px] max-w-[320px] bg-slate-100 p-3 rounded-lg border shadow-sm'):
                    # Encabezado
                    with ui.row().classes('w-full justify-between items-center mb-3'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon(icono).classes(f'text-{color}')
                            ui.label(titulo).classes('font-bold text-gray-800')
                        ui.badge(str(len(ordenes_etapa)), color='blue-8').classes('rounded-full')

                    # Tarjetas
                    if not ordenes_etapa:
                        ui.label('Sin órdenes').classes('text-xs text-gray-400 italic py-4 text-center w-full')
                    else:
                        for orden in ordenes_etapa:
                            with ui.card().classes('w-full p-3 mb-2 bg-white shadow-xs rounded border border-gray-200'):
                                with ui.row().classes('justify-between items-center w-full'):
                                    ui.label(orden.numero_ov).classes('font-bold text-blue-900 text-base')
                                    ui.label(orden.creado_en.strftime('%H:%M')).classes('text-xs text-gray-400')
                                
                                ui.label(f'👤 {orden.cliente}').classes('text-xs text-gray-600 mb-2')
                                
                                # Botones de movimiento
                                with ui.row().classes('w-full justify-between items-center pt-2 border-t border-gray-100'):
                                    # Retroceder
                                    if orden.estado != EstadoOrden.LOGISTICA:
                                        ui.button(icon='arrow_back', on_click=lambda o_id=orden.id: cambiar_estado_orden(o_id, False))\
                                            .props('flat round dense color=grey-7').tooltip('Regresar etapa')
                                    else:
                                        ui.element('div')  # Espaciador
                                    
                                    # Avanzar
                                    if orden.estado != EstadoOrden.ADMINISTRACION_COMPLETADO:
                                        ui.button(icon='arrow_forward', on_click=lambda o_id=orden.id: cambiar_estado_orden(o_id, True))\
                                            .props('flat round dense color=primary').tooltip('Avanzar etapa')

    contenedor_tablero = ui.column().classes('w-full')
    refrescar_tablero()

ui.run_with(
    app,
    storage_secret='secreto_ordenes_venta_2026'
)

if __name__ in {"__main__", "__mp_main__"}:
    import uvicorn
    uvicorn.run("app.main:app", host="172.16.31.105", port=8072, reload=True)