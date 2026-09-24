from getpass import getpass

from sqlmodel import Session

from app.database import engine
from app.models.usuario import Departamento
from app.services.usuario_service import UsuarioService


def crear_usuario():
    print("=== Crear usuario administrador ===")
    print()

    username = input("Username: ").strip().lower()
    nombre = input("Nombre completo: ").strip()

    password = getpass("Contraseña: ")
    confirmar_password = getpass("Confirmar contraseña: ")

    if password != confirmar_password:
        print("Error: las contraseñas no coinciden.")
        return

    try:
        with Session(engine) as session:
            usuario_service = UsuarioService()

            usuario = usuario_service.crear_usuario(
                session=session,
                username=username,
                nombre=nombre,
                password=password,
                rol_codigo="ADMINISTRADOR",
                departamento=Departamento.SAP,
                creado_por_id=None,
            )

            session.commit()

            print()
            print("Usuario administrador creado correctamente.")
            print(f"ID: {usuario.id}")
            print(f"Username: {usuario.username}")
            print(f"Nombre: {usuario.nombre}")
            print("Rol: Administrador")
            print(f"Departamento: {usuario.departamento.value}")

    except ValueError as error:
        print()
        print(f"Error: {error}")


if __name__ == "__main__":
    crear_usuario()