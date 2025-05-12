from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.utils.helpers import login_required, verificar_formulario_completo
from app.utils.conexion import conexion_basedatos
from werkzeug.security import check_password_hash
from PIL import Image
import os


perfil_bp = Blueprint('perfil', __name__)


# Configuración de la carpeta de subida de fotos
UPLOAD_FOLDERS = {
    'users': 'app/static/uploads/users',
    'trainers': 'app/static/uploads/users',
    'studies': 'app/static/uploads/titles'
}


# Configuración de las extensiones permitidas
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
DEFAULT_PROFILE_PICTURE = 'profile.webp'


# Función para verificar las extensiones permitidas
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Función para comprimir y convertir a .webp
def compress_and_convert_to_webp(file, id_usuario, folder_type, filename_format):
    """
    Comprime y convierte una imagen a formato WEBP.
    :param file: Archivo de imagen subido
    :param id_usuario: ID del usuario/entrenador
    :param folder_type: Tipo de carpeta (users/trainers/studies)
    :param filename_format: Formato del nombre de archivo
    :return: Nombre del archivo guardado o None si falla
    """
    try:
        uploads_dir = UPLOAD_FOLDERS.get(folder_type)
        if not uploads_dir:
            raise ValueError("Tipo de carpeta no válido")

        # Asegurar que el directorio existe
        os.makedirs(uploads_dir, exist_ok=True)

        # Generar nombre de archivo
        filename = filename_format.format(id=id_usuario)
        file_path = os.path.join(uploads_dir, filename)

        # Procesar imagen
        with Image.open(file) as img:
            # Redimensionar manteniendo aspect ratio
            base_width = 800
            w_percent = (base_width / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))
            img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)

            # Convertir y guardar
            img.convert("RGB").save(file_path, "WEBP", quality=70)
        
        return filename

    except Exception as e:
        print(f"Error procesando imagen: {e}")
        return None


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

    # Consultar datos del usuario
    cursor.execute("""
        SELECT u.email, u.nombre_usuario, u.rol,
            -- Datos de Alumno
            a.id_usuario AS alumno_id_usuario, a.apellido AS alumno_apellido, a.nombre AS alumno_nombre, 
            a.fecha_nacimiento AS alumno_fecha_nacimiento, a.edad AS alumno_edad, a.id_pais AS alumno_id_pais, 
            a.sexo AS alumno_sexo, a.biografia AS alumno_biografia, a.foto_perfil AS alumno_foto_perfil,
            a.instagram AS alumno_instagram, a.facebook AS alumno_facebook, a.telefono AS alumno_telefono,
                   
            -- Datos de Entrenador
            e.id_usuario AS entrenador_id_usuario, e.apellido AS entrenador_apellido, e.nombre AS entrenador_nombre, 
            e.fecha_nacimiento AS entrenador_fecha_nacimiento, e.edad AS entrenador_edad, e.id_pais AS entrenador_id_pais, 
            e.sexo AS entrenador_sexo, e.biografia AS entrenador_biografia, e.foto_perfil AS entrenador_foto_perfil, 
            e.especializacion, e.disciplina, e.experiencia, e.titulo_foto, e.titulo, e.instituto, 
            e.instagram AS entrenador_instagram, e.facebook AS entrenador_facebook, e.telefono AS entrenador_telefono
        FROM usuario u
        LEFT JOIN alumno a ON u.id_usuario = a.id_usuario
        LEFT JOIN entrenador e ON u.id_usuario = e.id_usuario
        WHERE u.nombre_usuario = ?
    """, (nombre_usuario,))
    usuario_data = cursor.fetchone()

    # print("CLAVES DE usuario_data:", usuario_data.keys())

    # Verificar el rol del usuario
    rol_usuario = usuario_data['rol']
    id_usuario = usuario_data['alumno_id_usuario'] if rol_usuario == 1 else usuario_data['entrenador_id_usuario']


    if not usuario_data:
        flash("Usuario no encontrado.", 'error')
        return redirect(url_for('entrenamiento.entrenamiento'))

    # Datos del formulario
    if rol_usuario == 1:  # Rol de alumno
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
                    foto_perfil_filename = compress_and_convert_to_webp(
                        file, id_usuario, 'users', 'user{id}-profile.webp'
                    )
                    if foto_perfil_filename:
                        # Guardar en la base de datos
                        cursor.execute("""
                            UPDATE alumno
                            SET foto_perfil = ?
                            WHERE id_usuario = ?
                        """, (foto_perfil_filename, id_usuario))
                        conn.commit()

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

    elif rol_usuario == 2:  # Rol de entrenador
        if request.method == 'POST':
            email = request.form['entrenador_email']
            nuevo_nombre_usuario = request.form['entrenador_nombre_usuario']
            apellido = request.form['entrenador_apellido']
            nombre = request.form['entrenador_nombre']
            fecha_nacimiento = request.form['entrenador_fecha_nacimiento']
            edad = request.form['entrenador_edad']
            pais = request.form['entrenador_pais']
            sexo = request.form['entrenador_sexo']
            biografia = request.form['entrenador_biografia']
            especializacion = request.form['entrenador_especializacion']
            disciplina = request.form['entrenador_disciplina']
            experiencia = request.form['entrenador_experiencia']
            titulo = request.form['entrenador_titulo']
            instituto = request.form['entrenador_instituto']

            # Procesar la foto de perfil
            if 'file' in request.files:
                file = request.files['file']
                if file and allowed_file(file.filename):
                    foto_perfil_filename = compress_and_convert_to_webp(
                        file, id_usuario, 'trainers', 'trainer{id}-profile.webp'
                    )
                    if foto_perfil_filename:
                        cursor.execute("""
                            UPDATE entrenador
                            SET foto_perfil = ?
                            WHERE id_usuario = ?
                        """, (foto_perfil_filename, id_usuario))
                    else:
                        flash("Error al procesar la imagen. Asegúrate de que es un archivo válido.", 'error')

            # Procesar la imagen de título
            if 'titulo_foto' in request.files:
                file = request.files['titulo_foto']
                if file and allowed_file(file.filename):
                    # Eliminar la imagen anterior si existe
                    titulo_actual = usuario_data['titulo_foto']
                    if titulo_actual and titulo_actual:
                        try:
                            old_path = os.path.join(UPLOAD_FOLDERS['studies'], titulo_actual)
                            if os.path.exists(old_path):
                                os.remove(old_path)
                        except Exception as e:
                            print(f"Error al eliminar imagen anterior: {e}")

                    # Procesar nueva imagen
                    titulo_foto_filename = compress_and_convert_to_webp(
                        file, id_usuario, 'studies', 'trainer{id}-title.webp'
                    )
                    if titulo_foto_filename:
                        cursor.execute("""
                            UPDATE entrenador
                            SET titulo_foto = ?
                            WHERE id_usuario = ?
                        """, (titulo_foto_filename, id_usuario))
                        conn.commit()


            try:
                # Actualizar los datos del usuario
                cursor.execute("""
                    UPDATE usuario 
                    SET email = ?, nombre_usuario = ?
                    WHERE nombre_usuario = ?
                """, (email, nuevo_nombre_usuario, nombre_usuario))

                # Actualizar la tabla `entrenador`
                cursor.execute("""
                    UPDATE entrenador
                    SET apellido = ?, nombre = ?, fecha_nacimiento = ?, edad = ?, 
                        id_pais = ?, sexo = ?, biografia = ?, especializacion = ?, 
                        disciplina = ?, experiencia = ?, titulo = ?, instituto = ?
                    WHERE id_usuario = (SELECT id_usuario FROM usuario WHERE nombre_usuario = ?)
                """, (apellido, nombre, fecha_nacimiento, edad, pais, sexo, biografia,
                    especializacion, disciplina, experiencia, titulo, instituto, nombre_usuario))
                conn.commit()

                flash("Perfil actualizado correctamente.", 'success')

                session['nombre_usuario'] = nuevo_nombre_usuario
                
                return redirect(url_for('perfil.perfil', nombre_usuario=nuevo_nombre_usuario))
            except Exception as e:
                conn.rollback()
                flash("Ocurrió un error al actualizar el perfil: " + str(e), 'error')
            finally:
                cursor.close()
                conn.close()

    # Renderizar plantilla con los datos actuales del usuario
    return render_template('perfil.html', rol_usuario=rol_usuario, nombre_usuario=nombre_usuario, usuario_data=usuario_data, paises=paises)


