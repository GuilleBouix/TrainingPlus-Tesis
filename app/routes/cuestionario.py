from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.conexion import conexion_basedatos
from app.utils.helpers import login_required
from datetime import date


cuestionario_bp = Blueprint('cuestionario', __name__)


# Ruta del cuestionario
@cuestionario_bp.route('/cuestionario', methods=['GET', 'POST'])
@login_required
def cuestionario():
    conn = conexion_basedatos()
    cursor = conn.cursor()

    # Obtener id_usuario de la sesión
    id_usuario = session.get('id_usuario')

    # Verificar si el usuario es alumno
    cursor.execute("SELECT rol FROM usuario WHERE id_usuario = ?", (id_usuario,))
    usuario = cursor.fetchone()
    
    if not usuario or usuario[0] != 1:  # Si no es alumno
        flash("Acceso solo para alumnos.", "error")
        return redirect(url_for('entrenamiento.entrenamiento'))

    # Buscar id_alumno correspondiente
    cursor.execute("SELECT id_alumno FROM alumno WHERE id_usuario = ?", (id_usuario,))
    alumno = cursor.fetchone()

    if not alumno:
        flash("No se encontró al alumno correspondiente", "error")
        return redirect(url_for('entrenamiento.entrenamiento'))

    id_alumno = alumno[0]

    # Guardar datos
    if request.method == 'POST':
        # Obtener datos del formulario
        datos = {
            'edad': request.form.get('edad'),
            'experiencia': request.form.get('nivel'),
            'objetivo': request.form.get('objetivo'),
            'altura': request.form.get('altura'),
            'peso': request.form.get('peso'),
            'actividad': request.form.get('actividad'),
            'frecuencia': request.form.get('frecuencia'),
            'duracion_sesion': request.form.get('duracion_sesion'),
            'estado_general': request.form.get('estado_general'),
            'lesiones': request.form.get('lesiones'),
            'condicion_cardio': request.form.get('condicion_cardio'),
            'nivel_estres': request.form.get('nivel_estres'),
            'comentarios': request.form.get('comentarios')
        }

        # Verificar si ya existe un cuestionario
        cursor.execute("SELECT id_cuestionario FROM cuestionario WHERE id_alumno = ?", (id_alumno,))
        existe_cuestionario = cursor.fetchone()

        if existe_cuestionario:
            # Actualizar registro existente
            cursor.execute("""
                UPDATE cuestionario SET
                    objetivo_general = ?,
                    edad = ?,
                    peso = ?,
                    altura = ?,
                    nivel_actividad = ?,
                    experiencia = ?,
                    frecuencia_entreno = ?,
                    duracion_sesion = ?,
                    estado_salud = ?,
                    lesiones = ?,
                    condicion_cardio = ?,
                    nivel_estres = ?,
                    notas_alumno = ?,
                    fecha_completado = DATE('now')
                WHERE id_alumno = ?
            """, (
                datos['objetivo'], datos['edad'], datos['peso'], datos['altura'],
                datos['actividad'], datos['experiencia'], datos['frecuencia'], 
                datos['duracion_sesion'], datos['estado_general'], datos['lesiones'],
                datos['condicion_cardio'], datos['nivel_estres'], datos['comentarios'],
                id_alumno
            ))
            mensaje = "Ficha actualizada correctamente"
        else:
            fecha = date.today().isoformat()

            # Crear nuevo registro
            cursor.execute("""
                INSERT INTO cuestionario (
                    id_alumno, objetivo_general, edad, peso, altura,
                    nivel_actividad, experiencia, frecuencia_entreno, duracion_sesion,
                    estado_salud, lesiones, condicion_cardio, nivel_estres,
                    notas_alumno, fecha_completado
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                id_alumno, datos['objetivo'], datos['edad'], datos['peso'], datos['altura'],
                datos['actividad'], datos['experiencia'], datos['frecuencia'], 
                datos['duracion_sesion'], datos['estado_general'], datos['lesiones'],
                datos['condicion_cardio'], datos['nivel_estres'], datos['comentarios'],
                fecha
            ))
            mensaje = "Ficha creada correctamente"

        conn.commit()
        conn.close()
        flash(mensaje, "success")
        return redirect(url_for('entrenamiento.entrenamiento'))

    # Buscar cuestionario existente
    cursor.execute("""
        SELECT 
            objetivo_general, edad, altura, peso,
            nivel_actividad, experiencia, frecuencia_entreno, duracion_sesion,
            estado_salud, lesiones, condicion_cardio, nivel_estres, notas_alumno
        FROM cuestionario 
        WHERE id_alumno = ?
    """, (id_alumno,))
    cuestionario_existente = cursor.fetchone()
    conn.close()

    # Preparar datos para el template
    datos_formulario = {
        'edad': '',
        'nivel': '',
        'objetivo': '',
        'altura': '',
        'peso': '',
        'actividad': '',
        'frecuencia': '',
        'duracion_sesion': '',
        'estado_general': '',
        'lesiones': '',
        'condicion_cardio': '',
        'nivel_estres': '',
        'comentarios': ''
    }

    if cuestionario_existente:
        datos_formulario = {
            'edad': cuestionario_existente[1],
            'nivel': cuestionario_existente[5],
            'objetivo': cuestionario_existente[0],
            'altura': cuestionario_existente[2],
            'peso': cuestionario_existente[3],
            'actividad': cuestionario_existente[4],
            'frecuencia': cuestionario_existente[6],
            'duracion_sesion': cuestionario_existente[7],
            'estado_general': cuestionario_existente[8],
            'lesiones': cuestionario_existente[9],
            'condicion_cardio': cuestionario_existente[10],
            'nivel_estres': cuestionario_existente[11],
            'comentarios': cuestionario_existente[12]
        }

    return render_template('cuestionario.html', datos=datos_formulario)