from sqlmodel import Session

from app.models.asignacion import (
    AsignacionOrden,
    TipoAsignacion,
)
from app.models.orden import OrdenVenta
from app.models.usuario import Usuario
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.orden_repository import OrdenRepository


class AsignacionService:

    def __init__(
        self,
        asignacion_repository: AsignacionRepository | None = None,
        orden_repository: OrdenRepository | None = None,
    ):
        self.asignacion_repository = (
            asignacion_repository or AsignacionRepository()
        )
        self.orden_repository = orden_repository or OrdenRepository()

    def asignar_usuario(
        self,
        session: Session,
        orden_id: int,
        usuario_id: int,
        tipo_asignacion: TipoAsignacion,
        asignado_por_id: int,
    ) -> AsignacionOrden:
        administrador = session.get(Usuario, asignado_por_id)

        if (
            administrador is None
            or not administrador.activo
            or administrador.rol is None
            or not administrador.rol.activo
            or administrador.rol.codigo != "ADMINISTRADOR"
        ):
            raise PermissionError(
                "Solo un administrador activo puede asignar órdenes."
            )

        orden = self.orden_repository.obtener_por_id(
            session,
            orden_id,
        )

        if orden is None:
            raise ValueError("La orden no existe.")

        usuario = session.get(Usuario, usuario_id)

        if (
            usuario is None
            or not usuario.activo
            or usuario.rol is None
            or not usuario.rol.activo
        ):
            raise ValueError(
                "El usuario asignado no existe o está inactivo."
            )

        roles_permitidos = {
            TipoAsignacion.OPERADOR: "OPERADOR",
            TipoAsignacion.CHOFER: "CHOFER",
        }

        if usuario.rol.codigo != roles_permitidos[tipo_asignacion]:
            raise ValueError(
                "El rol del usuario no corresponde al tipo de asignación."
            )

        if self.asignacion_repository.tiene_asignacion_activa_por_orden_tipo(
            session,
            orden_id,
            tipo_asignacion,
        ):
            raise ValueError(
                f"La orden ya tiene un {tipo_asignacion.value.lower()} asignado."
            )

        asignacion = AsignacionOrden(
            orden_id=orden_id,
            usuario_id=usuario_id,
            tipo_asignacion=tipo_asignacion,
            etapa_asignacion=orden.estado,
            asignado_por_id=asignado_por_id,
            activa=True,
        )

        return self.asignacion_repository.crear(
            session,
            asignacion,
        )

    def desasignar_usuario(
        self,
        session: Session,
        asignacion_id: int,
        administrador_id: int,
    ) -> AsignacionOrden:
        administrador = session.get(Usuario, administrador_id)

        if (
            administrador is None
            or not administrador.activo
            or administrador.rol is None
            or not administrador.rol.activo
            or administrador.rol.codigo != "ADMINISTRADOR"
        ):
            raise PermissionError(
                "Solo un administrador activo puede retirar asignaciones."
            )

        asignacion = session.get(AsignacionOrden, asignacion_id)

        if asignacion is None or not asignacion.activa:
            raise ValueError(
                "La asignación no existe o ya está inactiva."
            )

        return self.asignacion_repository.desactivar(
            session,
            asignacion,
        )
