from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models.orden import EstadoOrden


class RolEtapa(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    rol_id: int = Field(
        foreign_key="rol.id",
        nullable=False,
    )

    estado: EstadoOrden = Field(
        nullable=False,
    )

    activo: bool = Field(default=True)

    asignado_en: datetime = Field(
        default_factory=datetime.now
    )