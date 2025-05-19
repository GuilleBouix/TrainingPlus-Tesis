from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.helpers import login_required
from app.utils.conexion import conexion_basedatos
from datetime import date, timedelta


suscripcion_bp = Blueprint('suscripcion', __name__)


def confirmar_suscripcion():
    try:
        # Obtener el ID del usuario de la sesión
        id_usuario = session.get('id_usuario')
        rol = session.get('rol')
        
        # Verificar que el usuario es un entrenador
        if rol != 2:
            flash('Solo los entrenadores pueden suscribirse', 'error')
            return redirect(url_for('suscripcion.suscripcion'))

        # Obtener fechas
        fecha_actual = date.today()
        fecha_fin = fecha_actual + timedelta(days=30)  # 1 mes de suscripción

        # Actualizar la base de datos
        conn = conexion_basedatos()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE usuario 
            SET fecha_inicio_suscripcion = ?, 
                fecha_fin_suscripcion = ?, 
                estado_suscripcion = 1 
            WHERE id_usuario = ?
        """, (fecha_actual, fecha_fin, id_usuario))
        
        conn.commit()
        conn.close()

        # Actualizar la sesión
        session['estado_suscripcion'] = 1
        flash('Suscripción confirmada con éxito', 'success')
        
        # Redirigir al dashboard
        return redirect(url_for('entrenamiento.entrenamiento'))
    
    except Exception as e:
        flash(f'Error al confirmar la suscripción: {str(e)}', 'error')
        return redirect(url_for('suscripcion.suscripcion'))
    

# Ruta de Entrenamiento
@suscripcion_bp.route('/suscripcion', methods=['GET', 'POST'])
@login_required
def suscripcion():
    if request.method == 'POST':
        # Procesar la confirmación de suscripción
        return confirmar_suscripcion()
    
    # Obtener paises para el formulario
    conn = conexion_basedatos()
    cursor = conn.cursor()
    cursor.execute("SELECT id_pais, nombre FROM pais")
    paises = cursor.fetchall()
    conn.close()


    return render_template('suscripcion.html', paises=paises)