
from datetime import datetime
from pathlib import Path
from uuid import uuid4
import logging

from PIL import Image, UnidentifiedImageError
from sqlmodel import Session

from app.models.asignacion import TipoAsignacion
from app.models.imagen import ImagenOrden
from app.models.orden import OrdenVenta
from app.models.usuario import Usuario
from app.repositories.imagen_repository import ImagenRepository
from app.repositories.orden_repository import OrdenRepository
from app.services.authorization_service import AuthorizationService


logger = logging.getLogger(__name__)

DIRECTORIO_IMAGENES = (
    Path(__file__).resolve().parents[2]
    / "uploads"
    / "ordenes"
)

TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024

FORMATOS_PERMITIDOS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}


class ImagenService:

    def __init__(
        self,
        imagen_repository: ImagenRepository | None = None,
        orden_repository: OrdenRepository | None = None,
        authorization_service: AuthorizationService | None = None,
    ):
        self.imagen_repository = (
            imagen_repository or ImagenRepository()
        )
        self.orden_repository = (
            orden_repository or OrdenRepository()
        )
        self.authorization_service = (
            authorization_service or AuthorizationService()
        )

    def _validar_acceso(
        self,
        session: Session,
        orden_id: int,
        usuario_id: int,
        permiso_codigo: str,
    ) -> OrdenVenta:
        orden = self.orden_repository.obtener_por_id(
            session,
            orden_id,
        )

        if orden is None:
            raise ValueError("La orden no existe")

        usuario = session.get(Usuario, usuario_id)

        if (
            usuario is None
            or not usuario.activo
            or usuario.rol is None
            or not usuario.rol.activo
        ):
            raise PermissionError(
                "El usuario no existe o está inactivo"
            )

        if not self.authorization_service.tiene_permiso(
            session,
            usuario,
            permiso_codigo,
        ):
            raise PermissionError(
                "El usuario no tiene permiso para realizar esta operación"
            )

        if usuario.rol.codigo == "OPERADOR":
            if not self.authorization_service.tiene_asignacion(
                session,
                usuario,
                orden.id,
                TipoAsignacion.OPERADOR,
            ):
                raise PermissionError(
                    "El operador no tiene asignada esta orden"
                )

        elif usuario.rol.codigo == "CHOFER":
            if not self.authorization_service.tiene_asignacion(
                session,
                usuario,
                orden.id,
                TipoAsignacion.CHOFER,
            ):
                raise PermissionError(
                    "El chofer no tiene asignada esta orden"
                )

        return orden

    def obtener_por_orden(
        self,
        session: Session,
        orden_id: int,
        usuario_id: int,
    ) -> list[ImagenOrden]:
        self._validar_acceso(
            session,
            orden_id,
            usuario_id,
            "orden.ver",
        )

        return self.imagen_repository.obtener_por_orden(
            session,
            orden_id,
        )

    def guardar_imagen(
        self,
        session: Session,
        orden_id: int,
        usuario_id: int,
        contenido: bytes,
        nombre_original: str,
        descripcion: str | None = None,
    ) -> ImagenOrden:
        self._validar_acceso(
            session,
            orden_id,
            usuario_id,
            "orden.comentar",
        )

        if not isinstance(contenido, bytes) or not contenido:
            raise ValueError("El archivo está vacío o no es válido")

        if len(contenido) > TAMANO_MAXIMO_BYTES:
            raise ValueError(
                "La imagen supera el límite permitido de 10 MB"
            )

        if not nombre_original or not nombre_original.strip():
            raise ValueError("El archivo no tiene un nombre válido")

        try:
            import io

            with Image.open(io.BytesIO(contenido)) as imagen:
                formato = imagen.format

                if formato not in FORMATOS_PERMITIDOS:
                    raise ValueError(
                        "Formato no permitido. Usa JPG, PNG o WebP"
                    )

                imagen.verify()

        except (UnidentifiedImageError, OSError) as error:
            raise ValueError(
                "El archivo no contiene una imagen válida"
            ) from error

        extension = FORMATOS_PERMITIDOS[formato]
        nombre_seguro = f"{uuid4().hex}{extension}"

        directorio_orden = (
            DIRECTORIO_IMAGENES / str(orden_id)
        ).resolve()

        directorio_base = DIRECTORIO_IMAGENES.resolve()

        if not directorio_orden.is_relative_to(directorio_base):
            raise ValueError("La ruta de almacenamiento no es válida")

        ruta_archivo = directorio_orden / nombre_seguro
        ruta_relativa = ruta_archivo.relative_to(
            directorio_base.parent
        ).as_posix()

        descripcion_limpia = (
            descripcion.strip() if descripcion else None
        )

        if descripcion_limpia and len(descripcion_limpia) > 500:
            raise ValueError(
                "La descripción no puede superar 500 caracteres"
            )

        directorio_orden.mkdir(parents=True, exist_ok=True)

        try:
            with ruta_archivo.open("xb") as archivo:
                archivo.write(contenido)

            registro = ImagenOrden(
                orden_id=orden_id,
                nombre_archivo=nombre_seguro,
                ruta_archivo=ruta_relativa,
                usuario_id=usuario_id,
                descripcion=descripcion_limpia,
                fecha_registro=datetime.now(),
            )

            registro = self.imagen_repository.crear(
                session,
                registro,
            )

            session.commit()
            session.refresh(registro)

            return registro

        except Exception:
            session.rollback()

            try:
                ruta_archivo.unlink(missing_ok=True)
            except OSError:
                logger.exception(
                    "No se pudo limpiar el archivo tras un error"
                )

            raise
