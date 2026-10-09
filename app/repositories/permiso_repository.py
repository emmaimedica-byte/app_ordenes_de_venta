from sqlmodel import Session, select

from app.models.permiso import Permiso
from app.models.rol_permiso import RolPermiso


class PermisoRepository:

    def tiene_permiso(
        self,
        session: Session,
        rol_id: int,
        permiso_codigo: str,
    ) -> bool:

        permiso_codigo_normalizado = permiso_codigo.strip().lower()

        resultado = session.exec(
            select(RolPermiso)
            .join(Permiso, Permiso.id == RolPermiso.permiso_id)
            .where(
                RolPermiso.rol_id == rol_id,
                RolPermiso.activo == True,
                Permiso.codigo == permiso_codigo_normalizado,
                Permiso.activo == True,
            )
        ).first()

        return resultado is not None
    