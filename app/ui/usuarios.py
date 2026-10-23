from nicegui import ui
from sqlmodel import Session

from app.database import engine
from app.models.usuario import Departamento
from app.services.usuario_service import UsuarioService


usuario_service = UsuarioService()


def crear_usuarios(
    tab_usuarios,
    usuario_actual_id: int,
):
    def abrir_formulario_creacion():
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-lg"):
            ui.label("Crear usuario").classes("text-xl font-bold")

            username = ui.input("Usuario").classes("w-full")
            nombre = ui.input("Nombre completo").classes("w-full")

            password = ui.input(
                "Contraseña",
                password=True,
                password_toggle_button=True,
            ).classes("w-full")

            confirmar_password = ui.input(
                "Confirmar contraseña",
                password=True,
                password_toggle_button=True,
            ).classes("w-full")

            with Session(engine) as session:
                roles = usuario_service.listar_roles_activos(
                    session=session,
                    administrador_id=usuario_actual_id,
                )

            rol = ui.select(
                options={
                    item.codigo: item.nombre
                    for item in roles
                },
                label="Rol",
            ).classes("w-full")

            departamento = ui.select(
                options={
                    item.value: item.value
                    for item in Departamento
                },
                label="Departamento",
            ).classes("w-full")

            def guardar():
                if not all([
                    username.value,
                    nombre.value,
                    password.value,
                    confirmar_password.value,
                    rol.value,
                    departamento.value,
                ]):
                    ui.notify(
                        "Completa todos los campos.",
                        type="warning",
                    )
                    return

                if password.value != confirmar_password.value:
                    ui.notify(
                        "Las contraseñas no coinciden.",
                        type="negative",
                    )
                    return

                try:
                    with Session(engine) as session:
                        usuario_service.crear_usuario(
                            session=session,
                            username=username.value,
                            nombre=nombre.value,
                            password=password.value,
                            rol_codigo=rol.value,
                            departamento=Departamento(
                                departamento.value
                            ),
                            administrador_id=usuario_actual_id,
                        )
                        session.commit()

                    dialog.close()
                    tabla_usuarios.refresh()

                    ui.notify(
                        "Usuario creado correctamente.",
                        type="positive",
                    )

                except (ValueError, PermissionError) as error:
                    ui.notify(
                        str(error),
                        type="negative",
                    )

                except Exception:
                    ui.notify(
                        "No se pudo crear el usuario. "
                        "Verifica los datos e inténtalo de nuevo.",
                        type="negative",
                    )
                    raise

            with ui.row().classes("w-full justify-end"):
                ui.button(
                    "Cancelar",
                    on_click=dialog.close,
                ).props("flat")

                ui.button(
                    "Guardar usuario",
                    icon="person_add",
                    on_click=guardar,
                )

        dialog.open()

    @ui.refreshable
    def tabla_usuarios():
        with Session(engine) as session:
            usuarios = usuario_service.listar_usuarios(
                session=session,
                administrador_id=usuario_actual_id,
            )

            datos = [
                {
                    "id": usuario.id,
                    "username": usuario.username,
                    "nombre": usuario.nombre,
                    "rol": (
                        usuario.rol.nombre
                        if usuario.rol
                        else "Sin rol"
                    ),
                    "departamento": usuario.departamento.value,
                    "activo": usuario.activo,
                }
                for usuario in usuarios
            ]

        columnas = [
            {
                "name": "username",
                "label": "Usuario",
                "field": "username",
                "align": "left",
            },
            {
                "name": "nombre",
                "label": "Nombre",
                "field": "nombre",
                "align": "left",
            },
            {
                "name": "rol",
                "label": "Rol",
                "field": "rol",
                "align": "left",
            },
            {
                "name": "departamento",
                "label": "Departamento",
                "field": "departamento",
                "align": "left",
            },
            {
                "name": "estado",
                "label": "Estado",
                "field": "estado",
                "align": "center",
            },
            {
                "name": "acciones",
                "label": "Acciones",
                "field": "acciones",
                "align": "center",
            },

        ]

        
        filas = [
            {
                **dato,
                "estado": "Activo" if dato["activo"] else "Inactivo",
            }
            for dato in datos
        ]

        def cambiar_estado(usuario_id: int, activo: bool):
            with ui.dialog() as dialog, ui.card():
                accion = "activar" if activo else "desactivar"

                ui.label(
                    f"¿Deseas {accion} este usuario?"
                ).classes("text-lg font-bold")

                with ui.row().classes("w-full justify-end"):
                    ui.button(
                        "Cancelar",
                        on_click=dialog.close,
                    ).props("flat")

                    def confirmar():
                        try:
                            with Session(engine) as session:
                                usuario_service.cambiar_estado_usuario(
                                    session=session,
                                    usuario_id=usuario_id,
                                    activo=activo,
                                    administrador_id=usuario_actual_id,
                                )
                                session.commit()

                            dialog.close()
                            tabla_usuarios.refresh()

                            ui.notify(
                                "Estado del usuario actualizado.",
                                type="positive",
                            )

                        except (ValueError, PermissionError) as error:
                            ui.notify(str(error), type="negative")

                        except Exception:
                            ui.notify(
                                "No se pudo cambiar el estado del usuario.",
                                type="negative",
                            )
                            raise

                    ui.button(
                        "Confirmar",
                        icon="check",
                        on_click=confirmar,
                    )

            dialog.open()


        
        tabla = ui.table(
            columns=columnas,
            rows=filas,
            row_key="id",
        ).classes("w-full")

        tabla.add_slot(
            "body-cell-acciones",
            r"""
            <q-td :props="props">
                <q-btn
                    v-if="props.row.activo"
                    flat
                    round
                    dense
                    color="positive"
                    icon="person_check"
                    @click="$parent.$emit('desactivar', props.row.id)"
                >
                    <q-tooltip>Desactivar usuario</q-tooltip>
                </q-btn>

                <q-btn
                    v-else
                    flat
                    round
                    dense
                    color="negative"
                    icon="person_off"
                    @click="$parent.$emit('activar', props.row.id)"
                >
                    <q-tooltip>Activar usuario</q-tooltip>
                </q-btn>
            </q-td>
            """,
        )

        tabla.on(
            "desactivar",
            lambda e: cambiar_estado(int(e.args), False),
        )
        tabla.on(
            "activar",
            lambda e: cambiar_estado(int(e.args), True),
        )


    with ui.tab_panel(tab_usuarios):
        with ui.column().classes("w-full p-4 gap-4"):
            ui.label("Administración de usuarios").classes(
                "text-2xl font-bold"
            )

            ui.label(
                "Consulta y administra las cuentas del sistema."
            ).classes("text-gray-600")

            ui.button(
                "Nuevo usuario",
                icon="person_add",
                on_click=abrir_formulario_creacion,
            )

            tabla_usuarios()

