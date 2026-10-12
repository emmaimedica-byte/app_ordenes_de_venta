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
from app.models.rol import Rol




def limpiar_datos_prueba(session):
    """Elimina los datos de prueba respetando las claves foráneas."""

    from sqlmodel import select

    usernames = [
        "test_operador_6b4",
        "test_operador_sin_asignacion_6b4",
        "test_chofer_6b7",
        "test_lectura_4_6b7",
        "test_lectura_5_6b7",
        "test_rol_inactivo_6b7",
    ]

    ordenes = session.exec(
        select(OrdenVenta).where(
            OrdenVenta.numero_ov == "TEST-6B4-001"
        )
    ).all()

    orden_ids = [orden.id for orden in ordenes]

    usuarios = session.exec(
        select(Usuario).where(
            Usuario.username.in_(usernames)
        )
    ).all()

    usuario_ids = [usuario.id for usuario in usuarios]

    # Eliminar historial asociado a la orden de prueba.
    if orden_ids:
        registros = session.exec(
            select(HistorialOrden).where(
                HistorialOrden.orden_id.in_(orden_ids)
            )
        ).all()

        for registro in registros:
            session.delete(registro)

    # Eliminar historial que referencia a los usuarios temporales.
    if usuario_ids:
        registros_usuario = session.exec(
            select(HistorialOrden).where(
                HistorialOrden.usuario_operador_id.in_(usuario_ids)
            )
        ).all()

        for registro in registros_usuario:
            session.delete(registro)

    session.commit()

    # Eliminar asignaciones donde los temporales sean operador o asignador.
    condiciones = []

    if orden_ids:
        condiciones.append(
            AsignacionOrden.orden_id.in_(orden_ids)
        )

    if usuario_ids:
        condiciones.append(
            AsignacionOrden.usuario_id.in_(usuario_ids)
        )
        condiciones.append(
            AsignacionOrden.asignado_por_id.in_(usuario_ids)
        )

    if condiciones:
        from sqlalchemy import or_

        asignaciones = session.exec(
            select(AsignacionOrden).where(or_(*condiciones))
        ).all()

        for asignacion in asignaciones:
            session.delete(asignacion)

        session.commit()

    # Desvincular los operadores actuales antes de borrar las órdenes.
    for orden in ordenes:
        orden.operador_actual_id = None
        session.add(orden)

    session.commit()

    for orden in ordenes:
        session.delete(orden)

    session.commit()

    

    # Eliminar usuarios temporales.
    for usuario in usuarios:
        session.delete(usuario)

    session.commit()

    # El rol temporal se elimina al final.
    rol = session.exec(
        select(Rol).where(
            Rol.codigo == "ROL_TEST_INACTIVO_6B7"
        )
    ).first()

    if rol:
        session.delete(rol)
        session.commit()





