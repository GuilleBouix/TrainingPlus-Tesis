from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.helpers import login_required, verificar_formulario_completo, verificar_suscripcion
from app.utils.conexion import conexion_basedatos
from datetime import date


opciones_bp = Blueprint('opciones', __name__)


# Obtener datos del usuario para el formulario de soporte
def obtener_datos_usuario():
    try:
        if 'id_usuario' not in session or 'rol' not in session:
            return None
        
        id_usuario = session['id_usuario']
        rol = session['rol']
        
        conn = conexion_basedatos()
        cursor = conn.cursor()
        
        # Consulta para obtener el email (siempre de la tabla usuario)
        cursor.execute(
            "SELECT email FROM usuario WHERE id_usuario = ?",
            (id_usuario,)
        )
        usuario_data = cursor.fetchone()
        
        if not usuario_data:
            return None
        
        email = usuario_data[0]
        
        # Consulta para nombre y apellido según el rol
        if rol == 1:  # Alumno
            cursor.execute(
                "SELECT nombre, apellido FROM alumno WHERE id_usuario = ?",
                (id_usuario,)
            )
        elif rol == 2:  # Entrenador
            cursor.execute(
                "SELECT nombre, apellido FROM entrenador WHERE id_usuario = ?",
                (id_usuario,)
            )
        else:
            return {'email': email, 'nombre_completo': ''}
        
        datos_personales = cursor.fetchone()
        conn.close()
        
        if datos_personales:
            nombre, apellido = datos_personales
            nombre_completo = f"{nombre} {apellido}" if nombre and apellido else nombre or apellido or ''
        else:
            nombre_completo = ''
        
        return {
            'email': email,
            'nombre_completo': nombre_completo.strip()
        }
    except Exception as e:
        print(f"Error al obtener datos del usuario: {str(e)}")
        flash(f"Error al obtener datos para soporte: {str(e)}", 'error')
        
        return None


# Ruta de Opciones
@opciones_bp.route('/opciones', methods=['GET', 'POST'])
@login_required
def opciones():
    # Obtener datos para el formulario de soporte
    datos_soporte = obtener_datos_usuario()

    return render_template('opciones.html', 
                           datos_soporte=datos_soporte)