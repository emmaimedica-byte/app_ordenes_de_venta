from sqlmodel import Session

from app.models.usuario import Departamento, Usuario
from app.repositories.rol_repository import RolRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.auth_service import AuthService
from app.services.authorization_service import AuthorizationService
from app.repositories.asignacion_repository import AsignacionRepository
from datetime import datetime


class UsuarioService:
    def __init__(
        self,
        usuario_repository: UsuarioRepository | None = None,
        rol_repository: RolRepository | None = None,
        auth_service: AuthService | None = None,
        authorization_service: AuthorizationService | None = None,
        asignacion_repository: AsignacionRepository | None = None,
    ):
        self.usuario_repository = usuario_repository or UsuarioRepository()
        self.rol_repository = rol_repository or RolRepository()
        self.auth_service = auth_service or AuthService()
        self.authorization_service = (
            authorization_service or AuthorizationService()
        )
        self.asignacion_repository = (
            asignacion_repository or AsignacionRepository()
        )

    def _validar_permiso_administrativo(
        self,
        session: Session,
        administrador_id: int,
        permiso_codigo: str,
    ) -> Usuario:
        administrador = session.get(Usuario, administrador_id)

        if (
            administrador is None
            or not administrador.activo
            or administrador.rol is None
            or not administrador.rol.activo
        ):
            raise PermissionError(
                "El usuario administrador no existe o está inactivo."
            )

        if not self.authorization_service.tiene_permiso(
            session,
            administrador,
            permiso_codigo,
        ):
            raise PermissionError(
                f"No tienes permiso para realizar esta operación: "
                f"{permiso_codigo}."
            )

        return administrador

    def _crear_usuario(
        self,
        session: Session,
        username: str,
        nombre: str,
        password: str,
        rol_codigo: str,
        departamento: Departamento,
        creado_por_id: int | None,
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

        rol = self.rol_repository.obtener_por_codigo(session, rol_codigo)

        if rol is None:
            raise ValueError("El rol indicado no existe.")

        if not rol.activo:
            raise ValueError("El rol indicado está inactivo.")

        usuario = Usuario(
            username=username_normalizado,
            nombre=nombre_normalizado,
            password_hash=self.auth_service.generar_hash_password(password),
            rol_id=rol.id,
            departamento=departamento,
            creado_por_id=creado_por_id,
            activo=True,
        )

        self.usuario_repository.crear(session, usuario)
        return usuario
    
    def listar_usuarios(
        self,
        session: Session,
        administrador_id: int,
    ) -> list[Usuario]:
        self._validar_permiso_administrativo(
            session=session,
            administrador_id=administrador_id,
            permiso_codigo="usuario.ver",
        )

        return self.usuario_repository.listar_todos(session)
    
    def listar_roles_activos(
        self,
        session: Session,
        administrador_id: int,
    ) -> list:
        self._validar_permiso_administrativo(
            session=session,
            administrador_id=administrador_id,
            permiso_codigo="usuario.crear",
        )

        return self.rol_repository.listar_activos(session)

    def crear_usuario(
        self,
        session: Session,
        username: str,
        nombre: str,
        password: str,
        rol_codigo: str,
        departamento: Departamento,
        administrador_id: int,
    ) -> Usuario:
        self._validar_permiso_administrativo(
            session=session,
            administrador_id=administrador_id,
            permiso_codigo="usuario.crear",
        )

        return self._crear_usuario(
            session=session,
            username=username,
            nombre=nombre,
            password=password,
            rol_codigo=rol_codigo,
            departamento=departamento,
            creado_por_id=administrador_id,
        )
    
    def editar_usuario(
        self,
        session: Session,
        usuario_id: int,
        nombre: str,
        rol_codigo: str,
        departamento: Departamento,
        administrador_id: int,
    ) -> Usuario:
        self._validar_permiso_administrativo(
            session=session,
            administrador_id=administrador_id,
            permiso_codigo="usuario.editar",
        )

        usuario = self.usuario_repository.obtener_por_id(
            session,
            usuario_id,
        )

        if usuario is None:
            raise ValueError("El usuario indicado no existe.")

        nombre_normalizado = nombre.strip()

        if not nombre_normalizado:
            raise ValueError("El nombre es obligatorio.")

        rol = self.rol_repository.obtener_por_codigo(
            session,
            rol_codigo,
        )

        if rol is None:
            raise ValueError("El rol indicado no existe.")

        if not rol.activo:
            raise ValueError("El rol indicado está inactivo.")
        
        if (
            usuario.activo
            and usuario.rol is not None
            and usuario.rol.codigo == "ADMINISTRADOR"
            and rol.codigo != "ADMINISTRADOR"
        ):
            administradores_activos = (
                self.usuario_repository.obtener_activos_por_rol(
                    session,
                    "ADMINISTRADOR",
                )
            )

            if len(administradores_activos) <= 1:
                raise ValueError(
                    "No puedes cambiar el rol del último "
                    "administrador activo."
                )

        usuario.nombre = nombre_normalizado
        usuario.rol_id = rol.id
        usuario.departamento = departamento

        usuario.actualizado_en = datetime.now()

        return self.usuario_repository.actualizar(
            session,
            usuario,
        )
    
    def cambiar_estado_usuario(
        self,
        session: Session,
        usuario_id: int,
        activo: bool,
        administrador_id: int,
    ) -> Usuario:
        administrador = self._validar_permiso_administrativo(
            session=session,
            administrador_id=administrador_id,
            permiso_codigo="usuario.activar",
        )

        usuario = self.usuario_repository.obtener_por_id(
            session,
            usuario_id,
        )

        if usuario is None:
            raise ValueError("El usuario indicado no existe.")

        if usuario.id == administrador.id and not activo:
            raise ValueError("No puedes desactivar tu propia cuenta.")
        
        if usuario.activo and not activo:
            asignaciones_activas = (
                self.asignacion_repository.obtener_activas_por_usuario(
                    session=session,
                    usuario_id=usuario.id,
                )
            )

            if asignaciones_activas:
                raise ValueError(
                    "No puedes desactivar este usuario porque "
                    "tiene asignaciones activas. Retira sus "
                    "asignaciones antes de desactivarlo."
                )

        if (
            usuario.activo
            and not activo
            and usuario.rol is not None
            and usuario.rol.codigo == "ADMINISTRADOR"
        ):
            administradores_activos = (
                self.usuario_repository.obtener_activos_por_rol(
                    session,
                    "ADMINISTRADOR",
                )
            )

            if len(administradores_activos) <= 1:
                raise ValueError(
                    "No puedes desactivar al último "
                    "administrador activo."
                )

        usuario.activo = activo
        usuario.actualizado_en = datetime.now()

        return self.usuario_repository.actualizar(
            session,
            usuario,
        )

    def crear_usuario_inicial(
        self,
        session: Session,
        username: str,
        nombre: str,
        password: str,
        rol_codigo: str,
        departamento: Departamento,
    ) -> Usuario:
        existe_administrador = self.usuario_repository.obtener_activos_por_rol(
            session,
            "ADMINISTRADOR",
        )

        if existe_administrador:
            raise PermissionError(
                "Ya existe un administrador activo. "
                "Utiliza el alta administrativa."
            )

        return self._crear_usuario(
            session=session,
            username=username,
            nombre=nombre,
            password=password,
            rol_codigo=rol_codigo,
            departamento=departamento,
            creado_por_id=None,
        )
