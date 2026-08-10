from pydantic import BaseModel
from typing import Optional
from app.models.orden import EstadoOrden

class OrdenVentaCrear(BaseModel):
    numero_ov: str
    cliente: Optional[str] = "Cliente General"

class OrdenVentaActualizarEstado(BaseModel):
    numero_ov: str
    nuevo_estado: EstadoOrden
    operador: Optional[str] = "Handheld_User"
    observaciones: Optional[str] = None