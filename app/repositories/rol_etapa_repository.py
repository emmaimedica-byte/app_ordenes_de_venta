from sqlmodel import Session, select

from app.models.rol_etapa import RolEtapa
from app.models.orden import EstadoOrden


class RolEtapaRepository:

    def puede_operar_etapa(
        self,
        session: Session,
        rol_id: int,
        estado: EstadoOrden,
    ) -> bool:

        resultado = session.exec(
            select(RolEtapa)
            .where(
                RolEtapa.rol_id == rol_id,
                RolEtapa.estado == estado,
                RolEtapa.activo == True,
            )
        ).first()

        return resultado is not None
    