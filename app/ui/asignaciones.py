
from nicegui import ui
from sqlmodel import Session, select

from app.database import engine
from app.models.asignacion import AsignacionOrden, TipoAsignacion
from app.models.orden import OrdenVenta
from app.models.usuario import Usuario
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.orden_repository import OrdenRepository
from app.repositories.usuario_repository import UsuarioRepository


def crear_asignaciones(tab_asignaciones):
    asignacion_repository = AsignacionRepository()
    orden_repository = OrdenRepository()
    usuario_repository = UsuarioRepository()

    with ui.tab_panel(tab_asignaciones):
        ui.label('Administración de Asignaciones').classes(
            'text-2xl font-bold'
        )
        ui.label(
            'Consulta las órdenes y las asignaciones activas de operadores y choferes.'
        ).classes('text-gray-600')

        with Session(engine) as session:
            ordenes = orden_repository.obtener_todas(session)
            operadores = usuario_repository.obtener_activos_por_rol(
                session, 'OPERADOR'
            )
            choferes = usuario_repository.obtener_activos_por_rol(
                session, 'CHOFER'
            )

            opciones_ordenes = {
                orden.id: (
                    f'{orden.numero_ov} | {orden.cliente} | '
                    f'{orden.estado.value}'
                )
                for orden in ordenes
            }
            opciones_operadores = {
                usuario.id: usuario.nombre
                for usuario in operadores
            }
            opciones_choferes = {
                usuario.id: usuario.nombre
                for usuario in choferes
            }

        if not opciones_ordenes:
            ui.label('No hay órdenes registradas.').classes(
                'text-orange-700'
            )

        with ui.card().classes('w-full'):
            ui.label('Nueva asignación').classes(
                'text-lg font-semibold'
            )

            orden_select = ui.select(
                opciones_ordenes,
                label='Orden de venta',
            ).classes('w-full')

            tipo_select = ui.select(
                {
                    TipoAsignacion.OPERADOR.value: 'Operador',
                    TipoAsignacion.CHOFER.value: 'Chofer',
                },
                label='Tipo de asignación',
                value=TipoAsignacion.OPERADOR.value,
            ).classes('w-full')

            usuario_select = ui.select(
                opciones_operadores,
                label='Operador',
            ).classes('w-full')

            def actualizar_usuarios():
                if tipo_select.value == TipoAsignacion.CHOFER.value:
                    usuario_select.options = opciones_choferes
                    usuario_select.label = 'Chofer'
                else:
                    usuario_select.options = opciones_operadores
                    usuario_select.label = 'Operador'

                usuario_select.value = None
                usuario_select.update()

            tipo_select.on_value_change(
                lambda _: actualizar_usuarios()
            )

            ui.label(
                'La asignación se habilitará cuando conectemos las acciones '
                'al servicio de asignaciones.'
            ).classes('text-sm text-gray-500')

        with ui.card().classes('w-full'):
            ui.label('Asignaciones activas').classes(
                'text-lg font-semibold'
            )

            with Session(engine) as session:
                asignaciones = session.exec(
                    select(AsignacionOrden).where(
                        AsignacionOrden.activa == True
                    )
                ).all()

                filas = []

                for asignacion in asignaciones:
                    orden = session.get(
                        OrdenVenta, asignacion.orden_id
                    )
                    usuario = session.get(
                        Usuario, asignacion.usuario_id
                    )

                    filas.append({
                        'orden': (
                            orden.numero_ov
                            if orden else 'Orden no disponible'
                        ),
                        'cliente': (
                            orden.cliente
                            if orden else ''
                        ),
                        'tipo': asignacion.tipo_asignacion.value,
                        'usuario': (
                            usuario.nombre
                            if usuario else 'Usuario no disponible'
                        ),
                        'etapa': asignacion.etapa_asignacion.value,
                    })

            if filas:
                ui.table(
                    columns=[
                        {
                            'name': 'orden',
                            'label': 'Orden',
                            'field': 'orden',
                            'align': 'left',
                        },
                        {
                            'name': 'cliente',
                            'label': 'Cliente',
                            'field': 'cliente',
                            'align': 'left',
                        },
                        {
                            'name': 'tipo',
                            'label': 'Tipo',
                            'field': 'tipo',
                            'align': 'left',
                        },
                        {
                            'name': 'usuario',
                            'label': 'Usuario asignado',
                            'field': 'usuario',
                            'align': 'left',
                        },
                        {
                            'name': 'etapa',
                            'label': 'Etapa asignada',
                            'field': 'etapa',
                            'align': 'left',
                        },
                    ],
                    rows=filas,
                    row_key='orden',
                ).classes('w-full')
            else:
                ui.label(
                    'No hay asignaciones activas.'
                ).classes('text-gray-500')