def ejecutar_pruebas():
    repository = OrdenRepository()
    service = OrdenService(repository)

    with Session(engine) as session:
        # Eliminar posibles residuos de ejecuciones anteriores.
        limpiar_datos_prueba(session)

        try:
            administrador = session.get(Usuario, 2)

            if not administrador:
                raise RuntimeError(
                    "No existe el usuario administrador id=2"
                )

            # --------------------------------------------------
            # PREPARACIÓN DE DATOS
            # --------------------------------------------------

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
            # PRUEBA 1: Administrador puede mover la OV.
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
                True,
            )

            # --------------------------------------------------
            # PRUEBA 2: Operador asignado puede mover.
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
                True,
            )

            # --------------------------------------------------
            # PRUEBA 3: Operador sin asignación.
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
                    True,
                )

            # --------------------------------------------------
            # PRUEBAS DE mover_orden_a_estado() - HANDHELD
            # --------------------------------------------------

            print()
            print("PRUEBAS DE mover_orden_a_estado()")
            print("=" * 60)

            # PRUEBA 4: Administrador puede saltar de etapa.

            resultado = service.mover_orden_a_estado(
                session=session,
                orden_id=orden.id,
                nuevo_estado=EstadoOrden.CALIDAD_LIBERACION,
                usuario_id=administrador.id,
            )

            assert resultado.estado == EstadoOrden.CALIDAD_LIBERACION

            print(
                "Administrador → salto directo a Calidad:",
                True,
            )

            # PRUEBA 5: Operador asignado puede saltar de etapa.

            resultado = service.mover_orden_a_estado(
                session=session,
                orden_id=orden.id,
                nuevo_estado=EstadoOrden.ADMINISTRACION_COMPLETADO,
                usuario_id=operador.id,
            )

            assert (
                resultado.estado
                == EstadoOrden.ADMINISTRACION_COMPLETADO
            )

            print(
                "Operador asignado → salto directo a Completado:",
                True,
            )

            # PRUEBA 6: Operador sin asignación no puede mover.

            try:
                service.mover_orden_a_estado(
                    session=session,
                    orden_id=orden.id,
                    nuevo_estado=EstadoOrden.LOGISTICA,
                    usuario_id=operador_sin_asignacion.id,
                )

                raise AssertionError(
                    "El operador sin asignación pudo mover "
                    "la OV desde Handheld"
                )

            except PermissionError:
                print(
                    "Operador sin asignación → Handheld "
                    "rechaza movimiento:",
                    True,
                )

            # --------------------------------------------------
            # PRUEBAS ADICIONALES DE AUTORIZACIÓN
            # --------------------------------------------------

            print()
            print("PRUEBAS ADICIONALES DE AUTORIZACIÓN")
            print("=" * 60)

            # Crear un chofer temporal.

            chofer = Usuario(
                username="test_chofer_6b7",
                nombre="Chofer Prueba 6B7",
                password_hash="TEST",
                rol_id=3,
                departamento=Departamento.ALMACEN,
                activo=True,
            )

            session.add(chofer)
            session.commit()
            session.refresh(chofer)

            # Devolver la OV a Transporte para probar al chofer.

            orden.estado = EstadoOrden.TRANSPORTE_ENTREGA
            session.add(orden)
            session.commit()

            asignacion_chofer = AsignacionOrden(
                orden_id=orden.id,
                usuario_id=chofer.id,
                tipo_asignacion=TipoAsignacion.CHOFER,
                etapa_asignacion=EstadoOrden.TRANSPORTE_ENTREGA,
                asignado_por_id=administrador.id,
                activa=True,
            )

            session.add(asignacion_chofer)
            session.commit()

            # PRUEBA 7: Chofer puede completar una OV asignada.

            resultado = service.mover_orden_a_estado(
                session=session,
                orden_id=orden.id,
                nuevo_estado=EstadoOrden.ADMINISTRACION_COMPLETADO,
                usuario_id=chofer.id,
            )

            assert (
                resultado.estado
                == EstadoOrden.ADMINISTRACION_COMPLETADO
            )

            print(
                "Chofer asignado → Transporte a Completado:",
                True,
            )

            # PRUEBA 8: Chofer no puede mover a otra etapa.

            orden.estado = EstadoOrden.TRANSPORTE_ENTREGA
            session.add(orden)
            session.commit()

            try:
                service.mover_orden_a_estado(
                    session=session,
                    orden_id=orden.id,
                    nuevo_estado=EstadoOrden.CALIDAD_LIBERACION,
                    usuario_id=chofer.id,
                )

                raise AssertionError(
                    "El chofer pudo mover la OV a Calidad"
                )

            except PermissionError:
                session.refresh(orden)

                assert (
                    orden.estado
                    == EstadoOrden.TRANSPORTE_ENTREGA
                )

                print(
                    "Chofer → destino no permitido rechazado:",
                    True,
                )

            # PRUEBA 9: Chofer sin asignación no puede completar.

            asignacion_chofer.activa = False
            session.add(asignacion_chofer)
            session.commit()

            try:
                service.mover_orden_a_estado(
                    session=session,
                    orden_id=orden.id,
                    nuevo_estado=EstadoOrden.ADMINISTRACION_COMPLETADO,
                    usuario_id=chofer.id,
                )

                raise AssertionError(
                    "El chofer sin asignación pudo completar la OV"
                )

            except PermissionError:
                session.refresh(orden)

                assert (
                    orden.estado
                    == EstadoOrden.TRANSPORTE_ENTREGA
                )

                print(
                    "Chofer sin asignación → movimiento rechazado:",
                    True,
                )

            # PRUEBAS 10 y 11: Calidad y Consulta no pueden mover.

            for rol_id, nombre_rol in [
                (4, "Calidad"),
                (5, "Consulta"),
            ]:
                usuario_lectura = Usuario(
                    username=f"test_lectura_{rol_id}_6b7",
                    nombre=f"Usuario {nombre_rol} Prueba",
                    password_hash="TEST",
                    rol_id=rol_id,
                    departamento=Departamento.CALIDAD,
                    activo=True,
                )

                session.add(usuario_lectura)
                session.commit()
                session.refresh(usuario_lectura)

                try:
                    service.mover_orden_a_estado(
                        session=session,
                        orden_id=orden.id,
                        nuevo_estado=EstadoOrden.CALIDAD_LIBERACION,
                        usuario_id=usuario_lectura.id,
                    )

                    raise AssertionError(
                        f"{nombre_rol} pudo mover la OV"
                    )

                except PermissionError:
                    session.refresh(orden)

                    assert (
                        orden.estado
                        == EstadoOrden.TRANSPORTE_ENTREGA
                    )

                    print(
                        f"{nombre_rol} → movimiento rechazado:",
                        True,
                    )

                # No eliminar aquí: la limpieza centralizada
                # se encarga de los usuarios temporales.

            # PRUEBA 12: Usuario inactivo no puede mover.

            operador.activo = False
            session.add(operador)
            session.commit()

            try:
                service.mover_orden_a_estado(
                    session=session,
                    orden_id=orden.id,
                    nuevo_estado=EstadoOrden.CALIDAD_LIBERACION,
                    usuario_id=operador.id,
                )

                raise AssertionError(
                    "El usuario inactivo pudo mover la OV"
                )

            except PermissionError:
                session.refresh(orden)

                assert (
                    orden.estado
                    == EstadoOrden.TRANSPORTE_ENTREGA
                )

                print(
                    "Usuario inactivo → movimiento rechazado:",
                    True,
                )

            operador.activo = True
            session.add(operador)
            session.commit()

            # PRUEBA 13: Usuario con rol inactivo no puede mover.

            rol_temporal = Rol(
                codigo="ROL_TEST_INACTIVO_6B7",
                nombre="Rol Prueba Inactivo 6B7",
                descripcion="Rol temporal para pruebas",
                activo=False,
            )

            session.add(rol_temporal)
            session.commit()
            session.refresh(rol_temporal)

            usuario_rol_inactivo = Usuario(
                username="test_rol_inactivo_6b7",
                nombre="Usuario Rol Inactivo",
                password_hash="TEST",
                rol_id=rol_temporal.id,
                departamento=Departamento.ALMACEN,
                activo=True,
            )

            session.add(usuario_rol_inactivo)
            session.commit()
            session.refresh(usuario_rol_inactivo)

            try:
                service.mover_orden_a_estado(
                    session=session,
                    orden_id=orden.id,
                    nuevo_estado=EstadoOrden.CALIDAD_LIBERACION,
                    usuario_id=usuario_rol_inactivo.id,
                )

                raise AssertionError(
                    "El usuario con rol inactivo pudo mover la OV"
                )

            except PermissionError:
                session.refresh(orden)

                assert (
                    orden.estado
                    == EstadoOrden.TRANSPORTE_ENTREGA
                )

                print(
                    "Rol inactivo → movimiento rechazado:",
                    True,
                )

            print("=" * 60)
            print("PRUEBAS COMPLETADAS")

        finally:
            # Se ejecuta aunque una prueba falle.
            limpiar_datos_prueba(session)


if __name__ == "__main__":
    ejecutar_pruebas()
