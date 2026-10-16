from datetime import datetime

from sqlmodel import Session, select

from app.models.asignacion import AsignacionOrden, TipoAsignacion


class AsignacionRepository:

    def tiene_asignacion(
        self,
        session: Session,
        usuario_id: int,
        orden_id: int,
        tipo_asignacion: TipoAsignacion,
    ) -> bool:
        resultado = session.exec(
            select(AsignacionOrden).where(
                AsignacionOrden.usuario_id == usuario_id,
                AsignacionOrden.orden_id == orden_id,
                AsignacionOrden.tipo_asignacion == tipo_asignacion,
                AsignacionOrden.activa == True,
            )
        ).first()

        return resultado is not None
    
    def tiene_asignacion_activa_por_orden_tipo(
        self,
        session: Session,
        orden_id: int,
        tipo_asignacion: TipoAsignacion,
    ) -> bool:
        resultado = session.exec(
            select(AsignacionOrden).where(
                AsignacionOrden.orden_id == orden_id,
                AsignacionOrden.tipo_asignacion == tipo_asignacion,
                AsignacionOrden.activa == True,
            )
        ).first()

        return resultado is not None

    def obtener_activas_por_orden(
        self,
        session: Session,
        orden_id: int,
    ) -> list[AsignacionOrden]:
        return session.exec(
            select(AsignacionOrden).where(
                AsignacionOrden.orden_id == orden_id,
                AsignacionOrden.activa == True,
            )
        ).all()

    def obtener_activas_por_usuario(
        self,
        session: Session,
        usuario_id: int,
        tipo_asignacion: TipoAsignacion | None = None,
    ) -> list[AsignacionOrden]:
        consulta = select(AsignacionOrden).where(
            AsignacionOrden.usuario_id == usuario_id,
            AsignacionOrden.activa == True,
        )

        if tipo_asignacion is not None:
            consulta = consulta.where(
                AsignacionOrden.tipo_asignacion == tipo_asignacion
            )

        return session.exec(consulta).all()

    def crear(
        self,
        session: Session,
        asignacion: AsignacionOrden,
    ) -> AsignacionOrden:
        session.add(asignacion)
        session.flush()
        session.refresh(asignacion)

        return asignacion

    def desactivar(
        self,
        session: Session,
        asignacion: AsignacionOrden,
    ) -> AsignacionOrden:
        asignacion.activa = False
        asignacion.desasignado_en = datetime.now()

        session.add(asignacion)
        session.flush()
        session.refresh(asignacion)

        return asignacion
