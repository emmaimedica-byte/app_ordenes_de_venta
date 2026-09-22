from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Usuario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    username: str = Field(
        index=True,
        unique=True,
        nullable=False,
    )

    nombre: str = Field(nullable=False)

    password_hash: str = Field(nullable=False)

    rol_id: int = Field(
        foreign_key="rol.id",
        nullable=False,
    )

    departamento: str = Field(nullable=False)

    creado_por_id: Optional[int] = Field(
        default=None,
        foreign_key="usuario.id",
    )

    activo: bool = Field(default=True)

    creado_en: datetime = Field(
        default_factory=datetime.now
    )

    actualizado_en: datetime = Field(
        default_factory=datetime.now
    )