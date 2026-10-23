from sqlmodel import Session, select

from app.models.orden import OrdenVenta, HistorialOrden


class OrdenRepository:

    def obtener_por_id(
        self,
        session: Session,
        orden_id: int
    ) -> OrdenVenta | None:
        return session.get(OrdenVenta, orden_id)

    def obtener_por_numero(
        self,
        session: Session,
        numero_ov: str
    ) -> OrdenVenta | None:
        return session.exec(
            select(OrdenVenta)
            .where(OrdenVenta.numero_ov == numero_ov)
        ).first()

    def obtener_todas(
        self,
        session: Session
    ) -> list[OrdenVenta]:
        return session.exec(
            select(OrdenVenta)
        ).all()
    
    
    def obtener_doc_entries_sap_importados(
        self,
        session: Session,
    ) -> set[int]:
        """Obtiene los identificadores de SAP que ya están importados."""
        resultado = session.exec(
            select(OrdenVenta.sap_doc_entry).where(
                OrdenVenta.sap_doc_entry.is_not(None)
            )
        ).all()

        return {int(doc_entry) for doc_entry in resultado}


    def guardar(
        self,
        session: Session,
        orden: OrdenVenta
    ) -> None:
        session.add(orden)

    def agregar_historial(
        self,
        session: Session,
        historial: HistorialOrden
    ) -> None:
        session.add(historial)

    def obtener_historial(
        self,
        session: Session,
        orden_id: int
    ) -> list[HistorialOrden]:
        return session.exec(
            select(HistorialOrden)
            .where(HistorialOrden.orden_id == orden_id)
            .order_by(HistorialOrden.fecha_registro.desc())
        ).all()

    def crear(
        self,
        session: Session,
        orden: OrdenVenta
    ) -> OrdenVenta:
        session.add(orden)
        session.flush()
        session.refresh(orden)
        return orden