from dotenv import load_dotenv
import sqlite3
import os


# Cargar variables del archivo .env
load_dotenv()


# Función para conectar a la base de datos SQLite3
def conexion_basedatos():
    db_path = os.getenv("DATABASE_PATH", "database.db")  # usa 'database.db' por defecto si no existe la variable
    conexion = sqlite3.connect(db_path)
    conexion.row_factory = sqlite3.Row
    return conexion