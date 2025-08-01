from flask import Blueprint, render_template, request, session, redirect, flash, url_for
from app.utils.conexion import conexion_basedatos
from app.utils.helpers import login_required
from datetime import datetime
import secrets


notificaciones_bp = Blueprint('notificaciones', __name__)


# Ruta de Enviar Solicitud
@notificaciones_bp.route('/enviar_solicitud/<int:id_usuario_destino>', methods=['POST'])
@login_required
def enviar_solicitud(id_usuario_destino):
    id_usuario_origen = session['id_usuario']

    try:
        # Verificar que el origen sea un entrenador
        conexion = conexion_basedatos()
        cursor = conexion.cursor()
        
        cursor.execute("""
            SELECT rol FROM usuario WHERE id_usuario = ?
        """, (id_usuario_origen,))
        rol_origen = cursor.fetchone()

        if rol_origen[0] != 2:
            flash("Solo los entrenadores pueden enviar solicitudes.", "error")
            return redirect(url_for('usuario.usuario', id_usuario=id_usuario_origen))

        # Generar un token único
        token = secrets.token_urlsafe(16)

        # Generar la fecha y hora
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Insertar en la tabla vinculaciones
        cursor.execute("""
            INSERT INTO vinculaciones (id_usuario_origen, id_usuario_destino, estado, token, fecha_solicitud)
            VALUES (?, ?, 'pendiente', ?, ?)
        """, (id_usuario_origen, id_usuario_destino, token, fecha_actual))

        conexion.commit()
        conexion.close()

        flash("Solicitud de conexión enviada correctamente.", "success")
        return redirect(url_for('usuario.usuario', id_usuario=id_usuario_destino))

    except Exception as e:
        flash("Error al enviar la solicitud. Intente nuevamente.", "error")

        return redirect(url_for('usuario.usuario', id_usuario=id_usuario_origen))


# Ruta para cancelar una solicitud pendiente
@notificaciones_bp.route('/cancelar_solicitud/<int:id_usuario_destino>', methods=['POST'])
@login_required
def cancelar_solicitud(id_usuario_destino):
    id_usuario_origen = session['id_usuario']

    try:
        conexion = conexion_basedatos()
        cursor = conexion.cursor()

        # Verificar que existe una solicitud pendiente
        cursor.execute("""
            DELETE FROM vinculaciones
            WHERE id_usuario_origen = ? AND id_usuario_destino = ? AND estado = 'pendiente'
        """, (id_usuario_origen, id_usuario_destino))

        conexion.commit()
        conexion.close()

        flash("Solicitud cancelada correctamente.", "success")
        return redirect(url_for('usuario.usuario', id_usuario=id_usuario_destino))

    except Exception as e:
        print(f"Error al cancelar solicitud: {e}")
        flash("Error al cancelar la solicitud.", "error")
        return redirect(url_for('usuario.usuario', id_usuario=id_usuario_origen))


# Ruta para eliminar una conexión existente
@notificaciones_bp.route('/eliminar_conexion/<int:id_usuario_destino>', methods=['POST'])
@login_required
def eliminar_conexion(id_usuario_destino):
    id_usuario_origen = session['id_usuario']

    try:
        conexion = conexion_basedatos()
        cursor = conexion.cursor()

        # Eliminar la conexión aceptada
        cursor.execute("""
            DELETE FROM vinculaciones
            WHERE id_usuario_origen = ? AND id_usuario_destino = ? AND estado = 'aceptada'
        """, (id_usuario_origen, id_usuario_destino))

        # Crear notificación para el alumno
        cursor.execute("""
            SELECT nombre_usuario FROM usuario WHERE id_usuario = ?
        """, (id_usuario_origen,))
        nombre_entrenador = cursor.fetchone()[0]

        mensaje = f"El entrenador @{nombre_entrenador} ha eliminado tu conexión."
        cursor.execute("""
            INSERT INTO notificaciones (id_usuario, mensaje)
            VALUES (?, ?)
        """, (id_usuario_destino, mensaje))

        conexion.commit()
        conexion.close()

        flash("Conexión eliminada correctamente.", "success")
        return redirect(url_for('usuario.usuario', id_usuario=id_usuario_destino))

    except Exception as e:
        print(f"Error al eliminar conexión: {e}")
        flash("Error al eliminar la conexión.", "error")
        return redirect(url_for('usuario.usuario', id_usuario=id_usuario_origen))


