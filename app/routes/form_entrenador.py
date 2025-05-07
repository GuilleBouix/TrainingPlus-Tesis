from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.helpers import login_required, entrenador_required, verificar_suscripcion
from app.utils.conexion import conexion_basedatos
from PIL import Image
import os


form_entrenador_bp = Blueprint('form_entrenador', __name__)


# Configuración de la carpeta de subida de fotos para entrenadores
UPLOAD_TRAINER_FOLDER = 'static/uploads/users'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
DEFAULT_PROFILE_PICTURE = 'profile.webp'
DEFAULT_TITLE_IMAGE = 'title.webp'


# Verificar extensiones permitidas
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Comprimir y convertir a .webp
def compress_and_convert_to_webp(file, id_usuario, file_type):
    # Define el directorio de almacenamiento
    if file_type == 'title':
        uploads_dir = os.path.join('app', 'static', 'uploads', 'titles')
        filename = f'trainer{id_usuario}-title.webp'
    else:
        raise ValueError("Tipo de archivo no soportado.")

    # Crear directorio si no existe
    os.makedirs(uploads_dir, exist_ok=True)

    # Define el camino completo donde se guardará la imagen
    file_path = os.path.join(uploads_dir, filename)

    # Abre la imagen con PIL y comprímela a formato webp
    image = Image.open(file)

    # Redimensionar (opcional)
    width, height = image.size
    new_width = width // 2
    new_height = height // 2
    image = image.resize((new_width, new_height))

    # Convertir y guardar
    image = image.convert("RGB")
    image.save(file_path, format="WEBP", quality=60)

    return filename
    

# Ruta de Formulario de Entrenador
@form_entrenador_bp.route('/formulario-entrenador', methods=['GET', 'POST'])
@login_required
@entrenador_required
@verificar_suscripcion
def form_entrenador():
    db = conexion_basedatos()
    cursor = db.cursor()

    # Obtener lista de países
    cursor.execute("SELECT id_pais, nombre FROM pais")
    paises = cursor.fetchall()

    if request.method == 'POST':
        # Obtener datos del formulario
        apellido = request.form.get('apellido')
        nombre = request.form.get('nombre')
        edad = request.form.get('edad')
        id_pais = request.form.get('pais')
        sexo = request.form.get('sexo')
        fecha_nacimiento = request.form.get('fecha_nacimiento')
        biografia = request.form.get('biografia')
        especializacion = request.form.get('especializacion')
        disciplina = request.form.get('disciplina')
        experiencia = request.form.get('experiencia')
        titulo = request.form.get('titulo')
        instituto = request.form.get('instituto')

        # Manejo de imágenes
        titulo_foto = request.files['titulo_imagen']

        if titulo_foto and allowed_file(titulo_foto.filename):
            titulo_foto_name = compress_and_convert_to_webp(titulo_foto, session['id_usuario'], 'title')
        else:
            titulo_foto_name = DEFAULT_TITLE_IMAGE

        # Actualizar la base de datos
        cursor.execute("""
            UPDATE entrenador
            SET form_complete = 'true', apellido = ?, nombre = ?, edad = ?, id_pais = ?, 
                sexo = ?, fecha_nacimiento = ?, biografia = ?, especializacion = ?, 
                disciplina = ?, experiencia = ?, titulo_foto = ?, titulo = ?, instituto = ? 
            WHERE id_usuario = ?""", (apellido, nombre, edad, id_pais, sexo, fecha_nacimiento, biografia, especializacion, 
              disciplina, experiencia, titulo_foto_name, titulo, instituto,
              session['id_usuario']))
        db.commit()
        flash("Formulario completado con éxito", "success")
        return redirect(url_for('entrenamiento.entrenamiento'))

    return render_template('form_entrenador.html', paises=paises)