from nicegui import ui
from sqlmodel import Session

from app.database import engine
from app.models.orden import EstadoOrden
from app.services.authorization_service import AuthorizationService
from app.models.usuario import Usuario
from app.repositories.asignacion_repository import AsignacionRepository
from app.models.asignacion import TipoAsignacion


def crear_tablero(
    tab_kanban,
    filtro_texto,
    version_cliente_tablero,
    estado_global,
    orden_service,
    orden_repository,
    notificar_cambio_global,
    estados_config,
    usuario_id,
    usuario_rol,
):

    authorization_service = AuthorizationService()
    asignacion_repository = AsignacionRepository()

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
                    try:
                        orden = orden_service.mover_orden(
                            session=session,
                            orden_id=orden_id,
                            usuario_id=usuario_id,
                            mover_adelante=mover_adelante,
                            operador=usuario_rol,
                        )

                        ui.notify(
                            f'🚀 OV {orden.numero_ov} movida a {orden.estado.value}',
                            type='info'
                        )

                        notificar_cambio_global(orden.id)
                        refrescar_tablero()

                    except PermissionError as error:
                        ui.notify(str(error), type='negative')

                    except ValueError as error:
                        ui.notify(str(error), type='warning')


            def crear_nueva_ov():
                num_ov = input_ov.value or ''
                cliente_nombre = input_cliente.value or ''

                if not num_ov.strip():
                    ui.notify(
                        'Ingresa un número de OV válido',
                        type='warning'
                    )
                    return

                with Session(engine) as session:
                    try:
                        usuario = session.get(Usuario, usuario_id)

                        if (
                            usuario is None
                            or not usuario.activo
                            or usuario.rol is None
                            or not usuario.rol.activo
                            or not authorization_service.tiene_permiso(
                                session,
                                usuario,
                                'orden.crear'
                            )
                        ):
                            ui.notify(
                                'No tienes permiso para crear órdenes de venta.',
                                type='negative'
                            )
                            return

                        nueva = orden_service.crear_orden(
                            session=session,
                            usuario_id=usuario.id,
                            numero_ov=num_ov,
                            cliente=cliente_nombre,
                            operador=usuario.rol.codigo,
                        )

                        id_creada = nueva.id

                    except PermissionError as error:
                        ui.notify(
                            str(error),
                            type='negative'
                        )
                        return

                    except ValueError as error:
                        ui.notify(
                            str(error),
                            type='negative'
                        )
                        return

                ui.notify(
                    f'✨ OV {nueva.numero_ov} registrada con éxito',
                    type='positive'
                )

                input_ov.value = ''
                input_cliente.value = ''

                notificar_cambio_global(id_creada)
                refrescar_tablero()

            # MODALES (EDITAR, COMENTAR, HISTORIAL)
            def ver_editar_modal(orden_id: int):
                with Session(engine) as session:
                    orden = orden_repository.obtener_por_id(
                        session,
                        orden_id
                    )
                    if not orden:
                        return

                    with ui.dialog() as dialog, ui.card().classes('w-full max-w-md p-6 animacion-entrada'):
                        ui.label(f'✏️ Editar OV {orden.numero_ov}').classes('text-lg font-bold text-blue-900 mb-2')

                        edit_ov = ui.input('Número de OV', value=orden.numero_ov).classes('w-full').props('outlined dense')
                        edit_cliente = ui.input('Nombre del Cliente', value=orden.cliente).classes('w-full mt-2').props('outlined dense')


                        def guardar_cambios():
                            nuevo_num = edit_ov.value.strip()
                            nuevo_cli = edit_cliente.value.strip()

                            if not nuevo_num:
                                ui.notify(
                                    'El número de OV no puede estar vacío',
                                    type='warning'
                                )
                                return

                            with Session(engine) as s:
                                try:
                                    usuario = s.get(Usuario, usuario_id)

                                    if (
                                        usuario is None
                                        or not usuario.activo
                                        or usuario.rol is None
                                        or not usuario.rol.activo
                                        or not authorization_service.tiene_permiso(
                                            s,
                                            usuario,
                                            'orden.editar'
                                        )
                                    ):
                                        ui.notify(
                                            'No tienes permiso para editar órdenes de venta.',
                                            type='negative'
                                        )
                                        return

                                    orden_actualizada = orden_service.actualizar_orden(
                                        session=s,
                                        orden_id=orden_id,
                                        usuario_id=usuario_id,
                                        numero_ov=nuevo_num,
                                        cliente=nuevo_cli,
                                        operador=usuario.rol.codigo,
                                    )

                                except ValueError as error:
                                    ui.notify(
                                        str(error),
                                        type='negative'
                                    )
                                    return

                            ui.notify(
                                '✅ Orden actualizada correctamente',
                                type='positive'
                            )

                            dialog.close()
                            notificar_cambio_global(orden_actualizada.id)
                            refrescar_tablero()


                        with ui.row().classes('w-full justify-end gap-2 mt-4'):
                            ui.button('Cancelar', on_click=dialog.close).classes('bg-gray-400 text-white')
                            ui.button('Guardar', icon='save', on_click=guardar_cambios).classes('bg-primary text-white font-bold')

                    dialog.open()

            def ver_comentario_modal(orden_id: int):
                with Session(engine) as session:
                    orden = orden_repository.obtener_por_id(
                        session,
                        orden_id
                    )
                    if not orden:
                        return

                    with ui.dialog() as dialog, ui.card().classes('w-full max-w-md p-6 animacion-entrada'):
                        ui.label(f'💬 Agregar Comentario a {orden.numero_ov}').classes('text-lg font-bold text-blue-900 mb-1')
                        ui.label(f'Etapa Actual: {orden.estado.value}').classes('text-xs text-gray-500 mb-2')

                        input_operador = ui.input('Tu Nombre / Usuario', value='Operador').classes('w-full').props('outlined dense')
                        input_comentario = ui.textarea('Escribe tu comentario u observación...').classes('w-full mt-2').props('outlined dense')


                        def guardar_comentario():
                            coment = input_comentario.value.strip()

                            if not coment:
                                ui.notify(
                                    'Escribe un comentario antes de guardar',
                                    type='warning'
                                )
                                return

                            with Session(engine) as s:
                                try:
                                    usuario = s.get(Usuario, usuario_id)

                                    if (
                                        usuario is None
                                        or not usuario.activo
                                        or usuario.rol is None
                                        or not usuario.rol.activo
                                        or not authorization_service.tiene_permiso(
                                            s,
                                            usuario,
                                            'orden.comentar'
                                        )
                                    ):
                                        ui.notify(
                                            'No tienes permiso para comentar órdenes de venta.',
                                            type='negative'
                                        )
                                        return

                                    orden_actualizada = orden_service.agregar_comentario(
                                        session=s,
                                        orden_id=orden_id,
                                        usuario_id=usuario_id,
                                        comentario=coment,
                                        operador=usuario.rol.codigo,
                                    )

                                except ValueError as error:
                                    ui.notify(
                                        str(error),
                                        type='negative'
                                    )
                                    return

                            ui.notify(
                                '💬 Comentario añadido al historial',
                                type='positive'
                            )

                            dialog.close()
                            notificar_cambio_global(orden_actualizada.id)


                        with ui.row().classes('w-full justify-end gap-2 mt-4'):
                            ui.button('Cancelar', on_click=dialog.close).classes('bg-gray-400 text-white')
                            ui.button('Agregar', icon='send', on_click=guardar_comentario).classes('bg-secondary text-white font-bold')

                    dialog.open()

            def ver_historial_modal(orden_id: int):
                with Session(engine) as session:
                    usuario = session.get(Usuario, usuario_id)

                    if (
                        usuario is None
                        or not usuario.activo
                        or usuario.rol is None
                        or not usuario.rol.activo
                        or not authorization_service.tiene_permiso(
                            session,
                            usuario,
                            'orden.ver_historial'
                        )
                    ):
                        ui.notify(
                            'No tienes permiso para consultar el historial.',
                            type='negative'
                        )
                        return

                    orden = orden_repository.obtener_por_id(
                        session,
                        orden_id
                    )

                    if not orden:
                        ui.notify(
                            'No se encontró la orden de venta.',
                            type='warning'
                        )
                        return

                    historial = orden_service.obtener_historial(
                        session,
                        orden_id,
                        usuario_id,
                    )

                    with ui.dialog() as dialog, ui.card().classes(
                        'w-full max-w-lg p-6 animacion-entrada'
                    ):
                        ui.label(
                            f'📜 Trazabilidad de {orden.numero_ov}'
                        ).classes(
                            'text-lg font-bold text-blue-900 mb-1'
                        )

                        ui.label(
                            f'Cliente: {orden.cliente}'
                        ).classes(
                            'text-sm text-gray-600 mb-4'
                        )

                        with ui.column().classes(
                            'w-full gap-3 max-h-80 overflow-y-auto'
                        ):
                            for item in historial:
                                with ui.card().classes(
                                    'w-full p-3 bg-slate-50 border-l-4 '
                                    'border-blue-500 shadow-none'
                                ):
                                    with ui.row().classes(
                                        'justify-between items-center w-full'
                                    ):
                                        ui.label(
                                            f'➡️ {item.estado_nuevo}'
                                        ).classes(
                                            'font-bold text-sm text-slate-800'
                                        )

                                        ui.label(
                                            item.fecha_registro.strftime(
                                                '%d/%m/%Y %H:%M:%S'
                                            )
                                        ).classes(
                                            'text-xs text-gray-400'
                                        )

                                    if item.estado_anterior:
                                        ui.label(
                                            f'Origen: {item.estado_anterior}'
                                        ).classes(
                                            'text-xs text-gray-500'
                                        )

                                    usuario_historial = (
                                        session.get(Usuario, item.usuario_operador_id)
                                        if item.usuario_operador_id is not None
                                        else None
                                    )

                                    nombre_operador = (
                                        usuario_historial.nombre
                                        if usuario_historial
                                        else 'Usuario no disponible'
                                    )

                                    ui.label(
                                        f'👤 {nombre_operador}'
                                    ).classes(
                                        'text-xs text-blue-800 mt-1 font-semibold'
                                    )

                                    if item.observaciones:
                                        ui.label(
                                            f'💬 {item.observaciones}'
                                        ).classes(
                                            'text-xs text-gray-600 italic'
                                        )

                        ui.button(
                            'Cerrar',
                            on_click=dialog.close
                        ).classes(
                            'mt-4 self-end bg-gray-500 text-white'
                        )

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
                    with Session(engine) as session:
                        usuario_actual = session.get(Usuario, usuario_id)

                        mostrar_crear_ov = (
                            usuario_actual is not None
                            and usuario_actual.activo
                            and usuario_actual.rol is not None
                            and usuario_actual.rol.activo
                            and usuario_actual.rol.codigo == 'ADMINISTRADOR'
                        )

                    if mostrar_crear_ov:
                        input_ov = ui.input(
                            placeholder='Ej: OV-1001'
                        ).classes('w-32').props('dense outlined')

                        input_cliente = ui.input(
                            placeholder='Cliente'
                        ).classes('w-44').props('dense outlined')

                        ui.button(
                            'Crear OV',
                            icon='add',
                            on_click=crear_nueva_ov,
                        ).classes('bg-secondary text-white font-bold')



            # Renderizado de Columnas Kanban con Colores Personalizados
            def render_columnas():
                with Session(engine) as session:
                    todas_ordenes = orden_repository.obtener_todas(
                        session
                    )

                    usuario = session.get(Usuario, usuario_id)

                    usuario_autorizado = (
                        usuario is not None
                        and usuario.activo
                        and usuario.rol is not None
                        and usuario.rol.activo
                    )


                    if (
                        usuario_autorizado
                        and usuario.rol.codigo in ('OPERADOR', 'CHOFER')
                    ):
                        tipo_asignacion = (
                            TipoAsignacion.OPERADOR
                            if usuario.rol.codigo == 'OPERADOR'
                            else TipoAsignacion.CHOFER
                        )

                        asignaciones_usuario = (
                            asignacion_repository.obtener_activas_por_usuario(
                                session,
                                usuario_id,
                                tipo_asignacion,
                            )
                        )

                        ordenes_asignadas_ids = {
                            asignacion.orden_id
                            for asignacion in asignaciones_usuario
                        }

                        todas_ordenes = [
                            orden
                            for orden in todas_ordenes
                            if orden.id in ordenes_asignadas_ids
                        ]


                    puede_ver_historial = (
                        usuario_autorizado
                        and authorization_service.tiene_permiso(
                            session, usuario, 'orden.ver_historial'
                        )
                    )

                    puede_comentar = (
                        usuario_autorizado
                        and authorization_service.tiene_permiso(
                            session, usuario, 'orden.comentar'
                        )
                    )

                    puede_editar = (
                        usuario_autorizado
                        and authorization_service.tiene_permiso(
                            session, usuario, 'orden.editar'
                        )
                    )

                    estados_orden = [
                        configuracion[0]
                        for configuracion in estados_config
                    ]

                    puede_avanzar_por_orden = {}
                    puede_retroceder_por_orden = {}

                    for orden in todas_ordenes:
                        indice_estado = estados_orden.index(
                            orden.estado
                        )

                        puede_avanzar_por_orden[orden.id] = (
                            usuario_autorizado
                            and indice_estado < len(estados_orden) - 1
                            and authorization_service.puede_mover_orden(
                                session,
                                usuario,
                                orden,
                                estados_orden[indice_estado + 1],
                            )
                        )

                        puede_retroceder_por_orden[orden.id] = (
                            usuario_autorizado
                            and indice_estado > 0
                            and authorization_service.puede_mover_orden(
                                session,
                                usuario,
                                orden,
                                estados_orden[indice_estado - 1],
                            )
                        )

                if filtro_texto['val']:
                    query = filtro_texto['val']
                    todas_ordenes = [
                        o for o in todas_ordenes
                        if query in (o.numero_ov or '').lower() or query in (o.cliente or '').lower()
                    ]

                with ui.row().classes('w-full overflow-x-auto gap-4 p-2 items-start'):
                    for estado, titulo, icono, color_icon, bg_header, border_card, badge_col in estados_config:
                        ordenes_etapa = [o for o in todas_ordenes if o.estado == estado]

                        # Columna principal con encabezo coloreado
                        with ui.column().classes(f'min-w-[280px] max-w-[320px] bg-slate-100 p-3 rounded-lg border shadow-sm'):
                            with ui.row().classes(f'w-full justify-between items-center mb-3 p-2 rounded {bg_header}'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon(icono).classes(f'text-{color_icon}')
                                    ui.label(titulo).classes('font-bold text-gray-800')
                                ui.badge(str(len(ordenes_etapa)), color=badge_col).classes('rounded-full')

                            if not ordenes_etapa:
                                ui.label('Sin órdenes').classes('text-xs text-gray-400 italic py-4 text-center w-full')
                            else:
                                for orden in ordenes_etapa:
                                    es_recien_movida = (orden.id == estado_global["ultima_ov_movida"])
                                    clase_animacion = "animacion-entrada ring-2 ring-blue-400" if es_recien_movida else ""
                                    iso_fecha = orden.actualizado_en.isoformat()

                                    # Tarjeta con borde izquierdo del color correspondiente a su etapa
                                    with ui.card().classes(f'tarjeta-ov w-full p-3 mb-2 bg-white rounded shadow-xs {border_card} {clase_animacion}'):
                                        with ui.row().classes('justify-between items-center w-full'):
                                            ui.label(orden.numero_ov).classes('font-bold text-blue-900 text-base')

                                            badge_timer = ui.label('calculando...').classes('badge-tiempo text-xs px-2 py-0.5 rounded-full')
                                            badge_timer.props(f'data-iso="{iso_fecha}"')

                                            with ui.row().classes('gap-0 items-center'):
                                                if puede_ver_historial:
                                                    ui.button(
                                                        icon='visibility',
                                                        on_click=lambda o_id=orden.id: ver_historial_modal(o_id)
                                                    ).props(
                                                        'flat round dense color=grey-7'
                                                    ).tooltip('Ver historial')

                                                if puede_comentar:
                                                    ui.button(
                                                        icon='chat_bubble_outline',
                                                        on_click=lambda o_id=orden.id: ver_comentario_modal(o_id)
                                                    ).props(
                                                        'flat round dense color=blue-6'
                                                    ).tooltip('Agregar comentario')

                                                if puede_editar:
                                                    ui.button(
                                                        icon='edit',
                                                        on_click=lambda o_id=orden.id: ver_editar_modal(o_id)
                                                    ).props(
                                                        'flat round dense color=amber-7'
                                                    ).tooltip('Editar orden')

                                        ui.label(f'👤 {orden.cliente}').classes('text-xs text-gray-600 mb-2')

                                        with ui.row().classes(
                                            'w-full justify-between items-center pt-2 border-t border-gray-100'
                                        ):
                                            if puede_retroceder_por_orden[orden.id]:
                                                ui.button(
                                                    icon='arrow_back',
                                                    on_click=lambda o_id=orden.id: cambiar_estado_orden(
                                                        o_id, False
                                                    )
                                                ).props('flat round dense color=grey-7')
                                            else:
                                                ui.element('div')

                                            if puede_avanzar_por_orden[orden.id]:
                                                ui.button(
                                                    icon='arrow_forward',
                                                    on_click=lambda o_id=orden.id: cambiar_estado_orden(
                                                        o_id, True
                                                    )
                                                ).props('flat round dense color=primary')


            contenedor_tablero = ui.column().classes('w-full')
            refrescar_tablero()
