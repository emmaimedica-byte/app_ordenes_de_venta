from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ImagenOrden(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    orden_id: int = Field(
        foreign_key="ordenventa.id",
        nullable=False,
        index=True,
    )

    nombre_archivo: str = Field(nullable=False, max_length=255)

    ruta_archivo: str = Field(nullable=False, max_length=500)

    usuario_id: int = Field(
        foreign_key="usuario.id",
        nullable=False,
        index=True,
    )

    descripcion: Optional[str] = Field(default=None, max_length=500)

    fecha_registro: datetime = Field(default_factory=datetime.now)
