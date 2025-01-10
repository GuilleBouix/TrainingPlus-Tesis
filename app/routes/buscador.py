from flask import Blueprint, render_template, request, session, jsonify
from app.utils.conexion import conexion_basedatos
from app.utils.helpers import login_required, verificar_formulario_completo
import os



buscador_bp = Blueprint('buscar', __name__)



@buscador_bp.route('/buscador', methods=['GET'])
@login_required
@verificar_formulario_completo
def buscador():
    query = request.args.get('query', '')  # Búsqueda general
    tipo = request.args.get('tipo', '')    # Filtro por rol
    pais = request.args.get('pais', '')    # Filtro por país
    sexo = request.args.get('sexo', '')    # Filtro por sexo

    connection = conexion_basedatos()
    cursor = connection.cursor()

    # Base de la consulta SQL
    base_query = """
        SELECT u.id_usuario, u.nombre_usuario, u.rol, a.nombre, a.apellido, a.foto_perfil, p.nombre, p.codigo_iso, a.sexo
        FROM usuario u
        LEFT JOIN alumno a ON u.id_usuario = a.id_usuario
        LEFT JOIN pais p ON a.id_pais = p.id_pais
        WHERE (u.nombre_usuario LIKE ? OR a.nombre LIKE ? OR a.apellido LIKE ? OR p.nombre LIKE ?)
    """
    filters = ['%' + query + '%'] * 4  # Parámetros para la búsqueda general

    # Aplicar filtros adicionales
    if tipo:
        base_query += " AND u.rol = ?"
        filters.append(tipo)
    if pais:
        base_query += " AND a.id_pais = ?"
        filters.append(pais)
    if sexo:
        base_query += " AND a.sexo = ?"
        filters.append(sexo)

    cursor.execute(base_query, filters)
    resultados = cursor.fetchall()

    # Obtener lista de países para el filtro
    cursor.execute("SELECT id_pais, nombre FROM pais")
    paises = cursor.fetchall()

    # Obtener lista de países para mostrar los códigos ISO
    cursor.execute("SELECT id_pais, codigo_iso FROM pais")
    paises_iso = cursor.fetchall()

    connection.close()

    return render_template(
        'buscador.html',
        query=query,
        tipo=tipo,
        pais=pais,
        sexo=sexo,
        resultados=resultados,
        paises=paises,
        paises_iso=paises_iso
    )



@buscador_bp.route('/datos_usuario/<int:id_usuario>', methods=['GET'])
@login_required
def obtener_datos_usuario(id_usuario):
    connection = conexion_basedatos()
    cursor = connection.cursor()

    # Consultar la tabla usuario
    cursor.execute("""
        SELECT u.email, u.nombre_usuario, u.rol
        FROM usuario u
        WHERE u.id_usuario = ?
    """, (id_usuario,))
    usuario = cursor.fetchone()

    # Consultar la tabla alumno
    cursor.execute("""
        SELECT a.nombre, a.apellido, a.id_pais, a.sexo, a.biografia, a.foto_perfil, a.instagram, a.facebook, a.telefono
        FROM alumno a
        WHERE a.id_usuario = ?
    """, (id_usuario,))
    alumno = cursor.fetchone()

    # Consultar el nombre del país
    cursor.execute("""
        SELECT p.nombre
        FROM pais p
        WHERE p.id_pais = ?
    """, (alumno[2],))  # Obtener el nombre del país según el id_pais
    pais = cursor.fetchone()

    connection.close()

    if usuario and alumno and pais:
        # Combinar los datos de ambas tablas en un solo diccionario
        datos_usuario = {
            'email': usuario[0],
            'nombre_usuario': usuario[1],
            'rol': usuario[2],
            'nombre': alumno[0],
            'apellido': alumno[1],
            'id_pais': pais[0],  # Ahora mostramos el nombre del país
            'sexo': alumno[3],
            'biografia': alumno[4],
            'foto_perfil': alumno[5],
            'instagram': alumno[6],
            'facebook': alumno[7],
            'telefono': alumno[8]
        }
        return jsonify(datos_usuario)
    else:
        return jsonify({'error': 'Usuario no encontrado'}), 404
