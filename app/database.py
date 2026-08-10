import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# ==================== Configuración General ====================
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "ordenes_venta")

# Cadena de conexión MySQL con pymysql
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8mb4"

# Crear Motor de Base de Datos (con pool_pre_ping para reconexiones automáticas)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)


def create_db_and_tables():
    """Crea las tablas en MySQL / phpMyAdmin al iniciar la app si no existen."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Generador de sesiones para endpoints de FastAPI."""
    with Session(engine) as session:
        yield session