# Ruta para listar las solicitudes pendientes
@notificaciones_bp.route('/notificaciones', methods=['GET'])
@login_required
def listar_solicitudes():
    id_usuario = session['id_usuario']
    orden = request.args.get('orden', default='desc', type=str)  # Nuevo: obtener parámetro de orden

    conexion = conexion_basedatos()
    cursor = conexion.cursor()

    # Obtener solicitudes pendientes
    cursor.execute("""
        SELECT v.id_vinculacion, u.nombre_usuario, v.fecha_solicitud 
        FROM vinculaciones v
        JOIN usuario u ON v.id_usuario_origen = u.id_usuario
        WHERE v.id_usuario_destino = ? AND v.estado = 'pendiente'
        ORDER BY v.fecha_solicitud DESC
    """, (id_usuario,))
    solicitudes = cursor.fetchall()

    # Obtener notificaciones con ordenamiento dinámico
    order_clause = "DESC" if orden == 'desc' else "ASC"  # Determinar el orden
    cursor.execute(f"""
        SELECT id_notificacion, mensaje, fecha, id_entrenamiento
        FROM notificaciones
        WHERE id_usuario = ?
        ORDER BY fecha {order_clause}
    """, (id_usuario,))
    notificaciones = cursor.fetchall()

    conexion.close()

    # Formatear solicitudes pendientes
    solicitudes_formateadas = []
    for solicitud in solicitudes:
        solicitudes_formateadas.append({
            'id_vinculacion': solicitud[0],
            'nombre_usuario': solicitud[1],
            'fecha_solicitud': datetime.strptime(solicitud[2], "%Y-%m-%d %H:%M").strftime("%d/%m/%Y - %H:%M")
        })

    # Formatear notificaciones
    notificaciones_formateadas = []
    for notificacion in notificaciones:
        notificaciones_formateadas.append({
            'id_notificacion': notificacion[0],
            'mensaje': notificacion[1],
            'fecha': datetime.strptime(notificacion[2], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y - %H:%M"),
            'id_entrenamiento': notificacion[3]
        })

    return render_template(
        'notificaciones.html',
        solicitudes=solicitudes_formateadas,
        notificaciones=notificaciones_formateadas,
        orden_actual=orden
    )


# Ruta para responder a una solicitud
@notificaciones_bp.route('/responder_solicitud/<int:id_vinculacion>', methods=['POST'])
@login_required
def responder_solicitud(id_vinculacion):
    respuesta = request.form.get('respuesta')
    id_usuario_destino = session['id_usuario']

    try:
        conexion = conexion_basedatos()
        cursor = conexion.cursor()

        # Obtener los datos de la vinculación
        cursor.execute("""
            SELECT id_usuario_origen, id_usuario_destino, estado 
            FROM vinculaciones 
            WHERE id_vinculacion = ? AND id_usuario_destino = ?
        """, (id_vinculacion, id_usuario_destino))
        resultado = cursor.fetchone()

        if not resultado:
            flash("Solicitud no encontrada.", "error")
            return redirect(url_for('notificaciones.listar_solicitudes'))

        id_usuario_origen = resultado[0]
        estado_actual = resultado[2]

        if estado_actual != 'pendiente':
            flash("Esta solicitud ya fue procesada.", "error")
            return redirect(url_for('notificaciones.listar_solicitudes'))

        if respuesta == 'aceptar':
            # Actualizar el estado a 'aceptada'
            cursor.execute("""
                UPDATE vinculaciones
                SET estado = 'aceptada'
                WHERE id_vinculacion = ?
            """, (id_vinculacion,))

            # Notificación para el entrenador
            cursor.execute("""
                SELECT nombre_usuario FROM usuario WHERE id_usuario = ?
            """, (id_usuario_destino,))
            nombre_alumno = cursor.fetchone()[0]

            mensaje = f"El usuario @{nombre_alumno} ha aceptado tu solicitud de conexión."
            cursor.execute("""
                INSERT INTO notificaciones (id_usuario, mensaje)
                VALUES (?, ?)
            """, (id_usuario_origen, mensaje))

            flash("Solicitud aceptada exitosamente.", "success")

        elif respuesta == 'rechazar':
            # Actualizar el estado a 'rechazada'
            cursor.execute("""
                UPDATE vinculaciones
                SET estado = 'rechazada'
                WHERE id_vinculacion = ?
            """, (id_vinculacion,))

            # Notificación para el entrenador
            cursor.execute("""
                SELECT nombre_usuario FROM usuario WHERE id_usuario = ?
            """, (id_usuario_destino,))
            nombre_alumno = cursor.fetchone()[0]

            mensaje = f"El usuario @{nombre_alumno} ha rechazado tu solicitud de conexión."
            cursor.execute("""
                INSERT INTO notificaciones (id_usuario, mensaje)
                VALUES (?, ?)
            """, (id_usuario_origen, mensaje))

            flash("Solicitud rechazada exitosamente.", "success")

        conexion.commit()
        conexion.close()
        return redirect(url_for('notificaciones.listar_solicitudes'))

    except Exception as e:
        print(f"Error al procesar la solicitud: {e}")
        flash("Error al procesar la solicitud.", "error")
        return redirect(url_for('notificaciones.listar_solicitudes'))


# Ruta para eliminar todas las notificaciones
@notificaciones_bp.route('/eliminar_notificaciones', methods=['POST'])
@login_required
def eliminar_notificaciones():
    tipo = request.form.get('tipo')
    id_usuario = session['id_usuario']

    try:
        conexion = conexion_basedatos()
        cursor = conexion.cursor()

        # Eliminar notificaciones
        cursor.execute("""
            DELETE FROM notificaciones
            WHERE id_usuario = ?
        """, (id_usuario,))

        conexion.commit()
        conexion.close()

        flash("Notificaciones eliminadas correctamente.", "success")
        return redirect(url_for('notificaciones.listar_solicitudes'))

    except Exception as e:
        flash("Error al eliminar las notificaciones.", "error")
        return redirect(url_for('notificaciones.listar_solicitudes'))
    

# Ruta para obtener la cantidad de notificaciones no leídas
@notificaciones_bp.route('/cantidad_notificaciones')
@login_required
def cantidad_notificaciones():
    id_usuario = session['id_usuario']
    rol_usuario = session.get('rol')

    conexion = conexion_basedatos()
    cursor = conexion.cursor()

    # Para entrenadores: contar solicitudes de vinculación pendientes
    total_vinculaciones = 0
    if rol_usuario == 2:
        cursor.execute("""
            SELECT COUNT(*) FROM vinculaciones 
            WHERE id_usuario_destino = ? AND estado = 'pendiente'
        """, (id_usuario,))
        total_vinculaciones = cursor.fetchone()[0]

    # Contar TODAS las notificaciones del usuario (sin filtro de 'leído')
    cursor.execute("""
        SELECT COUNT(*) FROM notificaciones 
        WHERE id_usuario = ?
    """, (id_usuario,))
    total_notificaciones = cursor.fetchone()[0]

    conexion.close()

    # Lógica para mostrar el contador
    total = total_vinculaciones + total_notificaciones
    total_mostrar = min(total, 9) if total > 0 else None
    
    return {"cantidad": total_mostrar}