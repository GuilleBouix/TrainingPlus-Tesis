from flask import session, redirect, url_for, flash
from app.utils.conexion import conexion_basedatos
from functools import wraps
from datetime import date
import sqlite3


# Decorador para verificar si hay una sesión activa
def login_required(f):
    @wraps(f)
    def funcion_decorador(*args, **kwargs):
        # Verifica si hay una sesión activa
        if 'id_usuario' not in session:
            flash('Inicia sesión para acceder a esta página.', 'error')
            return redirect(url_for('auth.login'))  # Redirige al login si no hay sesión
        
        return f(*args, **kwargs)
    return funcion_decorador


def cuestionario_completo_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'id_usuario' not in session:
            return redirect(url_for('auth.login'))
        
        # Permitir acceso directo a entrenadores
        if session.get('rol') == 2:
            return f(*args, **kwargs)
        
        # Verificación para alumnos
        conn = conexion_basedatos()
        tiene_cuestionario = conn.execute("""
            SELECT 1 FROM cuestionario c
            JOIN alumno a ON c.id_alumno = a.id_alumno
            WHERE a.id_usuario = ?
            LIMIT 1
        """, (session['id_usuario'],)).fetchone() is not None
        conn.close()
        
        return f(*args, **kwargs) if tiene_cuestionario else redirect(url_for('cuestionario.cuestionario'))
    
    return decorated_function

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


# Verificar si el entrenador tiene una suscripcion activa
def verificar_suscripcion(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        conn = conexion_basedatos()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        id_usuario = session.get('id_usuario')

        if not id_usuario:
            return redirect(url_for('auth.login'))

        # Traemos los datos del usuario
        cursor.execute("SELECT rol, estado_suscripcion, fecha_fin_suscripcion FROM usuario WHERE id_usuario = ?", (id_usuario,))
        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            # Solo se aplica a entrenadores
            if usuario['rol'] == 2:
                fecha_fin = usuario['fecha_fin_suscripcion']
                estado = usuario['estado_suscripcion']

                if fecha_fin:
                    fecha_fin = date.fromisoformat(fecha_fin)
                    dias_vencido = (date.today() - fecha_fin).days
                else:
                    dias_vencido = 999  # si no tiene fecha, está vencido

                if estado != 1 or dias_vencido > 30:
                    return redirect(url_for('suscripcion.suscripcion'))

        return f(*args, **kwargs)

    return decorated_function


# Decorador para verificar si el usuario es un alumno y tiene una rutina asignada
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