# app/schemas/orden.py
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from app.models.orden import EstadoOrden

class OrdenVentaCrear(BaseModel):
    numero_ov: str
    cliente: Optional[str] = "Cliente General"


class OrdenVentaActualizar(BaseModel):
    numero_ov: str
    cliente: str

class OrdenVentaActualizarEstado(BaseModel):
    numero_ov: str
    nuevo_estado: EstadoOrden
    operador: Optional[str] = "Handheld_User"
    observaciones: Optional[str] = None


class OrdenVentaRespuesta(BaseModel):
    id: int
    numero_ov: str
    cliente: str
    estado: EstadoOrden
    operador_actual: Optional[str]
    observaciones: Optional[str]
    creado_en: datetime
    actualizado_en: datetime

class HistorialOrdenRespuesta(BaseModel):
    id: int
    orden_id: int
    estado_anterior: Optional[str]
    estado_nuevo: str
    usuario_operador: str
    observaciones: Optional[str]
    fecha_registro: datetime
