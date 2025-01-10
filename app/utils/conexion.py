import sqlite3

# Función para conectar a la base de datos SQLite3
def conexion_basedatos():
    # Conectamos a la base de datos "database.db" que está en la raíz del proyecto
    conexion = sqlite3.connect('database.db')
    conexion.row_factory = sqlite3.Row  # Esto nos permite acceder a los resultados como diccionarios
    
    return conexion



# Función para insertar un usuario en la base de datos
def insertar_usuario(correo, contraseña, rol):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO usuarios (correo, contraseña, rol) VALUES (?, ?, ?)", (correo, contraseña, rol))
    conn.commit()
    conn.close()



# Función para obtener un usuario por correo
def obtener_usuario_por_correo(correo):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE correo = ?", (correo,))
    existing_user = cursor.fetchone()
    conn.close()
    return existing_user