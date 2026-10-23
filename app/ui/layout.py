from nicegui import app,ui


def crear_layout(
    usuario_nombre: str,
    cerrar_sesion,
    usuario_rol: str = '',
):
    ui.colors(
        primary='#1E3A8A',
        secondary='#3B82F6',
        accent='#10B981',
    )

    ui.add_head_html('''
        <link rel="stylesheet" href="/static/css/app.css">
        <script src="/static/js/app.js"></script>
    ''')

    # Encabezado principal
    with ui.header().classes(
        'items-center justify-between bg-primary text-white p-3 shadow-md'
    ):
        with ui.row().classes('items-center gap-2'):
            ui.icon('local_shipping', size='md')
            ui.label(
                'Seguimiento de Órdenes de Venta'
            ).classes('text-lg md:text-xl font-bold')

        with ui.row().classes('items-center gap-3'):
            ui.label(
                f'Usuario: {usuario_nombre}'
            ).classes('text-sm')

            ui.button(
                'Cerrar sesión',
                icon='logout',
                on_click=cerrar_sesion,
            ).props('flat color=white')

            ui.label(
                'Red: 172.16.31.105:8072'
            ).classes(
                'text-xs opacity-80 bg-blue-900 px-3 py-1 rounded-full hidden md:block'
            )

    
    # Identificadores estables para recordar la pestaña activa
    pestana_guardada = app.storage.user.get(
        'pestana_activa',
        'tablero',
    )

    nombres_validos = {'tablero', 'handheld', 'dashboard'}

    if usuario_rol == 'ADMINISTRADOR':
        nombres_validos.update({'asignaciones', 'usuarios'})

    if pestana_guardada not in nombres_validos:
        pestana_guardada = 'tablero'

    def guardar_pestana(event):
        valor = event.value

        if isinstance(valor, str) and valor in nombres_validos:
            app.storage.user['pestana_activa'] = valor

    with ui.tabs(
        value=pestana_guardada,
        on_change=guardar_pestana,
    ).classes('w-full bg-blue-50 border-b') as tabs:
        tab_kanban = ui.tab(
            'tablero',
            label='Tablero General',
            icon='dashboard',
        )
        tab_handheld = ui.tab(
            'handheld',
            label='Modo Handheld / Escáner',
            icon='qr_code_scanner',
        )
        tab_metrics = ui.tab(
            'dashboard',
            label='Dashboard & KPIs',
            icon='analytics',
        )

        tab_asignaciones = None
        tab_usuarios = None

        if usuario_rol == 'ADMINISTRADOR':
            tab_asignaciones = ui.tab(
                'asignaciones',
                label='Administración de Asignaciones',
                icon='assignment_ind',
            )
            tab_usuarios = ui.tab(
                'usuarios',
                label='Administración de Usuarios',
                icon='manage_accounts',
            )

    pestanas = {
        'tablero': tab_kanban,
        'handheld': tab_handheld,
        'dashboard': tab_metrics,
    }

    if tab_asignaciones is not None:
        pestanas['asignaciones'] = tab_asignaciones

    if tab_usuarios is not None:
        pestanas['usuarios'] = tab_usuarios

    tab_panels = ui.tab_panels(
        tabs,
        value=pestanas[pestana_guardada],
    ).classes('w-full bg-slate-50 p-2')

    return (
        tab_panels,
        tab_kanban,
        tab_handheld,
        tab_metrics,
        tab_asignaciones,
        tab_usuarios,
    )

