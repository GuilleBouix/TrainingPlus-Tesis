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
        
        # print(f"Intentando enviar solicitud de {id_usuario_origen} a {id_usuario_destino}")

        cursor.execute("""
            SELECT rol FROM usuario WHERE id_usuario = ?
        """, (id_usuario_origen,))
        rol_origen = cursor.fetchone()

        if rol_origen[0] != 2:  # Si el origen no es un entrenador
            print("El usuario no es entrenador.")
            flash("Solo los entrenadores pueden enviar solicitudes.", "error")
            return redirect(url_for('usuario.usuario', id_usuario=id_usuario_origen))

        # Generar un token único
        token = secrets.token_urlsafe(16)
        # print(f"Token generado: {token}")

        # Generar la fecha sin segundos ni microsegundos
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



# Ruta para listar las solicitudes pendientes
@notificaciones_bp.route('/solicitudes', methods=['GET'])
@login_required
def listar_solicitudes():
    id_usuario = session['id_usuario']

    conexion = conexion_basedatos()
    cursor = conexion.cursor()

    # Obtener solicitudes pendientes
    cursor.execute("""
        SELECT v.id_vinculacion, u.nombre_usuario, v.fecha_solicitud 
        FROM vinculaciones v
        JOIN usuario u ON v.id_usuario_origen = u.id_usuario
        WHERE v.id_usuario_destino = ? AND v.estado = 'pendiente'
    """, (id_usuario,))
    solicitudes = cursor.fetchall()

    # Obtener notificaciones
    cursor.execute("""
        SELECT id_notificacion, mensaje, fecha, leida
        FROM notificaciones
        WHERE id_usuario = ?
        ORDER BY fecha DESC
    """, (id_usuario,))
    notificaciones = cursor.fetchall()

    conexion.close()

    # Formatear solicitudes pendientes
    solicitudes_formateadas = []
    for solicitud in solicitudes:
        id_vinculacion = solicitud[0]
        nombre_usuario = solicitud[1]
        fecha_solicitud = solicitud[2]

        # Convertir y formatear la fecha
        fecha_obj = datetime.strptime(fecha_solicitud, "%Y-%m-%d %H:%M")
        fecha_formateada = fecha_obj.strftime("%d/%m/%Y - %H:%M")

        solicitudes_formateadas.append({
            'id_vinculacion': id_vinculacion,
            'nombre_usuario': nombre_usuario,
            'fecha_solicitud': fecha_formateada
        })

    # Formatear notificaciones
    notificaciones_formateadas = []
    for notificacion in notificaciones:
        id_notificacion = notificacion[0]
        mensaje = notificacion[1]
        fecha = notificacion[2]
        leida = bool(notificacion[3])  # Convertir 0/1 a False/True

        # Convertir y formatear la fecha
        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S")
        fecha_formateada = fecha_obj.strftime("%d/%m/%Y - %H:%M")

        notificaciones_formateadas.append({
            'id_notificacion': id_notificacion,
            'mensaje': mensaje,
            'fecha': fecha_formateada,
            'leida': leida
        })

    return render_template(
        'notificaciones.html',
        solicitudes=solicitudes_formateadas,
        notificaciones=notificaciones_formateadas
    )



