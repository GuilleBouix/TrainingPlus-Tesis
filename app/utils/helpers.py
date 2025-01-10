from flask import session, redirect, url_for, flash
from functools import wraps
from app.utils.conexion import conexion_basedatos



def login_required(f):
    @wraps(f)
    def funcion_decorador(*args, **kwargs):
        # Verificamos si hay una sesión activa
        if 'id_usuario' not in session:
            flash('Inicia sesión para acceder a esta página.', 'error')
            return redirect(url_for('auth.login'))  # Redirigimos al login si no hay sesión
        
        return f(*args, **kwargs)  # Continuamos con la ejecución de la ruta
    return funcion_decorador



def entrenador_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rol') != 2:  # Solo permite acceso a entrenadores
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function



from functools import wraps
from flask import session, redirect, url_for
from app.utils.conexion import conexion_basedatos

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




def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions



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