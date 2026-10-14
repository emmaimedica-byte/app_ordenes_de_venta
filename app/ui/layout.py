from nicegui import ui


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

    # Pestañas
    with ui.tabs().classes('w-full bg-blue-50 border-b') as tabs:
        tab_kanban = ui.tab(
            'Tablero General',
            icon='dashboard',
        )
        tab_handheld = ui.tab(
            'Modo Handheld / Escáner',
            icon='qr_code_scanner',
        )
        tab_metrics = ui.tab(
            'Dashboard & KPIs',
            icon='analytics',
        )

        tab_asignaciones = None

        if usuario_rol == 'ADMINISTRADOR':
            tab_asignaciones = ui.tab(
                'Administración de Asignaciones',
                icon='assignment_ind',
            )

    tab_panels = ui.tab_panels(
        tabs,
        value=tab_kanban,
    ).classes('w-full bg-slate-50 p-2')

    return (
        tab_panels,
        tab_kanban,
        tab_handheld,
        tab_metrics,
        tab_asignaciones,
    )
