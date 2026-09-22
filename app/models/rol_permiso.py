from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class RolPermiso(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    rol_id: int = Field(
        foreign_key="rol.id",
        nullable=False,
    )

    permiso_id: int = Field(
        foreign_key="permiso.id",
        nullable=False,
    )

    asignado_en: datetime = Field(
        default_factory=datetime.now
    )

    activo: bool = Field(default=True)