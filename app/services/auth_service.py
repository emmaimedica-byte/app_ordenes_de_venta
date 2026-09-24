from pwdlib import PasswordHash
from sqlmodel import Session

from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository


class AuthService:

    def __init__(
        self,
        usuario_repository: UsuarioRepository | None = None
    ):
        self.password_hasher = PasswordHash.recommended()
        self.usuario_repository = (
            usuario_repository or UsuarioRepository()
        )

    def generar_hash_password(
        self,
        password: str
    ) -> str:
        return self.password_hasher.hash(password)

    def verificar_password(
        self,
        password: str,
        password_hash: str
    ) -> bool:
        return self.password_hasher.verify(
            password,
            password_hash
        )

    def autenticar_usuario(
        self,
        session: Session,
        username: str,
        password: str
    ) -> Usuario | None:

        usuario = self.usuario_repository.obtener_por_username(
            session,
            username
        )

        if usuario is None:
            return None

        if not usuario.activo:
            return None

        if usuario.rol is None:
            return None

        if not usuario.rol.activo:
            return None

        if not self.verificar_password(
            password,
            usuario.password_hash
        ):
            return None

        return usuario