@perfil_bp.route('/eliminar-cuenta', methods=['POST'])
@login_required
def eliminar_cuenta():
    if request.method == 'POST':
        password = request.form.get('password')
        
        if not password:
            flash('Por favor ingresa tu contraseña', 'error')
            return redirect(url_for('perfil.perfil', nombre_usuario=session['nombre_usuario']))
        
        nombre_usuario = session['nombre_usuario']
        conn = conexion_basedatos()
        cursor = conn.cursor()
        
        try:
            # Obtener los datos completos del usuario
            cursor.execute("""
                SELECT u.id_usuario, u.contrasena, u.rol, 
                       a.id_alumno, e.id_entrenador
                FROM usuario u
                LEFT JOIN alumno a ON u.id_usuario = a.id_usuario
                LEFT JOIN entrenador e ON u.id_usuario = e.id_usuario
                WHERE u.nombre_usuario = ?
            """, (nombre_usuario,))
            usuario = cursor.fetchone()
            
            if not usuario:
                flash('Usuario no encontrado', 'error')
                return redirect(url_for('perfil.perfil', nombre_usuario=nombre_usuario))
            
            # Verificar la contraseña
            if not check_password_hash(usuario['contrasena'], password):
                flash('Contraseña incorrecta', 'error')
                return redirect(url_for('perfil.perfil', nombre_usuario=nombre_usuario))
            
            # Eliminar primero los registros relacionados según el rol
            if usuario['rol'] == 1:  # Alumno
                self_delete_alumno(cursor, usuario)
            elif usuario['rol'] == 2:  # Entrenador
                self_delete_entrenador(cursor, usuario)
            
            # Eliminar datos comunes a ambos roles
            delete_common_user_data(cursor, usuario['id_usuario'])
            
            # Finalmente eliminar el usuario
            cursor.execute("DELETE FROM usuario WHERE id_usuario = ?", (usuario['id_usuario'],))
            conn.commit()
            
            # Cerrar sesión y redirigir al login
            session.clear()
            flash('Tu cuenta ha sido eliminada correctamente', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error al eliminar la cuenta: {str(e)}', 'error')
            return redirect(url_for('perfil.perfil', nombre_usuario=nombre_usuario))
        finally:
            cursor.close()
            conn.close()

def self_delete_alumno(cursor, usuario):
    if not usuario['id_alumno']:
        return
    
    # Eliminar archivos de imagen primero si existen
    cursor.execute("SELECT foto_perfil FROM alumno WHERE id_alumno = ?", (usuario['id_alumno'],))
    alumno_data = cursor.fetchone()
    if alumno_data and alumno_data['foto_perfil']:
        try:
            foto_path = os.path.join(UPLOAD_FOLDERS['users'], alumno_data['foto_perfil'])
            if os.path.exists(foto_path):
                os.remove(foto_path)
        except Exception as e:
            print(f"Error al eliminar imagen de perfil: {e}")
    
    # Obtener todos los entrenamientos del alumno
    cursor.execute("SELECT id_entrenamiento FROM entrenamiento WHERE id_alumno = ?", (usuario['id_alumno'],))
    entrenamientos = cursor.fetchall()
    
    # Eliminar datos relacionados con cada entrenamiento
    for entrenamiento in entrenamientos:
        delete_entrenamiento_data(cursor, entrenamiento['id_entrenamiento'])
    
    # Eliminar vinculaciones donde el alumno es origen o destino
    cursor.execute("DELETE FROM vinculaciones WHERE id_usuario_origen = ? OR id_usuario_destino = ?", 
                  (usuario['id_usuario'], usuario['id_usuario']))
    
    # Eliminar notificaciones del alumno
    cursor.execute("DELETE FROM notificaciones WHERE id_usuario = ?", (usuario['id_usuario'],))
    
    # Eliminar cuestionarios del alumno
    cursor.execute("DELETE FROM cuestionario WHERE id_alumno = ?", (usuario['id_alumno'],))
    
    # Eliminar registro de alumno
    cursor.execute("DELETE FROM alumno WHERE id_alumno = ?", (usuario['id_alumno'],))

def self_delete_entrenador(cursor, usuario):
    if not usuario['id_entrenador']:
        return
    
    # Eliminar archivos de imagen primero si existen
    cursor.execute("SELECT foto_perfil, titulo_foto FROM entrenador WHERE id_entrenador = ?", (usuario['id_entrenador'],))
    entrenador_data = cursor.fetchone()
    if entrenador_data:
        if entrenador_data['foto_perfil']:
            try:
                foto_path = os.path.join(UPLOAD_FOLDERS['trainers'], entrenador_data['foto_perfil'])
                if os.path.exists(foto_path):
                    os.remove(foto_path)
            except Exception as e:
                print(f"Error al eliminar imagen de perfil: {e}")
        
        if entrenador_data['titulo_foto']:
            try:
                titulo_path = os.path.join(UPLOAD_FOLDERS['studies'], entrenador_data['titulo_foto'])
                if os.path.exists(titulo_path):
                    os.remove(titulo_path)
            except Exception as e:
                print(f"Error al eliminar imagen de título: {e}")
    
    # Obtener todos los entrenamientos del entrenador
    cursor.execute("SELECT id_entrenamiento FROM entrenamiento WHERE id_entrenador = ?", (usuario['id_entrenador'],))
    entrenamientos = cursor.fetchall()
    
    # Eliminar datos relacionados con cada entrenamiento
    for entrenamiento in entrenamientos:
        delete_entrenamiento_data(cursor, entrenamiento['id_entrenamiento'])
    
    # Eliminar vinculaciones donde el entrenador es origen o destino
    cursor.execute("DELETE FROM vinculaciones WHERE id_usuario_origen = ? OR id_usuario_destino = ?", 
                  (usuario['id_usuario'], usuario['id_usuario']))
    
    # Eliminar notificaciones del entrenador
    cursor.execute("DELETE FROM notificaciones WHERE id_usuario = ?", (usuario['id_usuario'],))
    
    # Eliminar registro de entrenador
    cursor.execute("DELETE FROM entrenador WHERE id_entrenador = ?", (usuario['id_entrenador'],))

def delete_entrenamiento_data(cursor, id_entrenamiento):
    # Obtener todas las semanas del entrenamiento
    cursor.execute("SELECT id_semana FROM semanas WHERE id_entrenamiento = ?", (id_entrenamiento,))
    semanas = cursor.fetchall()
    
    for semana in semanas:
        # Obtener todos los días de la semana
        cursor.execute("SELECT id_dia FROM dias WHERE id_semana = ?", (semana['id_semana'],))
        dias = cursor.fetchall()
        
        for dia in dias:
            # Eliminar progreso de alumno relacionado con los ejercicios del día
            cursor.execute("""
                DELETE FROM progreso_alumno 
                WHERE id_dia_ejercicio IN (
                    SELECT id_dia_ejercicio FROM dia_ejercicio WHERE id_dia = ?
                )
            """, (dia['id_dia'],))
            
            # Eliminar ejercicios del día
            cursor.execute("DELETE FROM dia_ejercicio WHERE id_dia = ?", (dia['id_dia'],))
            
            # Eliminar el día
            cursor.execute("DELETE FROM dias WHERE id_dia = ?", (dia['id_dia'],))
        
        # Eliminar progreso semanal
        cursor.execute("DELETE FROM progreso_semana WHERE id_semana = ?", (semana['id_semana'],))
        
        # Eliminar la semana
        cursor.execute("DELETE FROM semanas WHERE id_semana = ?", (semana['id_semana'],))
    
    # Finalmente eliminar el entrenamiento
    cursor.execute("DELETE FROM entrenamiento WHERE id_entrenamiento = ?", (id_entrenamiento,))

def delete_common_user_data(cursor, id_usuario):
    # Eliminar notificaciones del usuario
    cursor.execute("DELETE FROM notificaciones WHERE id_usuario = ?", (id_usuario,))
    
    # Eliminar vinculaciones donde el usuario es origen o destino
    cursor.execute("DELETE FROM vinculaciones WHERE id_usuario_origen = ? OR id_usuario_destino = ?", 
                  (id_usuario, id_usuario))


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
        rol_usuario = session.get('rol')  # Asegúrate de tener el rol en la sesión

        if rol_usuario == 1:  # Alumno
            cursor.execute("""
                UPDATE alumno
                SET instagram = ?, facebook = ?, telefono = ?
                WHERE id_usuario = ?
            """, (instagram, facebook, telefono, id_usuario))
        elif rol_usuario == 2:  # Entrenador
            cursor.execute("""
                UPDATE entrenador
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