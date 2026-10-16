from datetime import datetime

from sqlmodel import Session

from app.models.orden import (
    EstadoOrden,
    HistorialOrden,
    OrdenVenta,
)
from app.repositories.orden_repository import OrdenRepository
from app.services.authorization_service import AuthorizationService
from app.models.usuario import Usuario
from app.models.asignacion import TipoAsignacion


ESTADOS_ORDENADOS = [
    EstadoOrden.LOGISTICA,
    EstadoOrden.ALMACEN_SURTIDO,
    EstadoOrden.EMBARQUES_REVISION,
    EstadoOrden.CALIDAD_LIBERACION,
    EstadoOrden.TRANSPORTE_ENTREGA,
    EstadoOrden.ADMINISTRACION_COMPLETADO,
]


class OrdenService:

    def __init__(
        self,
        repository: OrdenRepository,
        authorization_service: AuthorizationService | None = None,
    ):
        self.repository = repository
        self.authorization_service = (
            authorization_service or AuthorizationService()
        )


    def mover_orden(
        self,
        session: Session,
        orden_id: int,
        usuario_id: int,
        mover_adelante: bool = True,
        operador: str = "Operador Tablero",
        observaciones: str | None = None,
    ) -> OrdenVenta:

        orden = self.repository.obtener_por_id(
            session,
            orden_id
        )

        if not orden:
            raise ValueError("La orden no existe")

        indice_actual = ESTADOS_ORDENADOS.index(orden.estado)

        nuevo_indice = (
            indice_actual + 1
            if mover_adelante
            else indice_actual - 1
        )

        if not 0 <= nuevo_indice < len(ESTADOS_ORDENADOS):
            raise ValueError(
                "La orden no puede moverse en esa dirección"
            )

        estado_destino = ESTADOS_ORDENADOS[nuevo_indice]
        usuario = session.get(Usuario, usuario_id)

        if not usuario:
            raise ValueError("El usuario no existe")

        if not self.authorization_service.puede_mover_orden(
            session,
            usuario,
            orden,
            estado_destino,
        ):
            raise PermissionError(
                "El usuario no tiene autorización para mover esta orden"
            )

        estado_anterior = orden.estado.value
        nuevo_estado = ESTADOS_ORDENADOS[nuevo_indice]

        orden.estado = nuevo_estado
        orden.actualizado_en = datetime.now()
        orden.operador_actual_id = usuario.id

        historial = HistorialOrden(
            orden_id=orden.id,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado.value,
            usuario_operador_id=usuario.id,
            observaciones=(
                observaciones
                or (
                    "Avanzó de etapa"
                    if mover_adelante
                    else "Regresó de etapa"
                )
            ),
        )

        self.repository.guardar(session, orden)
        self.repository.agregar_historial(session, historial)

        session.commit()
        session.refresh(orden)

        return orden


    def crear_orden(
        self,
        session: Session,
        usuario_id: int,
        numero_ov: str,
        cliente: str = "Cliente General",
        operador: str = "Admin / Recepción",
    ) -> OrdenVenta:

        usuario = session.get(Usuario, usuario_id)

        if not usuario:
            raise ValueError("El usuario no existe")

        if not usuario.activo:
            raise PermissionError("El usuario está inactivo")

        if not usuario.rol or not usuario.rol.activo:
            raise PermissionError("El usuario no tiene un rol activo")

        if not self.authorization_service.tiene_permiso(
            session,
            usuario,
            "orden.crear",
        ):
            raise PermissionError(
                "El usuario no tiene permiso para crear órdenes"
            )

        numero_ov = numero_ov.strip()

        if not numero_ov:
            raise ValueError("El número de OV no puede estar vacío")

        existente = self.repository.obtener_por_numero(
            session,
            numero_ov
        )

        if existente:
            raise ValueError(
                f"La OV {numero_ov} ya existe"
            )

        nueva_orden = OrdenVenta(
            numero_ov=numero_ov,
            cliente=cliente.strip() or "Cliente General",
        )

        nueva_orden = self.repository.crear(
            session,
            nueva_orden
        )

        historial = HistorialOrden(
            orden_id=nueva_orden.id,
            estado_anterior=None,
            estado_nuevo=nueva_orden.estado.value,
            usuario_operador_id=usuario.id,
            observaciones="Alta de Orden",
        )

        self.repository.agregar_historial(
            session,
            historial
        )

        session.commit()
        session.refresh(nueva_orden)

        return nueva_orden

    def actualizar_orden(
        self,
        session: Session,
        orden_id: int,
        usuario_id: int,
        numero_ov: str,
        cliente: str,
        operador: str = "Admin",
    ) -> OrdenVenta:

        numero_ov = numero_ov.strip()
        cliente = cliente.strip()

        if not numero_ov:
            raise ValueError(
                "El número de OV no puede estar vacío"
            )

        orden = self.repository.obtener_por_id(
            session,
            orden_id
        )

        if not orden:
            raise ValueError(
                "La orden no existe"
            )

        usuario = session.get(Usuario, usuario_id)

        if (
            usuario is None
            or not usuario.activo
            or usuario.rol is None
            or not usuario.rol.activo
            or not self.authorization_service.tiene_permiso(
                session,
                usuario,
                "orden.editar",
            )
        ):
            raise PermissionError(
                "El usuario no tiene autorización para editar esta orden"
            )

        if numero_ov != orden.numero_ov:
            duplicado = self.repository.obtener_por_numero(
                session,
                numero_ov
            )

            if duplicado and duplicado.id != orden.id:
                raise ValueError(
                    "Ese número de OV ya pertenece a otra orden"
                )

        orden.numero_ov = numero_ov
        orden.cliente = cliente or "Cliente General"
        orden.actualizado_en = datetime.now()

        observaciones = (
            f"Edición de datos: "
            f"OV={numero_ov}, Cliente={orden.cliente}"
        )

        historial = HistorialOrden(
            orden_id=orden.id,
            estado_anterior=None,
            estado_nuevo=orden.estado.value,
            usuario_operador_id=usuario.id,
            observaciones=observaciones,
        )

        self.repository.guardar(
            session,
            orden
        )

        self.repository.agregar_historial(
            session,
            historial
        )

        session.commit()
        session.refresh(orden)

        return orden

    def agregar_comentario(
        self,
        session: Session,
        orden_id: int,
        usuario_id: int,
        comentario: str,
        operador: str = "Operador",
    ) -> OrdenVenta:

        comentario = comentario.strip()
        operador = operador.strip() or "Operador"

        if not comentario:
            raise ValueError(
                "El comentario no puede estar vacío"
            )

        orden = self.repository.obtener_por_id(
            session,
            orden_id
        )

        if not orden:
            raise ValueError(
                "La orden no existe"
            )


        usuario = session.get(Usuario, usuario_id)

        if (
            usuario is None
            or not usuario.activo
            or usuario.rol is None
            or not usuario.rol.activo
            or not self.authorization_service.tiene_permiso(
                session,
                usuario,
                "orden.comentar",
            )
        ):
            raise PermissionError(
                "El usuario no tiene autorización para comentar en esta orden"
            )


        if usuario.rol.codigo == "OPERADOR":
            if not self.authorization_service.tiene_asignacion(
                session,
                usuario,
                orden.id,
                TipoAsignacion.OPERADOR,
            ):
                raise PermissionError(
                    "El operador no tiene asignada esta orden"
                )

        elif usuario.rol.codigo == "CHOFER":
            if not self.authorization_service.tiene_asignacion(
                session,
                usuario,
                orden.id,
                TipoAsignacion.CHOFER,
            ):
                raise PermissionError(
                    "El chofer no tiene asignada esta orden"
                )



        historial = HistorialOrden(
            orden_id=orden.id,
            estado_anterior=None,
            estado_nuevo=orden.estado.value,
            usuario_operador_id=usuario.id,
            observaciones=f"Comentario: {comentario}",
        )

        self.repository.agregar_historial(
            session,
            historial
        )

        session.commit()

        return orden

    def obtener_historial(
        self,
        session: Session,
        orden_id: int,
        usuario_id: int,
    ) -> list[HistorialOrden]:

        orden = self.repository.obtener_por_id(
            session,
            orden_id
        )

        if not orden:
            raise ValueError(
                "La orden no existe"
            )


        usuario = session.get(Usuario, usuario_id)

        if (
            usuario is None
            or not usuario.activo
            or usuario.rol is None
            or not usuario.rol.activo
            or not self.authorization_service.tiene_permiso(
                session,
                usuario,
                "orden.ver_historial",
            )
        ):
            raise PermissionError(
                "El usuario no tiene autorización para consultar el historial"
            )

        if usuario.rol.codigo == "OPERADOR":
            if not self.authorization_service.tiene_asignacion(
                session,
                usuario,
                orden.id,
                TipoAsignacion.OPERADOR,
            ):
                raise PermissionError(
                    "El operador no tiene asignada esta orden"
                )

        elif usuario.rol.codigo == "CHOFER":
            if not self.authorization_service.tiene_asignacion(
                session,
                usuario,
                orden.id,
                TipoAsignacion.CHOFER,
            ):
                raise PermissionError(
                    "El chofer no tiene asignada esta orden"
                )


        return self.repository.obtener_historial(
            session,
            orden_id
        )

    def mover_orden_a_estado(
        self,
        session: Session,
        orden_id: int,
        nuevo_estado: EstadoOrden,
        usuario_id: int,
        operador: str = "Handheld_User",
        observaciones: str | None = None,
    ) -> OrdenVenta:

        orden = self.repository.obtener_por_id(
            session,
            orden_id
        )

        if not orden:
            raise ValueError("La orden no existe")

        if orden.estado == nuevo_estado:
            raise ValueError(
                "La orden ya se encuentra en esa etapa"
            )

        usuario = session.get(Usuario, usuario_id)

        if not usuario:
            raise ValueError("El usuario no existe")

        if not self.authorization_service.puede_mover_orden(
            session,
            usuario,
            orden,
            nuevo_estado,
        ):
            raise PermissionError(
                "El usuario no tiene autorización para mover esta orden"
            )

        estado_anterior = orden.estado.value

        orden.estado = nuevo_estado
        orden.actualizado_en = datetime.now()
        orden.operador_actual_id = usuario.id

        historial = HistorialOrden(
            orden_id=orden.id,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado.value,
            usuario_operador_id=usuario.id,
            observaciones=(
                observaciones
                or "Movimiento realizado desde Handheld"
            ),
        )

        self.repository.guardar(
            session,
            orden
        )

        self.repository.agregar_historial(
            session,
            historial
        )

        session.commit()
        session.refresh(orden)

        return orden