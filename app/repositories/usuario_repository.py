from sqlmodel import Session, select

from app.models.usuario import Usuario


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
    
    def crear(
        self,
        session: Session,
        usuario: Usuario,
    ) -> Usuario:

        session.add(usuario)
        session.flush()
        session.refresh(usuario)

        return usuario