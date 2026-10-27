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

            opciones_operadores_actuales = opciones_operadores.copy()
            opciones_choferes_actuales = opciones_choferes.copy()
        
        ordenes_disponibles = {'items': ordenes}

        if not opciones_ordenes:
            ui.label('No hay órdenes registradas.').classes(
                'text-orange-700'
            )

        with ui.card().classes('w-full'):
            ui.label('Nueva asignación').classes(
                'text-lg font-semibold'
            )

            
            orden_seleccionada = {
                'id': None,
                'texto': '',
            }

            etiqueta_orden = ui.label(
                'Ninguna orden seleccionada'
            ).classes('text-sm text-gray-600')

            def seleccionar_orden(orden):
                orden_seleccionada['id'] = orden.id
                orden_seleccionada['texto'] = (
                    f'{orden.numero_ov} | {orden.cliente}'
                )
                etiqueta_orden.text = (
                    f'OV seleccionada: {orden_seleccionada["texto"]}'
                )
                dialog_orden.close()

            
            def actualizar_ordenes_disponibles():
                with Session(engine) as session:
                    ordenes_actualizadas = (
                        orden_repository.obtener_todas(session)
                    )

                    ordenes_filtradas = []

                    for orden in ordenes_actualizadas:
                        # Las órdenes completadas nunca deben aparecer.
                        if orden.completadas:
                            continue

                        # Consultar las asignaciones activas de cada tipo.
                        tiene_operador = (
                            asignacion_repository.tiene_asignacion_activa_por_orden_tipo(
                                session,
                                orden.id,
                                TipoAsignacion.OPERADOR,
                            )
                        )

                        tiene_chofer = (
                            asignacion_repository.tiene_asignacion_activa_por_orden_tipo(
                                session,
                                orden.id,
                                TipoAsignacion.CHOFER,
                            )
                        )

                        # Ocultar solo si ya tiene ambos asignados.
                        if tiene_operador and tiene_chofer:
                            continue

                        ordenes_filtradas.append(orden)

                ordenes_disponibles['items'] = ordenes_filtradas

            def filtrar_ordenes():
                termino = (busqueda_ov.value or '').strip().casefold()
                resultados_ov.clear()

                with resultados_ov:
                    encontradas = [
                        orden
                        for orden in ordenes_disponibles['items']
                        if termino in str(orden.numero_ov).casefold()
                        or termino in str(orden.cliente).casefold()
                    ]

                    if not encontradas:
                        ui.label(
                            'No se encontraron órdenes.'
                        ).classes('text-gray-500 py-3')

                    for orden in encontradas:
                        ui.button(
                            f'{orden.numero_ov} | {orden.cliente}',
                            on_click=lambda o=orden: seleccionar_orden(o),
                        ).props('flat no-caps').classes('w-full justify-start')


            with ui.dialog() as dialog_orden, ui.card().classes(
                'w-full max-w-2xl'
            ):
                ui.label('Buscar orden de venta').classes(
                    'text-xl font-bold'
                )

                busqueda_ov = ui.input(
                    label='Buscar por OV o cliente',
                    placeholder='Escribe el número de OV o el cliente',
                ).classes('w-full')
                
                def limpiar_busqueda_orden():
                    busqueda_ov.value = ''
                    busqueda_ov.update()
                    filtrar_ordenes()

                dialog_orden.on('hide', limpiar_busqueda_orden)


                busqueda_ov.on(
                    'update:model-value',
                    lambda _: filtrar_ordenes(),
                )

                with ui.scroll_area().classes('w-full').style(
                    'max-height: 50vh'
                ):
                    resultados_ov = ui.column().classes('w-full gap-1')

                
                def cerrar_dialogo_orden():
                    busqueda_ov.value = ''
                    busqueda_ov.update()
                    filtrar_ordenes()
                    dialog_orden.close()

                ui.button(
                    'Cerrar',
                    on_click=cerrar_dialogo_orden,
                ).props('flat')


            
            def abrir_busqueda_orden():
                actualizar_ordenes_disponibles()
                filtrar_ordenes()
                dialog_orden.open()

            ui.button(
                'Buscar orden de venta',
                icon='search',
                on_click=abrir_busqueda_orden,
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
                    usuario_select.options = opciones_choferes_actuales
                    usuario_select.label = 'Chofer'
                else:
                    usuario_select.options = opciones_operadores_actuales
                    usuario_select.label = 'Operador'

                usuario_select.value = None
                usuario_select.update()


            def asignar():
                if not orden_seleccionada['id']:
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
                                orden_id=orden_seleccionada['id'],
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

            busqueda_asignaciones = ui.input(
                label='Buscar asignación',
                placeholder='Orden, cliente, usuario, tipo o etapa...',
            ).props('outlined dense clearable').classes('w-full')

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
                    {
                        'name': 'acciones',
                        'label': 'Acciones',
                        'field': 'acciones',
                        'align': 'center',
                    },
                ],
                rows=[],
                row_key='id',
            ).classes('w-full')

            tabla_asignaciones.add_slot(
                'body-cell-acciones',
                r'''
                <q-td :props="props">
                    <q-btn
                        flat
                        round
                        dense
                        color="negative"
                        icon="person_remove"
                        @click="$parent.$emit('desasignar', props.row.id)"
                    >
                        <q-tooltip>Retirar asignación</q-tooltip>
                    </q-btn>
                </q-td>
                ''',
            )

            tabla_asignaciones.on(
                'desasignar',
                lambda evento: desasignar(evento.args),
            )

            async def desasignar(asignacion_id: int):
                respuesta = await ui.run_javascript(
                    "confirm('¿Deseas retirar esta asignación?')",
                    timeout=10.0,
                )

                if not respuesta:
                    return

                try:
                    with Session(engine) as session:
                        try:
                            asignacion_service.desasignar_usuario(
                                session=session,
                                asignacion_id=asignacion_id,
                                administrador_id=usuario_actual_id,
                            )
                            session.commit()
                        except Exception:
                            session.rollback()
                            raise

                    ui.notify(
                        'Asignación retirada correctamente.',
                        type='positive',
                    )
                    actualizar_tabla_asignaciones()

                except PermissionError as error:
                    ui.notify(str(error), type='negative')
                except ValueError as error:
                    ui.notify(str(error), type='warning')
                except Exception as error:
                    ui.notify(
                        f'No se pudo retirar la asignación: {error}',
                        type='negative',
                    )

            
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

                    if usuario is None or not usuario.activo:
                        continue

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
                        'usuario': usuario.nombre,
                        'etapa_asignada': (
                            asignacion.etapa_asignacion.value
                        ),
                        'etapa_actual': (
                            orden.estado.value
                            if orden else 'Orden no disponible'
                        ),
                    })

            termino = (
                busqueda_asignaciones.value or ''
            ).strip().casefold()

            if termino:
                filas_actualizadas = [
                    fila
                    for fila in filas_actualizadas
                    if any(
                        termino in str(fila[campo]).casefold()
                        for campo in (
                            'orden',
                            'cliente',
                            'tipo',
                            'usuario',
                            'etapa_asignada',
                            'etapa_actual',
                        )
                    )
                ]

            tabla_asignaciones.rows = filas_actualizadas
            tabla_asignaciones.update()
            

        def actualizar_selector_usuarios():
            with Session(engine) as session:
                operadores_actuales = (
                    usuario_repository.obtener_activos_por_rol(
                        session,
                        'OPERADOR',
                    )
                )
                choferes_actuales = (
                    usuario_repository.obtener_activos_por_rol(
                        session,
                        'CHOFER',
                    )
                )

                # Actualizar los diccionarios compartidos.
                opciones_operadores_actuales.clear()
                opciones_operadores_actuales.update({
                    usuario.id: usuario.nombre
                    for usuario in operadores_actuales
                })

                opciones_choferes_actuales.clear()
                opciones_choferes_actuales.update({
                    usuario.id: usuario.nombre
                    for usuario in choferes_actuales
                })

            # Mostrar las opciones del tipo seleccionado.
            if tipo_select.value == TipoAsignacion.CHOFER.value:
                opciones_actuales = opciones_choferes_actuales
                usuario_select.label = 'Chofer'
            else:
                opciones_actuales = opciones_operadores_actuales
                usuario_select.label = 'Operador'

            usuario_select.options = opciones_actuales

            # Deseleccionar únicamente si el usuario ya no está disponible.
            if usuario_select.value not in opciones_actuales:
                usuario_select.value = None

            usuario_select.update()

        # Carga inicial y actualización periódica independiente.
        actualizar_tabla_asignaciones()
        actualizar_selector_usuarios()

        busqueda_asignaciones.on_value_change(
            lambda _: actualizar_tabla_asignaciones()
        )

        ui.timer(5.0, actualizar_tabla_asignaciones)
        ui.timer(5.0, actualizar_selector_usuarios)
