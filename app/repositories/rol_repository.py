from sqlmodel import Session, select

from app.models.rol import Rol


class RolRepository:
    def obtener_por_codigo(self, session: Session, codigo: str) -> Rol | None:
        codigo_normalizado = codigo.strip().upper()

        return session.exec(
            select(Rol)
            .where(Rol.codigo == codigo_normalizado)
        ).first()
    
    def listar_activos(self, session: Session) -> list[Rol]:
        return session.exec(
            select(Rol)
            .where(Rol.activo == True)
            .order_by(Rol.nombre)
        ).all()