from sqlmodel import Session, select

from app.models.imagen import ImagenOrden


class ImagenRepository:

    def crear(self, session: Session, imagen: ImagenOrden) -> ImagenOrden:
        session.add(imagen)
        session.flush()
        session.refresh(imagen)
        return imagen

    def obtener_por_orden(
        self,
        session: Session,
        orden_id: int,
    ) -> list[ImagenOrden]:
        consulta = (
            select(ImagenOrden)
            .where(ImagenOrden.orden_id == orden_id)
            .order_by(ImagenOrden.fecha_registro.desc())
        )
        return list(session.exec(consulta).all())

    def obtener_por_id(
        self,
        session: Session,
        imagen_id: int,
    ) -> ImagenOrden | None:
        return session.get(ImagenOrden, imagen_id)

    def eliminar(self, session: Session, imagen: ImagenOrden) -> None:
        session.delete(imagen)
