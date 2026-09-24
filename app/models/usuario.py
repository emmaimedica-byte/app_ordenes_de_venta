from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Relationship
from enum import Enum
from app.models.rol import Rol

class Departamento(str, Enum):
    ALMACEN = "Almacén"
    BEDCARE = "Bedcare"
    CALIDAD = "Calidad"
    COMPRAS_IMPORTACIONES = "Compras e Importaciones"
    CONMED = "Conmed"
    CONTABILIDAD = "Contabilidad"
    CREDITO_COBRANZA = "Crédito y Cobranza"
    DIRECCION_GENERAL = "Dirección General"
    ESPECIALIDADES = "Especialidades"
    FINANZAS = "Finanzas"
    LICITACIONES = "Licitaciones"
    MERCADOTECNIA = "Mercadotecnia"
    PROYECTOS = "Proyectos"
    RECURSOS_HUMANOS = "Recursos Humanos"
    SAP = "SAP"
    STERIS = "Steris"
    TECNICOS = "Técnicos"
    TI = "TI"
    VENTAS = "Ventas"


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

    rol: Optional[Rol] = Relationship()

    departamento: Departamento = Field(nullable=False)

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