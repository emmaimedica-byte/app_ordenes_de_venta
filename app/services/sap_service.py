from sqlmodel import Session

from app.integrations.sap_hana import consultar_ordenes_abiertas
from app.repositories.orden_repository import OrdenRepository


class SAPService:

    def __init__(self, orden_repository: OrdenRepository):
        self.orden_repository = orden_repository

    def obtener_ordenes_abiertas(
        self,
        session: Session,
        limite: int = 100,
    ) -> list[dict]:
        """Consulta SAP y excluye las órdenes ya importadas localmente."""
        ordenes_sap = consultar_ordenes_abiertas(limite=limite)

        doc_entries_importados = (
            self.orden_repository.obtener_doc_entries_sap_importados(
                session
            )
        )

        return [
            orden
            for orden in ordenes_sap
            if int(orden["DocEntry"]) not in doc_entries_importados
        ]

