from sqlmodel import Session, select

from app.database import engine
from app.models.asignacion import AsignacionOrden, TipoAsignacion
from app.models.orden import (
    EstadoOrden,
    HistorialOrden,
    OrdenVenta,
)
from app.models.usuario import Departamento, Usuario
from app.repositories.orden_repository import OrdenRepository
from app.services.orden_service import OrdenService


def ejecutar_pruebas():

    repository = OrdenRepository()
    service = OrdenService(repository)

    with Session(engine) as session:

        administrador = session.get(Usuario, 2)

        if not administrador:
            raise RuntimeError(
                "No existe el usuario administrador id=2"
            )

        operador = Usuario(
            username="test_operador_6b4",
            nombre="Operador Prueba 6B4",
            password_hash="TEST",
            rol_id=2,
            departamento=Departamento.ALMACEN,
            activo=True,
        )

        session.add(operador)
        session.commit()
        session.refresh(operador)

        orden = OrdenVenta(
            numero_ov="TEST-6B4-001",
            cliente="Prueba 6B.4",
            estado=EstadoOrden.LOGISTICA,
        )

        session.add(orden)
        session.commit()
        session.refresh(orden)

        asignacion = AsignacionOrden(
            orden_id=orden.id,
            usuario_id=operador.id,
            tipo_asignacion=TipoAsignacion.OPERADOR,
            etapa_asignacion=EstadoOrden.LOGISTICA,
            asignado_por_id=administrador.id,
            activa=True,
        )

        session.add(asignacion)
        session.commit()
        session.refresh(asignacion)

        print("PRUEBAS DE mover_orden()")
        print("=" * 60)

        # --------------------------------------------------
        # PRUEBA 1: Administrador puede mover la OV
        # --------------------------------------------------

        resultado = service.mover_orden(
            session=session,
            orden_id=orden.id,
            usuario_id=administrador.id,
            mover_adelante=True,
        )

        assert resultado.estado == EstadoOrden.ALMACEN_SURTIDO

        print(
            "Administrador → Logística a Almacén:",
            True
        )

        # --------------------------------------------------
        # PRUEBA 2: Operador con asignación puede mover
        # --------------------------------------------------

        resultado = service.mover_orden(
            session=session,
            orden_id=orden.id,
            usuario_id=operador.id,
            mover_adelante=True,
        )

        assert resultado.estado == EstadoOrden.EMBARQUES_REVISION

        print(
            "Operador con asignación → Almacén a Embarques:",
            True
        )

        # --------------------------------------------------
        # PRUEBA 3: Operador sin asignación
        # --------------------------------------------------

        operador_sin_asignacion = Usuario(
            username="test_operador_sin_asignacion_6b4",
            nombre="Operador Sin Asignación 6B4",
            password_hash="TEST",
            rol_id=2,
            departamento=Departamento.ALMACEN,
            activo=True,
        )

        session.add(operador_sin_asignacion)
        session.commit()
        session.refresh(operador_sin_asignacion)

        try:

            service.mover_orden(
                session=session,
                orden_id=orden.id,
                usuario_id=operador_sin_asignacion.id,
                mover_adelante=True,
            )

            raise AssertionError(
                "El operador sin asignación pudo mover la OV"
            )

        except PermissionError:

            print(
                "Operador sin asignación → movimiento rechazado:",
                True
            )

       
    
        # --------------------------------------------------
        # PRUEBAS DE mover_orden_a_estado() - HANDHELD
        # --------------------------------------------------

        print()
        print("PRUEBAS DE mover_orden_a_estado()")
        print("=" * 60)

        # PRUEBA 4: Administrador puede saltar de etapa

        resultado = service.mover_orden_a_estado(
            session=session,
            orden_id=orden.id,
            nuevo_estado=EstadoOrden.CALIDAD_LIBERACION,
            usuario_id=administrador.id,
        )

        assert resultado.estado == EstadoOrden.CALIDAD_LIBERACION

        print(
            "Administrador → salto directo a Calidad:",
            True
        )

        # PRUEBA 5: Operador asignado puede saltar de etapa

        resultado = service.mover_orden_a_estado(
            session=session,
            orden_id=orden.id,
            nuevo_estado=EstadoOrden.ADMINISTRACION_COMPLETADO,
            usuario_id=operador.id,
        )

        assert resultado.estado == EstadoOrden.ADMINISTRACION_COMPLETADO

        print(
            "Operador asignado → salto directo a Completado:",
            True
        )

        # PRUEBA 6: Operador sin asignación no puede mover

        try:
            service.mover_orden_a_estado(
                session=session,
                orden_id=orden.id,
                nuevo_estado=EstadoOrden.LOGISTICA,
                usuario_id=operador_sin_asignacion.id,
            )

            raise AssertionError(
                "El operador sin asignación pudo mover la OV desde Handheld"
            )

        except PermissionError:
            print(
                "Operador sin asignación → Handheld rechaza movimiento:",
                True
            )

     # --------------------------------------------------
        # LIMPIEZA
        # --------------------------------------------------

        historial = session.exec(
            select(HistorialOrden)
            .where(HistorialOrden.orden_id == orden.id)
        ).all()

        for registro in historial:
            session.delete(registro)

        session.delete(asignacion)

        # Quitamos la referencia del usuario temporal
        # antes de eliminarlo.
        orden.operador_actual_id = None
        session.add(orden)
        session.commit()

        # Ahora la orden ya no referencia al usuario.
        session.delete(orden)
        session.commit()

        session.delete(operador)
        session.delete(operador_sin_asignacion)
        session.commit()

        print("=" * 60)
        print("PRUEBAS COMPLETADAS")
    


if __name__ == "__main__":
    ejecutar_pruebas()
    