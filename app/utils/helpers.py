from flask import session, redirect, url_for, flash, request
from functools import wraps
from app.utils.conexion import conexion_basedatos



# Decorador para verificar si hay una sesión activa
def login_required(f):
    @wraps(f)
    def funcion_decorador(*args, **kwargs):
        # Verificamos si hay una sesión activa
        if 'id_usuario' not in session:
            flash('Inicia sesión para acceder a esta página.', 'error')
            return redirect(url_for('auth.login'))  # Redirigimos al login si no hay sesión
        
        return f(*args, **kwargs)  # Continuamos con la ejecución de la ruta
    return funcion_decorador



# Decorador para verificar si el usuario es un entrenador
def entrenador_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rol') != 2:  # Solo permite acceso a entrenadores
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function



# Decorador para verificar si el formulario de entrenador esta completo
def verificar_formulario_completo(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Verifica si el usuario está logueado y es un entrenador (rol = 2)
        if 'id_usuario' in session and session.get('rol') == 2:
            db = conexion_basedatos()
            cursor = db.cursor()
            cursor.execute(
                "SELECT form_complete FROM entrenador WHERE id_usuario = ?",
                (session['id_usuario'],)
            )
            form_complete = cursor.fetchone()
            
            # Si el formulario no está completo, redirige a la página para completar el formulario
            if form_complete and form_complete[0] == 'false':
                return redirect(url_for('form_entrenador.form_entrenador'))

        # Si el formulario está completo o el usuario no es entrenador, ejecuta la función
        return func(*args, **kwargs)
    
    return wrapper


def verificar_vinculo_y_rutina(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Obtener el ID de usuario de la sesión
        id_usuario = session.get('id_usuario')
        
        if not id_usuario:
            flash('Debes iniciar sesión para acceder a esta sección', 'error')
            return redirect(url_for('auth.login'))
        
        # Verificar si es alumno (rol 1)
        conn = conexion_basedatos()
        cursor = conn.cursor()
        
        # Obtener el rol del usuario
        cursor.execute("SELECT rol FROM usuario WHERE id_usuario = ?", (id_usuario,))
        usuario = cursor.fetchone()
        
        if not usuario or usuario['rol'] != 1:  # Si no es alumno
            conn.close()
            return f(*args, **kwargs)  # Permitir acceso a otros roles
            
        # Verificar si tiene vinculación con un entrenador
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM vinculaciones 
            WHERE id_usuario_destino = ? AND estado = 'aceptada'
        """, (id_usuario,))
        vinculacion = cursor.fetchone()
        
        # Verificar si tiene al menos un entrenamiento asignado
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM entrenamiento e
            JOIN alumno a ON e.id_alumno = a.id_alumno
            WHERE a.id_usuario = ?
        """, (id_usuario,))
        entrenamiento = cursor.fetchone()
        
        conn.close()
        
        # Si no tiene vinculación o no tiene entrenamiento
        if vinculacion['count'] == 0 or entrenamiento['count'] == 0:
            flash('No tienes ninguna rutina de entrenamiento asignada para ver tu progreso.', 'error')
            return redirect(url_for('entrenamiento.entrenamiento'))
        
        return f(*args, **kwargs)
    return decorated_function


# Función para verificar si un archivo tiene una extension permitida
def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions



# Función para insertar un usuario en la base de datos
def insertar_usuario(email, nombre_usuario, contrasena, rol):
    try:
        conn = conexion_basedatos()
        cursor = conn.cursor()

        # Insertar en la tabla usuario
        cursor.execute(
            "INSERT INTO usuario (email, nombre_usuario, contrasena, rol) VALUES (?, ?, ?, ?)",
            (email, nombre_usuario, contrasena, rol)
        )
        id_usuario = cursor.lastrowid  # Obtener el ID del usuario recién creado

        # Insertar en la tabla alumno o entrenador según el rol
        if rol == 1:  # Alumno
            cursor.execute(
                """
                INSERT INTO alumno (id_usuario, apellido, nombre, edad, id_pais, sexo, fecha_nacimiento, biografia)
                VALUES (?, 'NULL', 'NULL', NULL, NULL, 'NULL', NULL, 'NULL')
                """,
                (id_usuario,)
            )
        elif rol == 2:  # Entrenador
            cursor.execute(
                """
                INSERT INTO entrenador (id_usuario, apellido, nombre, edad, id_pais, sexo, fecha_nacimiento, biografia)
                VALUES (?, 'NULL', 'NULL', NULL, NULL, 'NULL', NULL, 'NULL')
                """,
                (id_usuario,)
            )

        conn.commit()  # Confirmar los cambios

    except Exception as e:
        conn.rollback()  # Revertir cambios si algo falla
        raise Exception(f"Error al insertar usuario: {str(e)}.")  # Propagar el error

    finally:
        conn.close()