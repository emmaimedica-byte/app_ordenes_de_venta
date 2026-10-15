
from nicegui import ui, run
from sqlmodel import Session, select

from app.database import engine
from app.models.asignacion import AsignacionOrden, TipoAsignacion
from app.models.orden import OrdenVenta
from app.models.usuario import Usuario
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.orden_repository import OrdenRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.asignacion_service import AsignacionService

def crear_asignaciones(tab_asignaciones, usuario_actual_id):
    asignacion_repository = AsignacionRepository()
    orden_repository = OrdenRepository()
    usuario_repository = UsuarioRepository()

    asignacion_service = AsignacionService(
        asignacion_repository=asignacion_repository,
        orden_repository=orden_repository,
    )

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


            def asignar():
                if not orden_select.value:
                    ui.notify(
                        'Selecciona una orden de venta.',
                        type='warning',
                    )
                    return

                if not usuario_select.value:
                    ui.notify(
                        'Selecciona un usuario.',
                        type='warning',
                    )
                    return


                try:
                    with Session(engine) as session:
                        try:
                            asignacion_service.asignar_usuario(
                                session=session,
                                orden_id=orden_select.value,
                                usuario_id=usuario_select.value,
                                tipo_asignacion=TipoAsignacion(
                                    tipo_select.value
                                ),
                                asignado_por_id=usuario_actual_id,
                            )
                            session.commit()
                        except Exception:
                            session.rollback()
                            raise

                    ui.notify(
                        'Asignación creada correctamente.',
                        type='positive',
                    )
                    ui.navigate.reload()

                except PermissionError as error:
                    ui.notify(str(error), type='negative')
                except ValueError as error:
                    ui.notify(str(error), type='warning')
                except Exception as error:
                    ui.notify(
                        f'No se pudo crear la asignación: {error}',
                        type='negative',
                    )


            ui.button(
                'Asignar',
                on_click=asignar,
                icon='person_add',
            ).classes('w-full')



        with ui.card().classes('w-full'):
            ui.label('Asignaciones activas').classes(
                'text-lg font-semibold'
            )

            tabla_asignaciones = ui.table(
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
                        'name': 'etapa_asignada',
                        'label': 'Etapa asignada',
                        'field': 'etapa_asignada',
                        'align': 'left',
                    },
                    {
                        'name': 'etapa_actual',
                        'label': 'Etapa actual',
                        'field': 'etapa_actual',
                        'align': 'left',
                    },
                ],
                rows=[],
                row_key='id',
            ).classes('w-full')

            def actualizar_tabla_asignaciones():
                with Session(engine) as session:
                    asignaciones_actuales = session.exec(
                        select(AsignacionOrden).where(
                            AsignacionOrden.activa == True
                        )
                    ).all()

                    filas_actualizadas = []

                    for asignacion in asignaciones_actuales:
                        orden = session.get(
                            OrdenVenta,
                            asignacion.orden_id,
                        )
                        usuario = session.get(
                            Usuario,
                            asignacion.usuario_id,
                        )

                        filas_actualizadas.append({
                            'id': asignacion.id,
                            'orden': (
                                orden.numero_ov
                                if orden else 'Orden no disponible'
                            ),
                            'cliente': (
                                orden.cliente if orden else ''
                            ),
                            'tipo': asignacion.tipo_asignacion.value,
                            'usuario': (
                                usuario.nombre
                                if usuario else 'Usuario no disponible'
                            ),
                            'etapa_asignada': (
                                asignacion.etapa_asignacion.value
                            ),
                            'etapa_actual': (
                                orden.estado.value
                                if orden else 'Orden no disponible'
                            ),
                        })

                tabla_asignaciones.rows = filas_actualizadas
                tabla_asignaciones.update()

            actualizar_tabla_asignaciones()
            ui.timer(5.0, actualizar_tabla_asignaciones)
