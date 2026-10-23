# app/models/orden.py
from typing import Optional, List
from enum import Enum
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

class EstadoOrden(str, Enum):
    LOGISTICA = "Logística"
    ALMACEN_SURTIDO = "Almacén (Surtido)"
    EMBARQUES_REVISION = "Embarques (Revisión)"
    CALIDAD_LIBERACION = "Calidad (Liberación)"
    TRANSPORTE_ENTREGA = "Transporte (En tránsito)"
    ADMINISTRACION_COMPLETADO = "Administración (Completado)"

# ----------------------------------------------------
# 1. TABLA SECUNDARIA: HISTORIAL DE MOVIMIENTOS
# ----------------------------------------------------
class HistorialOrden(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    orden_id: int = Field(
        foreign_key="ordenventa.id",
        nullable=False,
        )
    estado_anterior: Optional[str] = Field(default=None)
    estado_nuevo: str = Field(nullable=False)
    usuario_operador_id: Optional[int] = Field(
        default=None,
        foreign_key="usuario.id"
    )
    observaciones: Optional[str] = Field(default=None)
    fecha_registro: datetime = Field(
        default_factory=datetime.now
    )

    # Relación inversa a la orden
    orden: Optional["OrdenVenta"] = Relationship(
        back_populates="historial"
    )

# ----------------------------------------------------
# 2. TABLA PRINCIPAL: ORDEN DE VENTA
# ----------------------------------------------------
class OrdenVenta(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sap_doc_entry: Optional[int] = Field(
        default=None,
        index=True,
        unique=True,
        nullable=True,
    )
    numero_ov: str = Field(
        index=True,
        unique=True,
        nullable=False
    )
    cliente: str = Field(nullable=False)
    estado: EstadoOrden = Field(
        default=EstadoOrden.LOGISTICA
    )
    operador_actual_id: Optional[int] = Field(
        default=None,
        foreign_key="usuario.id"
    )
    observaciones: Optional[str] = Field(default=None)
    creado_en: datetime = Field(
        default_factory=datetime.now
    )
    actualizado_en: datetime = Field(
        default_factory=datetime.now
    )

    # Relación: Una orden tiene muchos registros de historial
    historial: List[HistorialOrden] = Relationship(
        back_populates="orden"
    )