# Ruta para aceptar una solicitud
@notificaciones_bp.route('/aceptar_vinculo/<token>', methods=['GET', 'POST'])
@login_required
def aceptar_vinculo(token):
    id_usuario = session['id_usuario']
    try:
        conexion = conexion_basedatos()
        cursor = conexion.cursor()

        # Buscar la invitación usando el token
        cursor.execute("""
            SELECT id_usuario_origen, id_usuario_destino, estado
            FROM vinculaciones
            WHERE token = ? AND id_usuario_destino = ?
        """, (token, id_usuario))

        vinculo = cursor.fetchone()

        if vinculo and vinculo[2] == 'pendiente':  # Solo aceptar si el estado es pendiente
            if request.method == 'POST':
                # Si el alumno acepta la invitación
                if 'aceptar' in request.form:
                    # Actualizamos el estado del vínculo
                    cursor.execute("""
                        UPDATE vinculaciones
                        SET estado = 'aceptado'
                        WHERE token = ?
                    """, (token,))
                    
                    # Crear el entrenamiento en la tabla entrenamiento
                    id_entrenador = vinculo[0]
                    id_alumno = vinculo[1]
                    duracion_semanas = 12  # Ejemplo: duración por defecto de 12 semanas
                    fecha_inicio = datetime.datetime.now()  # La fecha actual

                    cursor.execute("""
                        INSERT INTO entrenamiento (id_entrenador, id_alumno, duracion_semanas, fecha_inicio)
                        VALUES (?, ?, ?, ?)
                    """, (id_entrenador, id_alumno, duracion_semanas, fecha_inicio))
                    
                    conexion.commit()

                # Si el alumno rechaza la invitación
                elif 'rechazar' in request.form:
                    cursor.execute("""
                        UPDATE vinculaciones
                        SET estado = 'rechazado'
                        WHERE token = ?
                    """, (token,))

                conexion.commit()

                flash("Vinculación y entrenamiento actualizados correctamente.", "success")
                return redirect(url_for('usuario.usuario', id_usuario=id_usuario))

        else:
            flash("Este vínculo no es válido o ya ha sido procesado.", "error")
            return redirect(url_for('usuario.usuario', id_usuario=id_usuario))

        conexion.close()
    except Exception as e:
        print(f"Error al aceptar o rechazar el vínculo: {e}")
        flash("Error al procesar la invitación.", "error")
        return redirect(url_for('usuario.usuario', id_usuario=id_usuario))
    


# Ruta para responder a una solicitud
@notificaciones_bp.route('/responder_solicitud/<int:id_vinculacion>', methods=['POST'])
@login_required
def responder_solicitud(id_vinculacion):
    respuesta = request.form.get('respuesta')
    id_usuario_destino = session['id_usuario']

    try:
        conexion = conexion_basedatos()
        cursor = conexion.cursor()

        # Obtener el entrenador (origen) asociado a esta solicitud
        cursor.execute("""
            SELECT id_usuario_origen 
            FROM vinculaciones 
            WHERE id_vinculacion = ?
        """, (id_vinculacion,))
        resultado = cursor.fetchone()

        if not resultado:
            flash("Solicitud no encontrada.", "error")
            return redirect(url_for('notificaciones.listar_solicitudes'))

        id_usuario_origen = resultado[0]

        if respuesta == 'aceptar':
            # Cambiar el estado de la solicitud a 'aceptada'
            cursor.execute("""
                UPDATE vinculaciones
                SET estado = 'aceptada'
                WHERE id_vinculacion = ?
            """, (id_vinculacion,))

            # Crear notificación para el entrenador
            mensaje = f"El usuario @{session['nombre_usuario']} aceptó tu solicitud de conexión."
            cursor.execute("""
                INSERT INTO notificaciones (id_usuario, mensaje)
                VALUES (?, ?)
            """, (id_usuario_origen, mensaje))

            flash("Solicitud aceptada y notificación enviada al entrenador.", "success")

        elif respuesta == 'rechazar':
            # Eliminar la solicitud de la tabla
            cursor.execute("""
                DELETE FROM vinculaciones
                WHERE id_vinculacion = ?
            """, (id_vinculacion,))

            # Crear notificación para el entrenador sobre el rechazo
            mensaje_rechazo = f"El usuario @{session['nombre_usuario']} rechazó tu solicitud de conexión."
            cursor.execute("""
                INSERT INTO notificaciones (id_usuario, mensaje)
                VALUES (?, ?)
            """, (id_usuario_origen, mensaje_rechazo))

            flash("Solicitud rechazada y notificación enviada al entrenador.", "info")

        conexion.commit()
        conexion.close()
        return redirect(url_for('notificaciones.listar_solicitudes'))

    except Exception as e:
        print(f"Error al procesar la solicitud: {e}")
        flash("Error al procesar la solicitud.", "error")
        return redirect(url_for('notificaciones.listar_solicitudes'))



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

        flash("Notificaciones y vinculaciones eliminadas correctamente.", "success")
        return redirect(url_for('notificaciones.listar_solicitudes'))

    except Exception as e:
        print(f"Error al eliminar notificaciones y vinculaciones: {e}")
        flash("Error al eliminar las notificaciones y vinculaciones.", "error")
        return redirect(url_for('notificaciones.listar_solicitudes'))