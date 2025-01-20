from flask import Blueprint, render_template, request, session, jsonify, redirect, flash, url_for
from app.utils.conexion import conexion_basedatos
from app.utils.helpers import login_required, verificar_formulario_completo
import os



notificaciones_bp = Blueprint('notificaciones', __name__)



@notificaciones_bp.route('/enviar_solicitud/<int:id_usuario_destino>', methods=['POST'])
@login_required
def enviar_solicitud(id_usuario_destino):
    # Obtener el id del usuario actual (entrenador)
    id_usuario_origen = session['id_usuario']  # Asegúrate de que la sesión tenga el id del usuario
    
    # Datos de la notificación
    tipo = 'solicitud'
    estado = 'pendiente'
    mensaje = 'El entrenador ha solicitado conectarse contigo.'

    # Registrar la notificación en la base de datos
    try:
        conexion = conexion_basedatos()
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO notificaciones (id_usuario_origen, id_usuario_destino, tipo, estado, mensaje, fecha)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (id_usuario_origen, id_usuario_destino, tipo, estado, mensaje))
        conexion.commit()
        conexion.close()
    except Exception as e:
        print(f"Error al registrar la notificación: {e}")
        return redirect(url_for('usuario.html'))  # Manejo de errores: redirige al usuario o muestra un error

    # Opcional: mensaje de éxito o redirección
    flash("Solicitud de conexión enviada correctamente.", "success")
    return redirect(url_for('usuario.usuario', id_usuario=session.get('id_usuario'))) # Redirige a donde prefieras



@notificaciones_bp.route('/obtener_notificaciones', methods=['GET'])
@login_required
def obtener_notificaciones():
    id_usuario = session['id_usuario']  # Obtener el id del usuario actual
    try:
        conexion = conexion_basedatos()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT id_notificacion, id_usuario_origen, id_usuario_destino, tipo, estado, mensaje, fecha
            FROM notificaciones
            WHERE id_usuario_destino = ?
            ORDER BY fecha DESC
        """, (id_usuario,))
        # Obtener las filas como una lista de diccionarios
        notificaciones = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
        conexion.close()
    except Exception as e:
        print(f"Error al cargar notificaciones: {e}")
        notificaciones = []

    return jsonify(notificaciones)  # Retornamos las notificaciones en formato JSON



@notificaciones_bp.route('/obtener_count_notificaciones', methods=['GET'])
@login_required
def obtener_count_notificaciones():
    id_usuario = session['id_usuario']  # Obtener el id del usuario actual
    try:
        conexion = conexion_basedatos()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM notificaciones 
            WHERE id_usuario_destino = ? AND estado = 'pendiente'
        """, (id_usuario,))
        
        # Obtener el conteo de notificaciones pendientes
        count_notificaciones = cursor.fetchone()[0]
        conexion.close()
    except Exception as e:
        print(f"Error al contar las notificaciones: {e}")
        count_notificaciones = 0

    return jsonify({'count': count_notificaciones})  # Retornamos el conteo de notificaciones




@notificaciones_bp.route('/actualizar_notificacion/<int:id_notificacion>', methods=['POST'])
@login_required
def actualizar_notificacion(id_notificacion):
    nuevo_estado = request.form.get('estado')  # 'aceptada' o 'rechazada'
    try:
        conexion = conexion_basedatos()
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE notificaciones
            SET estado = ?
            WHERE id_notificacion = ?
        """, (nuevo_estado, id_notificacion))
        conexion.commit()
        conexion.close()
    except Exception as e:
        print(f"Error al actualizar notificación: {e}")
        return jsonify({'success': False}), 500

    return jsonify({'success': True})