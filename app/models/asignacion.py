from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models.orden import EstadoOrden


class TipoAsignacion(str, Enum):
    OPERADOR = "OPERADOR"
    CHOFER = "CHOFER"


class AsignacionOrden(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    orden_id: int = Field(
        foreign_key="ordenventa.id",
        nullable=False,
    )

    usuario_id: int = Field(
        foreign_key="usuario.id",
        nullable=False,
    )

    tipo_asignacion: TipoAsignacion = Field(
        nullable=False,
    )

    etapa_asignacion: EstadoOrden = Field(
        nullable=False,
    )

    asignado_por_id: Optional[int] = Field(
        default=None,
        foreign_key="usuario.id",
    )

    asignado_en: datetime = Field(
        default_factory=datetime.now
    )

    desasignado_en: Optional[datetime] = Field(
        default=None
    )

    activa: bool = Field(default=True)