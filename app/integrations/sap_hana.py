import os

from hdbcli import dbapi
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

def obtener_conexion_sap():
    """Establece una conexión de lectura con SAP HANA."""

    host = os.getenv("SAP_HANA_HOST")
    puerto = os.getenv("SAP_HANA_PORT")
    usuario = os.getenv("SAP_HANA_USER")
    contrasena = os.getenv("SAP_HANA_PASSWORD")

    if not all([host, puerto, usuario, contrasena]):
        raise RuntimeError(
            "Faltan variables de entorno para conectar con SAP HANA."
        )

    return dbapi.connect(
        address=host,
        port=int(puerto),
        user=usuario,
        password=contrasena,
        databaseName="HDB",
    )


def consultar_ordenes_abiertas(limite=100):
    """Consulta órdenes de venta abiertas en SAP, sin modificarlas."""

    if not isinstance(limite, int) or isinstance(limite, bool) or limite < 1:
        raise ValueError("El límite debe ser un entero positivo.")

    conexion = obtener_conexion_sap()

    try:
        cursor = conexion.cursor()

        try:
            consulta = """
                SELECT TOP ?
                    "DocEntry",
                    "DocNum",
                    "CardCode",
                    "CardName",
                    "DocDate",
                    "DocStatus"
                FROM "SBO_IM"."ORDR"
                WHERE "DocStatus" = 'O'
                ORDER BY "DocEntry" DESC
            """

            cursor.execute(consulta, (limite,))
            columnas = [columna[0] for columna in cursor.description]

            return [
                dict(zip(columnas, fila))
                for fila in cursor.fetchall()
            ]

        finally:
            cursor.close()

    finally:
        conexion.close()
