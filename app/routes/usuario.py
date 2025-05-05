from flask import Blueprint, render_template, request, session, jsonify, abort
from app.utils.conexion import conexion_basedatos
from app.utils.helpers import login_required, verificar_formulario_completo
from datetime import datetime


usuario_bp = Blueprint('usuario', __name__)


# Función para formatear la fecha de nacimiento
def format_fecha(fecha):
    meses = [
        "01", "02", "03", "04", "05", "06",
        "07", "08", "09", "10", "11", "12"
    ]
    return f"{fecha.day}/{meses[fecha.month - 1]}/{fecha.year}"


# Función para verificar el estado de conexión
def verificar_estado_conexion(id_entrenador, id_alumno, cursor):
    cursor.execute("""
        SELECT estado 
        FROM vinculaciones 
        WHERE id_usuario_origen = ? AND id_usuario_destino = ?
        ORDER BY fecha_solicitud DESC
        LIMIT 1
    """, (id_entrenador, id_alumno))
    
    resultado = cursor.fetchone()
    return resultado[0] if resultado else None


# Ruta de Usuario
@usuario_bp.route('/usuario/<int:id_usuario>')
@login_required
def usuario(id_usuario):
    # Conectar a la base de datos
    connection = conexion_basedatos()
    cursor = connection.cursor()

    # Obtener los datos generales del usuario
    cursor.execute("""
        SELECT id_usuario, email, nombre_usuario, rol
        FROM usuario 
        WHERE id_usuario = ?
    """, (id_usuario,))
    usuario_data = cursor.fetchone()

    # Si el usuario no existe, devolver error 404
    if not usuario_data:
        abort(404)

    # Convertir usuario_data a diccionario
    usuario_data = dict(usuario_data)

    # Obtener datos específicos según el rol
    if usuario_data['rol'] == 1:  # Alumno
        cursor.execute("""
            SELECT id_alumno, apellido, nombre, edad, id_pais, sexo, fecha_nacimiento, biografia, 
                   foto_perfil, instagram, facebook, telefono 
            FROM alumno
            WHERE id_usuario = ?
        """, (id_usuario,))
        usuario_info = cursor.fetchone()
    elif usuario_data['rol'] == 2:  # Entrenador
        cursor.execute("""
            SELECT id_entrenador, apellido, nombre, edad, id_pais, sexo, fecha_nacimiento, biografia, 
                   foto_perfil, especializacion, experiencia, titulo, instituto, instagram, facebook, telefono 
            FROM entrenador
            WHERE id_usuario = ?
        """, (id_usuario,))
        usuario_info = cursor.fetchone()
    else:
        abort(404)

    # Si no se encuentra información adicional, devolver error 404
    if not usuario_info:
        abort(404)

    # Convertir usuario_info a diccionario
    usuario_info = dict(usuario_info)

    # Obtener el nombre del país
    cursor.execute("""
        SELECT nombre
        FROM pais
        WHERE id_pais = ?
    """, (usuario_info['id_pais'],))
    pais_data = cursor.fetchone()

    # Asignar el nombre del país
    usuario_info['id_pais'] = pais_data['nombre'] if pais_data else "Desconocido"

    # Formatear la fecha de nacimiento
    fecha_nacimiento = usuario_info['fecha_nacimiento']
    if fecha_nacimiento:
        usuario_info['fecha_nacimiento'] = format_fecha(datetime.strptime(fecha_nacimiento, '%Y-%m-%d'))

    # Capitalizar el género
    usuario_info['sexo'] = usuario_info['sexo'].capitalize() if usuario_info['sexo'] else "No especificado"

    # Convertir nombre y apellido a mayúsculas
    usuario_info['nombre'] = usuario_info['nombre'].upper()
    usuario_info['apellido'] = usuario_info['apellido'].upper()

    # Obtener los datos de la sesión actual
    id_usuario_sesion = session.get('id_usuario')

    # Verificar si el usuario de la sesión actual es un entrenador
    cursor.execute("""
        SELECT rol
        FROM usuario
        WHERE id_usuario = ?
    """, (id_usuario_sesion,))
    sesion_data = cursor.fetchone()
    es_entrenador = sesion_data and sesion_data['rol'] == 2

    # Verificar si el usuario de la sesión actual es un entrenador
    es_entrenador_perfil = usuario_data['rol'] == 2
    
    titulo_foto = None

    if es_entrenador_perfil:
        cursor.execute("""
            SELECT titulo_foto
            FROM entrenador
            WHERE id_usuario = ?
        """, (id_usuario,))
        titulo_data = cursor.fetchone()
        titulo_foto = titulo_data['titulo_foto'] if titulo_data and titulo_data['titulo_foto'] else None

    # Verificar estado de conexión si es un entrenador viendo perfil de alumno
    estado_conexion = None
    if es_entrenador and usuario_data['rol'] == 1 and usuario_data['id_usuario'] != id_usuario_sesion:
        estado_conexion = verificar_estado_conexion(id_usuario_sesion, id_usuario, cursor)

    # Cerrar la conexión a la base de datos
    cursor.close()
    connection.close()

    # Renderizar la plantilla con los datos procesados
    return render_template(
            'usuario.html', 
            usuario=usuario_data, 
            info=usuario_info,  
            id_usuario_sesion=id_usuario_sesion, 
            es_entrenador=es_entrenador,
            es_entrenador_perfil=es_entrenador_perfil,
            titulo_foto=titulo_foto,
            estado_conexion=estado_conexion
        )