from getpass import getpass

from sqlmodel import Session

from app.database import engine
from app.models.usuario import Departamento
from app.services.usuario_service import UsuarioService


ROLES_DISPONIBLES = {
    "1": ("ADMINISTRADOR", "Administrador"),
    "2": ("OPERADOR", "Operador"),
    "3": ("CHOFER", "Chofer"),
    "4": ("CALIDAD", "Calidad"),
    "5": ("CONSULTA", "Consulta"),
}


def crear_usuario():
    print("=== Crear usuario ===")
    print()

    for opcion, (_, nombre_rol) in ROLES_DISPONIBLES.items():
        print(f"{opcion}. {nombre_rol}")

    opcion = input("\nSelecciona el rol: ").strip()

    if opcion not in ROLES_DISPONIBLES:
        print("Error: selecciona un rol válido.")
        return

    rol_codigo, nombre_rol = ROLES_DISPONIBLES[opcion]

    username = input("Username: ").strip().lower()
    nombre = input("Nombre completo: ").strip()

    print("\nDepartamentos disponibles:")
    for departamento in Departamento:
        print(f"- {departamento.value}")

    departamento_texto = input(
        "\nEscribe el departamento: "
    ).strip()

    departamento = next(
        (
            item
            for item in Departamento
            if item.value.lower() == departamento_texto.lower()
        ),
        None,
    )

    if departamento is None:
        print("Error: el departamento no es válido.")
        return

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
                rol_codigo=rol_codigo,
                departamento=departamento,
                creado_por_id=None,
            )

            session.commit()

            print("\nUsuario creado correctamente.")
            print(f"ID: {usuario.id}")
            print(f"Username: {usuario.username}")
            print(f"Nombre: {usuario.nombre}")
            print(f"Rol: {nombre_rol}")
            print(f"Departamento: {usuario.departamento.value}")

    except ValueError as error:
        print(f"\nError: {error}")


if __name__ == "__main__":
    crear_usuario()
