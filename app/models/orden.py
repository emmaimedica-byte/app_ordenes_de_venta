# app/models/orden.py
from enum import Enum
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class EstadoOrden(str, Enum):
    LOGISTICA = "LOGISTICA"
    ALMACEN_SURTIDO = "ALMACEN_SURTIDO"
    EMBARQUES_REVISION = "EMBARQUES_REVISION"
    CALIDAD_LIBERACION = "CALIDAD_LIBERACION"
    TRANSPORTE_ENTREGA = "TRANSPORTE_ENTREGA"
    ADMINISTRACION_COMPLETADO = "ADMINISTRACION_COMPLETADO"

class OrdenVenta(SQLModel, table=True):
    __tablename__ = "ordenes_venta"

    id: Optional[int] = Field(default=None, primary_key=True)
    numero_ov: str = Field(index=True, unique=True, nullable=False)
    cliente: str = Field(default="Cliente General")
    estado: EstadoOrden = Field(default=EstadoOrden.LOGISTICA, index=True)
    
    creado_en: datetime = Field(default_factory=datetime.now)
    actualizado_en: datetime = Field(default_factory=datetime.now)
    operador_actual: Optional[str] = Field(default="Sistema")
    observaciones: Optional[str] = Field(default=None)