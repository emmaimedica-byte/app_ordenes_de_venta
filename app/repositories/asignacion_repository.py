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
            select(AsignacionOrden)
            .where(
                AsignacionOrden.usuario_id == usuario_id,
                AsignacionOrden.orden_id == orden_id,
                AsignacionOrden.tipo_asignacion == tipo_asignacion,
                AsignacionOrden.activa == True,
            )
        ).first()

        return resultado is not None
    