from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Rol(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    codigo: str = Field(
        index=True,
        unique=True,
        nullable=False,
    )

    nombre: str = Field(
        unique=True,
        nullable=False,
    )

    descripcion: Optional[str] = Field(default=None)

    activo: bool = Field(default=True)

    creado_en: datetime = Field(
        default_factory=datetime.now
    )

    actualizado_en: datetime = Field(
        default_factory=datetime.now
    )