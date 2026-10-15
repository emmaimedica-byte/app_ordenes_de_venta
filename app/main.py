from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from contextlib import asynccontextmanager
from datetime import datetime
from nicegui import app as nicegui_app, ui

from app.database import create_db_and_tables, engine
from app.models.orden import OrdenVenta, EstadoOrden, HistorialOrden

from app.repositories.orden_repository import OrdenRepository
from app.services.orden_service import OrdenService

from app.services.dashboard_service import DashboardService

from app.services.auth_service import AuthService
from app.models.usuario import Usuario

from app.ui.layout import crear_layout
from app.ui.tablero import crear_tablero
from app.ui.handheld import crear_handheld
from app.ui.dashboard import crear_dashboard
from app.ui.asignaciones import crear_asignaciones

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
auth_service = AuthService()



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

@ui.page('/login')
def login_page():
    if nicegui_app.storage.user.get('usuario_id'):
        ui.navigate.to('/')
        return

    with ui.card().classes('absolute-center w-full max-w-md p-6'):
        ui.icon('local_shipping', size='xl').classes('text-primary')
        ui.label('Seguimiento de Órdenes de Venta').classes(
            'text-xl font-bold'
        )
        ui.label('Inicia sesión para continuar').classes(
            'text-gray-500'
        )

        username = ui.input('Usuario').classes('w-full').props(
            'autocomplete=username'
        )

        password = ui.input('Contraseña').classes('w-full').props(
            'type=password autocomplete=current-password'
        )

        def iniciar_sesion():
            nombre_usuario = (username.value or '').strip()
            contrasena = password.value or ''

            if not nombre_usuario or not contrasena:
                ui.notify(
                    'Ingresa tu usuario y contraseña.',
                    type='warning'
                )
                return

            with Session(engine) as session:
                usuario = auth_service.autenticar_usuario(
                    session,
                    nombre_usuario,
                    contrasena
                )

                if usuario is None:
                    ui.notify(
                        'Credenciales incorrectas o usuario inactivo.',
                        type='negative'
                    )
                    return

                usuario_id = usuario.id

            nicegui_app.storage.user['usuario_id'] = usuario_id
            ui.navigate.to('/')

        ui.button(
            'Iniciar sesión',
            icon='login',
            on_click=iniciar_sesion
        ).classes('w-full')

        password.on(
            'keydown.enter',
            lambda: iniciar_sesion()
        )


@ui.page('/')
def main_page():
    usuario_id = nicegui_app.storage.user.get('usuario_id')

    if not usuario_id:
        ui.navigate.to('/login')
        return

    with Session(engine) as session:
        usuario = session.exec(
            select(Usuario).where(Usuario.id == usuario_id)
        ).first()

        usuario_valido = (
            usuario is not None
            and usuario.activo
            and usuario.rol is not None
            and usuario.rol.activo
        )

        usuario_nombre = usuario.nombre if usuario_valido else None

    if not usuario_valido:
        nicegui_app.storage.user.clear()
        ui.navigate.to('/login')
        return

    def cerrar_sesion():
        nicegui_app.storage.user.clear()
        ui.navigate.to('/login')

    filtro_texto = {'val': ''}
    version_cliente_tablero = {'ultima_vista': None}
    version_cliente_metrics = {'ultima_vista': None}

    tab_panels, tab_kanban, tab_handheld, tab_metrics, tab_asignaciones = crear_layout(
        usuario_nombre=usuario_nombre,
        cerrar_sesion=cerrar_sesion,
        usuario_rol=usuario.rol.codigo,
    )

    with tab_panels:
        crear_tablero(
            tab_kanban=tab_kanban,
            filtro_texto=filtro_texto,
            version_cliente_tablero=version_cliente_tablero,
            estado_global=estado_global,
            orden_service=orden_service,
            orden_repository=orden_repository,
            notificar_cambio_global=notificar_cambio_global,
            estados_config=ESTADOS_CONFIG,
            usuario_id=usuario.id,
            usuario_rol=usuario.rol.codigo,
        )

        crear_handheld(
            tab_handheld=tab_handheld,
            orden_service=orden_service,
            orden_repository=orden_repository,
            notificar_cambio_global=notificar_cambio_global,
            estados_config=ESTADOS_CONFIG,
        )

        crear_dashboard(
            tab_metrics=tab_metrics,
            version_cliente_metrics=version_cliente_metrics,
            estado_global=estado_global,
            dashboard_service=dashboard_service,
            orden_repository=orden_repository,
            estados_config=ESTADOS_CONFIG,
        )


        if tab_asignaciones is not None:
            crear_asignaciones(
                tab_asignaciones=tab_asignaciones,
                usuario_actual_id=usuario.id,
            )



ui.run_with(
    app,
    storage_secret='secreto_ordenes_venta_2026'
)

if __name__ in {"__main__", "__mp_main__"}:
    import uvicorn
    uvicorn.run("app.main:app", host="172.16.31.105", port=8072, reload=True)
