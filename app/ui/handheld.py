from nicegui import ui
from sqlmodel import Session

from app.database import engine
from app.models.orden import EstadoOrden


def crear_handheld(
    tab_handheld,
    orden_service,
    orden_repository,
    notificar_cambio_global,
    estados_config,
):
    with ui.tab_panel(tab_handheld):
        with ui.column().classes('w-full max-w-md mx-auto items-center p-2 gap-3'):

                ui.label('📱 Módulo Handheld').classes('text-xl font-bold text-blue-900')
                ui.label('Escanea una orden para moverla de etapa o registrar observaciones.')\
                    .classes('text-xs text-gray-500 text-center mb-1')

                # Opciones de Etapa
                opciones_etapas = {"SOLO_COMENTARIO": "💬 Solo agregar comentario (Sin mover)"}
                opciones_etapas.update({e.value: titulo for e, titulo, _, _, _, _, _ in estados_config})

                select_etapa = ui.select(
                    options=opciones_etapas,
                    value=EstadoOrden.ALMACEN_SURTIDO.value,
                    label='Acción / Etapa destino:'
                ).classes('w-full text-base')

                input_operador_hh = ui.input(
                    label='Operador / Handheld ID',
                    placeholder='Ej. Operador Handheld #1'
                ).classes('w-full').props('outlined dense')
                input_operador_hh.value = "Handheld Almacén"

                input_comentario_hh = ui.textarea(
                    label='Comentario / Observación (Opcional)',
                    placeholder='Ej: Caja dañada, faltan 2 piezas, listo para embarque...'
                ).classes('w-full').props('outlined dense rows=2')

                input_escaneo = ui.input(
                    label='📷 Escanear Código OV',
                    placeholder='Apunte con el escáner láser...'
                ).classes('w-full text-xl').props('outlined autofocus')

                resultado_card = ui.column().classes('w-full')

                def procesar_escaneo():
                    codigo = input_escaneo.value.strip()
                    if not codigo:
                        return

                    accion_seleccionada = select_etapa.value
                    nombre_op = input_operador_hh.value.strip() or "Handheld User"
                    comentario_txt = input_comentario_hh.value.strip()

                    with Session(engine) as session:
                        orden = orden_repository.obtener_por_numero(
                            session,
                            codigo
                        )

                        resultado_card.clear()
                        with resultado_card:
                            if not orden:
                                ui.card().classes('w-full p-4 bg-red-100 border-l-8 border-red-500 text-red-900 shadow animacion-entrada')
                                ui.label('❌ ORDEN NO ENCONTRADA').classes('font-bold text-lg')
                                ui.label(f'No se encontró la OV "{codigo}". Primero créala en el Tablero General.').classes('text-xs')
                                ui.notify(f'OV {codigo} no existe', type='negative')
                            else:
                                estado_previo = orden.estado.value

                                # CASO 1: SOLO COMENTAR
                                if accion_seleccionada == "SOLO_COMENTARIO":
                                    obs_final = (
                                        f"Comentario Handheld: {comentario_txt}"
                                        if comentario_txt
                                        else "Comentario sin texto"
                                    )

                                    orden_service.agregar_comentario(
                                        session,
                                        orden.id,
                                        obs_final,
                                        operador=nombre_op,
                                    )

                                    ui.card().classes('w-full p-4 bg-blue-100 border-l-8 border-blue-500 text-blue-900 shadow animacion-entrada')
                                    ui.label('💬 ¡COMENTARIO REGISTRADO!').classes('font-bold text-lg')
                                    ui.label(f'OV: {orden.numero_ov} | Etapa actual: {estado_previo}').classes('text-sm font-semibold')
                                    if comentario_txt:
                                        ui.label(f'Nota: "{comentario_txt}"').classes('text-xs italic text-blue-800 mt-1')
                                    ui.notify(f'💬 Comentario guardado en OV {codigo}', type='info')

                                # CASO 2: MOVER DE ETAPA
                                else:
                                    obs_final = f"Escaneo por Handheld."
                                    if comentario_txt:
                                        obs_final += f" Nota: {comentario_txt}"

                                    orden = orden_service.mover_orden_a_estado(
                                        session,
                                        orden.id,
                                        EstadoOrden(accion_seleccionada),
                                        operador=nombre_op,
                                        observaciones=obs_final,
                                    )



                                    ui.card().classes('w-full p-4 bg-green-100 border-l-8 border-green-500 text-green-900 shadow animacion-entrada')
                                    ui.label('✅ ¡MOVIMIENTO REGISTRADO!').classes('font-bold text-lg')
                                    ui.label(f'OV: {orden.numero_ov} | Cliente: {orden.cliente}').classes('text-sm font-semibold')
                                    ui.label(f'De: {estado_previo} ➔ A: {accion_seleccionada}').classes('text-xs font-semibold text-green-800 mt-1')
                                    if comentario_txt:
                                        ui.label(f'Nota agregada: "{comentario_txt}"').classes('text-xs italic text-green-900 mt-1')
                                    ui.notify(f'🚀 OV {codigo} movida a {accion_seleccionada}', type='positive')

                                notificar_cambio_global(orden.id)

                    input_escaneo.value = ''
                    input_comentario_hh.value = ''
                    input_escaneo.run_method('focus')

                input_escaneo.on('keydown.enter', procesar_escaneo)

                ui.button('Procesar Escaneo', icon='qr_code', on_click=procesar_escaneo)\
                    .classes('w-full bg-green-600 text-white font-bold py-3 text-lg shadow-md hover:scale-105 transition-transform')