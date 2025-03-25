from app.utils.helpers import login_required, verificar_formulario_completo, redirect, url_for
from flask import Blueprint, render_template, session, request
from app.utils.conexion import conexion_basedatos
from datetime import datetime



rutina_bp = Blueprint('rutina', __name__)


# Ruta de Rutina
@rutina_bp.route('/entrenamiento/rutina/<int:id_entrenamiento>')
@login_required
@verificar_formulario_completo
def rutina(id_entrenamiento):
    user_id = session.get('id_usuario')

    DB = conexion_basedatos()

    # Obtener el ID del alumno basado en el usuario logueado
    id_alumno = DB.execute("""
        SELECT id_alumno FROM alumno WHERE id_usuario = ?
    """, (user_id,)).fetchone()

    if not id_alumno:
        return "Error: No se encontró el alumno", 400  # Mejor manejar el error de manera más clara

    id_alumno = id_alumno[0]  # Aquí obtienes el id real del alumno

    entrenamiento = DB.execute("""
    SELECT entrenamiento.id_entrenamiento, entrenamiento.nombre_entrenamiento, 
        entrenamiento.duracion_semanas,
        disciplina.nombre AS nombre_disciplina
    FROM entrenamiento
    LEFT JOIN disciplina ON entrenamiento.id_disciplina = disciplina.id_disciplina
    WHERE entrenamiento.id_entrenamiento = ? 
    """, (id_entrenamiento,)).fetchone()

    if not entrenamiento:
        return "Entrenamiento no encontrado", 404

    # Obtener semanas del entrenamiento
    semanas = [dict(semana) for semana in DB.execute("""
        SELECT id_semana, numero_semana 
        FROM semanas 
        WHERE id_entrenamiento = ? 
        ORDER BY numero_semana
    """, (id_entrenamiento,)).fetchall()]

    # Obtener días y ejercicios por semana
    for semana in semanas:
        id_semana = semana['id_semana']

        dias = [dict(dia) for dia in DB.execute("""
            SELECT id_dia, numero_dia, nombre_rutina 
            FROM dias 
            WHERE id_semana = ? 
            ORDER BY numero_dia
        """, (id_semana,)).fetchall()]

        for dia in dias:
            id_dia = dia['id_dia']

            ejercicios = [dict(ejercicio) for ejercicio in DB.execute("""
                SELECT de.id_dia_ejercicio, e.nombre_ejercicio, 
                    de.series, de.repeticiones, de.peso, de.tiempo_descanso, e.imagen_url,
                    COALESCE(pa.series_realizadas, '') AS series_realizadas,
                    COALESCE(pa.repeticiones_realizadas, '') AS repeticiones_realizadas,
                    COALESCE(pa.peso_utilizado, '') AS peso_utilizado,
                    COALESCE(pa.observaciones, '') AS observaciones
                FROM dia_ejercicio de
                JOIN ejercicios e ON de.id_ejercicio = e.id_ejercicio
                LEFT JOIN progreso_alumno pa 
                    ON de.id_dia_ejercicio = pa.id_dia_ejercicio 
                    AND pa.id_alumno = ?
                WHERE de.id_dia = ?
                ORDER BY de.id_dia_ejercicio
            """, (id_alumno, id_dia)).fetchall()]

            # Agregar progreso vacío si no hay registro
            for ejercicio in ejercicios:
                ejercicio["id_dia_ejercicio"] = ejercicio["id_dia_ejercicio"]  # Asegurar que esté en el diccionario
                ejercicio["series_realizadas"] = ejercicio["series_realizadas"] or ""
                ejercicio["repeticiones_realizadas"] = ejercicio["repeticiones_realizadas"] or ""
                ejercicio["peso_utilizado"] = ejercicio["peso_utilizado"] or ""
                ejercicio["observaciones"] = ejercicio["observaciones"] or ""

            dia["ejercicios"] = ejercicios  # Agregar los ejercicios al día

        semana["dias"] = dias  # Agregar los días a la semana

    return render_template('rutina.html', 
                           entrenamiento=entrenamiento,
                           semanas=semanas)



# Ruta de Guardar Progreso
@rutina_bp.route('/guardar_progreso', methods=['POST'])
@login_required
def guardar_progreso():
    # Obtener los datos del formulario
    id_dia_ejercicio = request.form['id_dia_ejercicio']
    # Si el id_alumno ya está en la sesión, lo obtenemos desde allí
    id_alumno = session.get('id_usuario')

    series_realizadas = request.form['series_realizadas']
    repeticiones_realizadas = request.form['repeticiones_realizadas']
    peso_utilizado = request.form['peso_utilizado']
    observaciones = request.form['observaciones']

    DB = conexion_basedatos()

    # Verificar si ya existe un registro para este ejercicio
    progreso = DB.execute("""
        SELECT id_progreso FROM progreso_alumno WHERE id_dia_ejercicio = ? AND id_alumno = ?
    """, (id_dia_ejercicio, id_alumno)).fetchone()

    if progreso:
        # Si ya existe, actualizar el progreso
        DB.execute("""
            UPDATE progreso_alumno
            SET series_realizadas = ?, repeticiones_realizadas = ?, peso_utilizado = ?, observaciones = ?
            WHERE id_progreso = ?
        """, (series_realizadas, repeticiones_realizadas, peso_utilizado, observaciones, progreso[0]))
    else:
        # Si no existe, insertar un nuevo registro
        DB.execute("""
            INSERT INTO progreso_alumno (id_dia_ejercicio, id_alumno, series_realizadas, repeticiones_realizadas, peso_utilizado, observaciones, fecha)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_DATE)
        """, (id_dia_ejercicio, id_alumno, series_realizadas, repeticiones_realizadas, peso_utilizado, observaciones))

    DB.commit()
    
    return redirect(url_for('rutina.rutina', id_entrenamiento=request.form['id_entrenamiento']))
