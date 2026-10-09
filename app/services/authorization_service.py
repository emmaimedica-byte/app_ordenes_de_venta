from sqlmodel import Session

from app.models.asignacion import TipoAsignacion
from app.models.orden import EstadoOrden, OrdenVenta
from app.models.usuario import Usuario
from app.repositories.asignacion_repository import AsignacionRepository
from app.repositories.permiso_repository import PermisoRepository
from app.repositories.rol_etapa_repository import RolEtapaRepository



class AuthorizationService:

    def __init__(
        self,
        permiso_repository: PermisoRepository | None = None,
        rol_etapa_repository: RolEtapaRepository | None = None,
        asignacion_repository: AsignacionRepository | None = None,
    ):
        self.permiso_repository = (
            permiso_repository or PermisoRepository()
        )
        self.rol_etapa_repository = (
            rol_etapa_repository or RolEtapaRepository()
        )
        self.asignacion_repository = (
            asignacion_repository or AsignacionRepository()
        )

    def tiene_permiso(
        self,
        session: Session,
        usuario: Usuario,
        permiso_codigo: str,
    ) -> bool:

        return self.permiso_repository.tiene_permiso(
            session,
            usuario.rol_id,
            permiso_codigo,
        )

    def puede_operar_etapa(
        self,
        session: Session,
        usuario: Usuario,
        estado: EstadoOrden,
    ) -> bool:

        return self.rol_etapa_repository.puede_operar_etapa(
            session,
            usuario.rol_id,
            estado,
        )

    def tiene_asignacion(
        self,
        session: Session,
        usuario: Usuario,
        orden_id: int,
        tipo_asignacion: TipoAsignacion,
    ) -> bool:

        return self.asignacion_repository.tiene_asignacion(
            session,
            usuario.id,
            orden_id,
            tipo_asignacion,
        )
    
    def puede_mover_orden(
        self,
        session: Session,
        usuario: Usuario,
        orden: OrdenVenta,
        estado_destino: EstadoOrden,
    ) -> bool:

        if not usuario.activo:
            return False

        if usuario.rol is None or not usuario.rol.activo:
            return False

        if not self.tiene_permiso(
            session,
            usuario,
            "orden.mover",
        ):
            return False

        if usuario.rol.codigo == "ADMINISTRADOR":
            return True

        if usuario.rol.codigo == "OPERADOR":
            if not self.puede_operar_etapa(
                session,
                usuario,
                orden.estado,
            ):
                return False

            if not self.puede_operar_etapa(
                session,
                usuario,
                estado_destino,
            ):
                return False

            return self.tiene_asignacion(
                session,
                usuario,
                orden.id,
                TipoAsignacion.OPERADOR,
            )

        if usuario.rol.codigo == "CHOFER":
            if orden.estado != EstadoOrden.TRANSPORTE_ENTREGA:
                return False

            if estado_destino != EstadoOrden.ADMINISTRACION_COMPLETADO:
                return False

            return self.tiene_asignacion(
                session,
                usuario,
                orden.id,
                TipoAsignacion.CHOFER,
            )

        return False
    