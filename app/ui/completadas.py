from nicegui import ui
from sqlmodel import Session

from app.database import engine
from app.repositories.orden_repository import OrdenRepository
from app.models.usuario import Usuario
from app.models.asignacion import TipoAsignacion
from app.repositories.asignacion_repository import AsignacionRepository


orden_repository = OrdenRepository()
asignacion_repository = AsignacionRepository()


def crear_completadas(
    tab_completadas,
    orden_service,
    orden_repository,
    usuario_id,
):
    
    historial_abierto = {"valor": False}
    
    def ver_historial_modal(orden_id: int):
        try:
            with Session(engine) as session:
                orden = orden_repository.obtener_por_id(
                    session,
                    orden_id,
                )

                if orden is None:
                    ui.notify(
                        "No se encontró la orden de venta.",
                        type="warning",
                    )
                    return

                historial = orden_service.obtener_historial(
                    session,
                    orden_id,
                    usuario_id,
                )

                historial_abierto["valor"] = True

                with ui.dialog() as dialog, ui.card().classes(
                    "w-full max-w-lg p-6"
                ):
                    ui.label(
                        f"📜 Trazabilidad de {orden.numero_ov}"
                    ).classes("text-xl font-bold")

                    ui.label(f"Cliente: {orden.cliente}")

                    with ui.column().classes(
                        "w-full gap-3 max-h-80 overflow-y-auto"
                    ):
                        if not historial:
                            ui.label(
                                "Esta orden no tiene movimientos registrados."
                            ).classes("text-gray-500")

                        for item in historial:
                            with ui.card().classes("w-full bg-gray-50"):
                                ui.label(
                                    item.estado_nuevo or "Estado no disponible"
                                ).classes("font-bold")

                                ui.label(
                                    item.fecha_registro.strftime(
                                        "%d/%m/%Y %H:%M"
                                    )
                                    if item.fecha_registro
                                    else "Fecha no disponible"
                                ).classes("text-sm text-gray-500")

                                if item.estado_anterior:
                                    ui.label(
                                        f"Estado anterior: {item.estado_anterior}"
                                    )

                                
                                usuario_historial = (
                                    session.get(
                                        Usuario,
                                        item.usuario_operador_id,
                                    )
                                    if item.usuario_operador_id is not None
                                    else None
                                )

                                nombre_operador = (
                                    usuario_historial.nombre
                                    if usuario_historial
                                    else "Usuario no disponible"
                                )

                                ui.label(
                                    f"👤 {nombre_operador}"
                                ).classes("text-sm text-gray-600")

                                if item.observaciones:
                                    ui.label(
                                        f"Observaciones: {item.observaciones}"
                                    ).classes("text-sm text-gray-700")


                    ui.button(
                        "Cerrar",
                        on_click=lambda: (
                            historial_abierto.update({"valor": False}),
                            dialog.close(),
                        ),
                    )

                dialog.open()

                dialog.on(
                    "hide",
                    lambda: historial_abierto.update({"valor": False}),
                )

        except PermissionError as error:
            ui.notify(str(error), type="negative")

        except ValueError as error:
            ui.notify(str(error), type="warning")

    
    @ui.refreshable
    def tabla_completadas():
        with Session(engine) as session:
            ordenes = orden_repository.obtener_todas(session)

            ordenes = [
                orden
                for orden in ordenes
                if orden.completadas
            ]

            filas = []

            for orden in ordenes:
                asignaciones = (
                    asignacion_repository.obtener_todas_por_orden(
                        session,
                        orden.id,
                    )
                )

                ultimos_responsables = {}

                for asignacion in asignaciones:
                    tipo = asignacion.tipo_asignacion

                    asignacion_actual = ultimos_responsables.get(tipo)

                    if (
                        asignacion_actual is None
                        or asignacion.asignado_en
                        > asignacion_actual.asignado_en
                    ):
                        ultimos_responsables[tipo] = asignacion

                responsables = []

                for tipo, etiqueta in (
                    (TipoAsignacion.OPERADOR, "Operador"),
                    (TipoAsignacion.CHOFER, "Chofer"),
                ):
                    asignacion = ultimos_responsables.get(tipo)

                    if asignacion is None:
                        continue

                    usuario_asignado = session.get(
                        Usuario,
                        asignacion.usuario_id,
                    )

                    if usuario_asignado is not None:
                        responsables.append(
                            f"{etiqueta}: {usuario_asignado.nombre}"
                        )


                filas.append({
                    "id": orden.id,
                    "numero_ov": orden.numero_ov,
                    "cliente": orden.cliente,
                    "estado": orden.estado.value,
                    "asignados": (
                        " · ".join(responsables)
                        if responsables
                        else "Sin asignaciones registradas"
                    ),
                    "creado_en": (
                        orden.creado_en.strftime("%d/%m/%Y %H:%M")
                        if orden.creado_en
                        else ""
                    ),
                    "actualizado_en": (
                        orden.actualizado_en.strftime("%d/%m/%Y %H:%M")
                        if orden.actualizado_en
                        else ""
                    ),
                })

        columnas = [
            {
                "name": "numero_ov",
                "label": "Número de OV",
                "field": "numero_ov",
                "align": "left",
                "sortable": True,
            },
            {
                "name": "cliente",
                "label": "Cliente",
                "field": "cliente",
                "align": "left",
                "sortable": True,
            },
            {
                "name": "historial",
                "label": "Historial",
                "field": "historial",
                "align": "center",
            },
            {
                "name": "asignados",
                "label": "Asignados",
                "field": "asignados",
                "align": "left",
                "style": "max-width: 260px; white-space: normal; overflow-wrap: anywhere;",
            },
            {
                "name": "creado_en",
                "label": "Fecha de registro",
                "field": "creado_en",
                "align": "left",
                "sortable": True,
            },
            {
                "name": "actualizado_en",
                "label": "Última actualización",
                "field": "actualizado_en",
                "align": "left",
                "sortable": True,
            },
        ]

        busqueda = (
            busqueda_completadas.value or ""
        ).strip().casefold()

        if busqueda:
            filas = [
                fila
                for fila in filas
                if any(
                    busqueda in str(fila[campo]).casefold()
                    for campo in (
                        "numero_ov",
                        "cliente",
                        "estado",
                        "asignados",
                    )
                )
            ]

        ui.label(
            f"Órdenes completadas: {len(filas)}"
        ).classes("text-lg font-bold text-green-800")

        
        tabla = ui.table(
            columns=columnas,
            rows=filas,
            row_key="numero_ov",
        ).classes("w-full")

        tabla.add_slot(
            "body-cell-historial",
            """
            <q-td :props="props">
                <q-btn
                    flat
                    dense
                    color="primary"
                    label="Ver"
                    @click="$parent.$emit('ver_historial', props.row)"
                />
            </q-td>
            """,
        )

        tabla.on(
            "ver_historial",
            lambda evento: ver_historial_modal(
                int(evento.args["id"])
            ),
        )



    with ui.tab_panel(tab_completadas):
        ui.label(
            "Historial de órdenes completadas"
        ).classes("text-2xl font-bold text-blue-900")

        ui.label(
            "Consulta las órdenes que fueron marcadas como completadas."
        ).classes("text-gray-600 mb-2")

        busqueda_completadas = ui.input(
            "Buscar por OV, cliente o etapa",
            placeholder="Escribe para filtrar...",
        ).classes("w-full max-w-md")

        busqueda_completadas.on(
            "update:model-value",
            lambda: tabla_completadas.refresh(),
        )

        tabla_completadas()

        ui.timer(
            3.0,
            lambda: (
                None
                if historial_abierto["valor"]
                else tabla_completadas.refresh()
            ),
        )
