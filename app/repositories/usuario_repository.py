from sqlmodel import Session, select

from app.models.usuario import Usuario
from app.models.rol import Rol


class UsuarioRepository:

    def obtener_por_username(
        self,
        session: Session,
        username: str
    ) -> Usuario | None:
        username_normalizado = username.strip().lower()

        return session.exec(
            select(Usuario)
            .where(Usuario.username == username_normalizado)
        ).first()




    def obtener_activos_por_rol(
        self,
        session: Session,
        codigo_rol: str
    ) -> list[Usuario]:
        return session.exec(
            select(Usuario)
            .join(Usuario.rol)
            .where(
                Usuario.activo == True,
                Rol.codigo == codigo_rol,
                Rol.activo == True,
            )
            .order_by(Usuario.nombre)
        ).all()




    def crear(
        self,
        session: Session,
        usuario: Usuario,
    ) -> Usuario:

        session.add(usuario)
        session.flush()
        session.refresh(usuario)

        return usuario
