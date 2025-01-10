from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.utils.conexion import conexion_basedatos
from app.utils.helpers import login_required, verificar_formulario_completo
from werkzeug.utils import secure_filename
from PIL import Image
import os



perfil_bp = Blueprint('perfil', __name__)



# Configuración de la carpeta de subida de fotos
UPLOAD_FOLDER = 'app/static/uploads/users'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
DEFAULT_PROFILE_PICTURE = 'profile.webp'



# Función para verificar las extensiones permitidas
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



# Función para comprimir y convertir a .webp
def compress_and_convert_to_webp(file, id_usuario):
    # Define el directorio de almacenamiento
    uploads_dir = os.path.join('app', 'static', 'uploads', 'users')

    # Genera el nombre de archivo basado en el id_usuario
    filename = f'user{id_usuario}-profile.webp'

    # Define el camino completo donde se guardará la imagen
    file_path = os.path.join(uploads_dir, filename)

    # Abre la imagen con PIL y comprímela a formato webp
    image = Image.open(file)

    # Obtener las dimensiones originales
    width, height = image.size

    # Redimensionar la imagen a la mitad del tamaño original
    new_width = width // 2
    new_height = height // 2

    # Redimensionar la imagen
    image = image.resize((new_width, new_height))

    image = image.convert("RGB")  # Convertir la imagen a RGB si es necesario
    image.save(file_path, format="WEBP", quality=60)  # Guarda con calidad 60%

    return filename



# Ruta de Perfil
@perfil_bp.route('/perfil/@<nombre_usuario>', methods=['GET', 'POST'])
@login_required
@verificar_formulario_completo
def perfil(nombre_usuario):
    if 'nombre_usuario' not in session or session['nombre_usuario'] != nombre_usuario:
        flash("No tienes permiso para acceder a este perfil.", 'error')
        return redirect(url_for('entrenamiento.entrenamiento'))

    # Conexión a la base de datos para obtener los países
    db = conexion_basedatos()
    cursor = db.cursor()
    cursor.execute("SELECT id_pais, nombre FROM pais")
    paises = cursor.fetchall()

    # Obtener datos actuales del usuario
    conn = conexion_basedatos()
    cursor = conn.cursor()

    # Consultar datos del usuario (usuarios y alumno, incluyendo el rol)
    cursor.execute("""
        SELECT u.email, u.nombre_usuario, a.id_usuario, a.apellido, a.nombre, 
               a.fecha_nacimiento, a.edad, a.id_pais, a.sexo, a.biografia, a.foto_perfil,
               a.instagram, a.facebook, a.telefono, u.rol
        FROM usuario u
        LEFT JOIN alumno a ON u.id_usuario = a.id_usuario
        WHERE u.nombre_usuario = ?
    """, (nombre_usuario,))
    usuario_data = cursor.fetchone()

    if not usuario_data:
        flash("Usuario no encontrado.", 'error')
        return redirect(url_for('entrenamiento.entrenamiento'))

    # Datos del formulario
    if request.method == 'POST':
        email = request.form['email']
        nuevo_nombre_usuario = request.form['nombre_usuario']
        apellido = request.form['apellido']
        nombre = request.form['nombre']
        fecha_nacimiento = request.form['fecha_nacimiento']
        edad = request.form['edad']
        pais = request.form['pais']
        sexo = request.form['sexo']
        biografia = request.form['biografia']

        # Procesar la foto de perfil
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                # Accede correctamente al 'id_usuario'
                id_usuario = usuario_data['id_usuario']  # Acceso correcto con nombre de columna

                if id_usuario:
                    foto_perfil_filename = compress_and_convert_to_webp(file, id_usuario)

                    if foto_perfil_filename:
                        cursor.execute("""
                            UPDATE alumno
                            SET foto_perfil = ?
                            WHERE id_usuario = ?
                        """, (foto_perfil_filename, id_usuario))
                        conn.commit()
                    else:
                        flash('Error al procesar la foto de perfil', 'error')
                else:
                    flash('No se encontró el id del usuario', 'error')


        try:
            # Actualizar los datos del usuario
            cursor.execute("""
                UPDATE usuario 
                SET email = ?, nombre_usuario = ?
                WHERE nombre_usuario = ?
            """, (email, nuevo_nombre_usuario, nombre_usuario))

            # Actualizar la tabla `alumno`
            cursor.execute("""
                UPDATE alumno
                SET apellido = ?, nombre = ?, fecha_nacimiento = ?, 
                    edad = ?, id_pais = ?, sexo = ?, biografia = ?
                WHERE id_usuario = (SELECT id_usuario FROM usuario WHERE nombre_usuario = ?)
            """, (apellido, nombre, fecha_nacimiento, edad, pais, sexo, biografia, nombre_usuario))

            conn.commit()
            flash("Perfil actualizado correctamente.", 'success')
            session['nombre_usuario'] = nuevo_nombre_usuario  # Actualizar la sesión si cambia el nombre de usuario
            return redirect(url_for('perfil.perfil', nombre_usuario=nuevo_nombre_usuario))
        except Exception as e:
            conn.rollback()
            flash("Ocurrió un error al actualizar el perfil: " + str(e), 'error')
        finally:
            cursor.close()
            conn.close()

    # Renderizar plantilla con los datos actuales del usuario
    return render_template('perfil.html', nombre_usuario=nombre_usuario, usuario_data=usuario_data, paises=paises)



# Ruta para actualizar las Redes Sociales
@perfil_bp.route('/actualizar_redes', methods=['POST'])
@login_required
def actualizar_redes():
    data = request.get_json()
    instagram = data.get('instagram')
    facebook = data.get('facebook')
    telefono = data.get('telefono')

    if not instagram or not facebook or not telefono:
        return jsonify({'success': False, 'message': 'Todos los campos son obligatorios.'})

    try:
        conn = conexion_basedatos()
        cursor = conn.cursor()
        id_usuario = session.get('id_usuario')

        if not id_usuario:
            return jsonify({'success': False, 'message': 'Usuario no autenticado.'})

        cursor.execute("""
            UPDATE alumno
            SET instagram = ?, facebook = ?, telefono = ?
            WHERE id_usuario = ?
        """, (instagram, facebook, telefono, id_usuario))

        conn.commit()
        flash('Redes actualizadas correctamente.', 'success')
        return jsonify({'success': True})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error al actualizar redes sociales: {str(e)}'})

    finally:
        cursor.close()
        conn.close()