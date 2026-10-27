from nicegui import ui
from nicegui.events import UploadEventArguments
from sqlmodel import Session
from app.models.usuario import Usuario
from app.database import engine
from app.models.orden import EstadoOrden
from app.models.asignacion import TipoAsignacion


def crear_handheld(
    tab_handheld,
    orden_service,
    orden_repository,
    asignacion_repository,
    notificar_cambio_global,
    estados_config,
    imagen_service,
    usuario_id,
):
    with ui.tab_panel(tab_handheld):
        with ui.column().classes(
            'w-full max-w-md mx-auto items-center p-2 gap-3'
        ):
            ui.label('📱 Módulo Handheld').classes(
                'text-xl font-bold text-blue-900'
            )
            ui.label(
                'Captura la OV, selecciona una etapa si necesitas moverla, '
                'agrega un comentario y adjunta evidencia.'
            ).classes('text-xs text-gray-500 text-center mb-1')

            opciones_etapas = {
                e.value: titulo
                for e, titulo, _, _, _, _, _ in estados_config
            }

            select_etapa = ui.select(
                options=opciones_etapas,
                value=None,
                label='Etapa destino (opcional)',
                clearable=True,
            ).classes('w-full text-base')

            with Session(engine) as session:
                usuario_actual = session.get(Usuario, usuario_id)

                nombre_usuario = (
                    usuario_actual.nombre
                    if usuario_actual is not None
                    else 'Usuario no disponible'
                )

                usuario_autorizado = (
                    usuario_actual is not None
                    and usuario_actual.activo
                    and usuario_actual.rol is not None
                    and usuario_actual.rol.activo
                )

                ordenes_asignadas = []

                if (
                    usuario_autorizado
                    and usuario_actual.rol.codigo in ('OPERADOR', 'CHOFER')
                ):
                    tipo_asignacion = (
                        TipoAsignacion.OPERADOR
                        if usuario_actual.rol.codigo == 'OPERADOR'
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

                    todas_ordenes = orden_repository.obtener_todas(session)

                    ordenes_asignadas = [
                        orden
                        for orden in todas_ordenes
                        if (
                            orden.id in ordenes_asignadas_ids
                            and not orden.completadas
                        )
                    ]

            input_operador_hh = ui.input(
                label='Operador / Handheld ID',
                value=nombre_usuario,
            ).classes('w-full').props('outlined dense readonly')

            input_comentario_hh = ui.textarea(
                label='Comentario / Observación (opcional)',
                placeholder='Ej. Caja dañada, faltan piezas, listo para embarque...',
            ).classes('w-full').props('outlined dense rows=2')

            opciones_ordenes = {
                orden.numero_ov: f'{orden.numero_ov} · {orden.cliente}'
                for orden in ordenes_asignadas
            }

            input_escaneo = ui.select(
                options=opciones_ordenes,
                label='📋 Orden de venta asignada',
                value=None,
                clearable=True,
            ).classes('w-full text-xl').props('outlined')

            def actualizar_ordenes_asignadas():
                with Session(engine) as session:
                    usuario_actual = session.get(Usuario, usuario_id)

                    if (
                        usuario_actual is None
                        or not usuario_actual.activo
                        or usuario_actual.rol is None
                        or not usuario_actual.rol.activo
                        or usuario_actual.rol.codigo not in ('OPERADOR', 'CHOFER')
                    ):
                        input_escaneo.options = {}
                        input_escaneo.value = None
                        input_escaneo.update()
                        return

                    tipo_asignacion_actual = (
                        TipoAsignacion.OPERADOR
                        if usuario_actual.rol.codigo == 'OPERADOR'
                        else TipoAsignacion.CHOFER
                    )

                    asignaciones_actuales = (
                        asignacion_repository.obtener_activas_por_usuario(
                            session,
                            usuario_id,
                            tipo_asignacion_actual,
                        )
                    )

                    ids_asignados = {
                        asignacion.orden_id
                        for asignacion in asignaciones_actuales
                    }

                    todas_ordenes_actuales = orden_repository.obtener_todas(session)

                    opciones_actualizadas = {
                        orden.numero_ov: f'{orden.numero_ov} · {orden.cliente}'
                        for orden in todas_ordenes_actuales
                        if orden.id in ids_asignados and not orden.completadas
                    }

                seleccion_actual = input_escaneo.value

                input_escaneo.options = opciones_actualizadas

                if seleccion_actual not in opciones_actualizadas:
                    input_escaneo.value = None

                input_escaneo.update()

            resultado_card = ui.column().classes('w-full')

            ui.timer(
                3.0,
                actualizar_ordenes_asignadas,
            )

            # La imagen permanece en memoria hasta procesar la OV.
            imagen_pendiente = {
                'contenido': None,
                'nombre': None,
            }

            async def preparar_evidencia(e: UploadEventArguments):
                try:
                    contenido = await e.file.read()

                    if not contenido:
                        ui.notify(
                            'El archivo está vacío.',
                            type='negative',
                        )
                        return

                    if len(contenido) > 10 * 1024 * 1024:
                        ui.notify(
                            'La imagen no puede superar los 10 MB.',
                            type='negative',
                        )
                        return

                    imagen_pendiente['contenido'] = contenido
                    imagen_pendiente['nombre'] = e.file.name

                    ui.notify(
                        f'Imagen preparada: {e.file.name}. '
                        'Se guardará al procesar la OV.',
                        type='positive',
                    )

                except Exception:
                    ui.notify(
                        'No fue posible preparar la imagen.',
                        type='negative',
                    )
                    raise

            upload_imagen = ui.upload(
                label='Tomar fotografía o seleccionar imagen',
                auto_upload=True,
                max_file_size=10 * 1024 * 1024,
                on_upload=preparar_evidencia,
            ).props(
                'accept="image/jpeg,image/png,image/webp" capture="environment"'
            ).classes('w-full')

            def limpiar_formulario():
                select_etapa.value = None
                input_comentario_hh.value = ''
                input_escaneo.value = None
                imagen_pendiente['contenido'] = None
                imagen_pendiente['nombre'] = None

                upload_imagen.run_method('reset')
                input_escaneo.run_method('focus')

            def procesar_escaneo():
                codigo = input_escaneo.value

                if not codigo:
                    ui.notify(
                        'Selecciona una OV asignada antes de procesar.',
                        type='warning',
                    )
                    return

                codigo = str(codigo).strip()

                accion_seleccionada = select_etapa.value
                nombre_op = (
                    input_operador_hh.value or ''
                ).strip() or 'Handheld User'
                comentario_txt = (
                    input_comentario_hh.value or ''
                ).strip()

                contenido_imagen = imagen_pendiente['contenido']
                nombre_imagen = imagen_pendiente['nombre']

                # No aceptar un envío vacío que no haga nada.
                if (
                    not accion_seleccionada
                    and not comentario_txt
                    and not contenido_imagen
                ):
                    ui.notify(
                        'Selecciona una etapa, agrega un comentario '
                        'o adjunta una imagen.',
                        type='warning',
                    )
                    return

                try:
                    with Session(engine) as session:
                        orden = orden_repository.obtener_por_numero(
                            session,
                            codigo,
                        )

                        if not orden:
                            resultado_card.clear()
                            with resultado_card:
                                with ui.card().classes(
                                    'w-full p-4 bg-red-100 '
                                    'border-l-8 border-red-500 text-red-900'
                                ):
                                    ui.label(
                                        '❌ ORDEN NO ENCONTRADA'
                                    ).classes('font-bold text-lg')
                                    ui.label(
                                        f'No se encontró la OV "{codigo}".'
                                    ).classes('text-sm')

                            ui.notify(
                                f'La OV {codigo} no existe.',
                                type='negative',
                            )
                            return

                        estado_previo = orden.estado.value
                        se_movio = False

                        # 1. Mover de etapa solo si se seleccionó una.
                        if accion_seleccionada:
                            observaciones = 'Procesamiento por Handheld.'

                            if comentario_txt:
                                observaciones += (
                                    f' Nota: {comentario_txt}'
                                )

                            orden = orden_service.mover_orden_a_estado(
                                session,
                                orden.id,
                                EstadoOrden(accion_seleccionada),
                                usuario_id,
                                operador=nombre_op,
                                observaciones=observaciones,
                            )
                            se_movio = True

                        # 2. Sin movimiento, registrar el comentario
                        # si existe. Si hay movimiento, ya se incluye
                        # en las observaciones del movimiento.
                        elif comentario_txt:
                            orden_service.agregar_comentario(
                                session,
                                orden.id,
                                usuario_id,
                                comentario_txt,
                                operador=nombre_op,
                            )

                        # 3. Guardar la imagen al procesar la orden.
                        if contenido_imagen:
                            imagen_service.guardar_imagen(
                                session=session,
                                orden_id=orden.id,
                                usuario_id=usuario_id,
                                contenido=contenido_imagen,
                                nombre_original=nombre_imagen,
                                descripcion=comentario_txt or None,
                            )

                        orden_id = orden.id
                        numero_ov = orden.numero_ov
                        cliente = orden.cliente
                        estado_actual = orden.estado.value

                    # La limpieza ocurre solamente si el proceso
                    # anterior terminó sin lanzar una excepción.
                    resultado_card.clear()

                    with resultado_card:
                        with ui.card().classes(
                            'w-full p-4 bg-green-100 '
                            'border-l-8 border-green-500 text-green-900'
                        ):
                            ui.label('✅ ORDEN PROCESADA').classes(
                                'font-bold text-lg'
                            )
                            ui.label(
                                f'OV: {numero_ov} | Cliente: {cliente}'
                            ).classes('text-sm font-semibold')

                            if se_movio:
                                ui.label(
                                    f'Etapa: {estado_previo} → {estado_actual}'
                                ).classes('text-sm')

                            if comentario_txt:
                                ui.label(
                                    f'Comentario: {comentario_txt}'
                                ).classes('text-sm')

                            if contenido_imagen:
                                ui.label(
                                    '📷 Evidencia adjuntada correctamente.'
                                ).classes('text-sm')

                    notificar_cambio_global(orden_id)

                    ui.notify(
                        f'OV {numero_ov} procesada correctamente.',
                        type='positive',
                    )

                    limpiar_formulario()

                except (ValueError, PermissionError) as error:
                    ui.notify(str(error), type='negative')

                except Exception:
                    ui.notify(
                        'Ocurrió un error al procesar la OV. '
                        'Revisa la consola del servidor.',
                        type='negative',
                    )
                    raise

            ui.button(
                'Escanear orden',
                icon='qr_code',
                on_click=procesar_escaneo,
            ).classes(
                'w-full bg-green-600 text-white font-bold '
                'py-3 text-lg shadow-md'
            )