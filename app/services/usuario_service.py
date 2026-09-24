from sqlmodel import Session

from app.models.usuario import Departamento, Usuario
from app.repositories.rol_repository import RolRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.auth_service import AuthService


class UsuarioService:
    def __init__(
        self,
        usuario_repository: UsuarioRepository | None = None,
        rol_repository: RolRepository | None = None,
        auth_service: AuthService | None = None,
    ):
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.rol_repository = rol_repository or RolRepository()
        self.auth_service = auth_service or AuthService()

    def crear_usuario(
        self,
        session: Session,
        username: str,
        nombre: str,
        password: str,
        rol_codigo: str,
        departamento: Departamento,
        creado_por_id: int | None = None,
    ) -> Usuario:

        username_normalizado = username.strip().lower()
        nombre_normalizado = nombre.strip()

        if not username_normalizado:
            raise ValueError("El username es obligatorio.")

        if not nombre_normalizado:
            raise ValueError("El nombre es obligatorio.")

        if not password:
            raise ValueError("La contraseña es obligatoria.")

        usuario_existente = self.usuario_repository.obtener_por_username(
            session,
            username_normalizado,
        )

        if usuario_existente is not None:
            raise ValueError("El username ya existe.")

        rol = self.rol_repository.obtener_por_codigo(
            session,
            rol_codigo,
        )

        if rol is None:
            raise ValueError("El rol indicado no existe.")

        if not rol.activo:
            raise ValueError("El rol indicado está inactivo.")

        password_hash = self.auth_service.generar_hash_password(password)

        usuario = Usuario(
            username=username_normalizado,
            nombre=nombre_normalizado,
            password_hash=password_hash,
            rol_id=rol.id,
            departamento=departamento,
            creado_por_id=creado_por_id,
            activo=True,
        )

        self.usuario_repository.crear(session, usuario)

        return usuario