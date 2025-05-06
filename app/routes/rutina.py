from flask import Blueprint, render_template, session, request, current_app,  redirect, url_for, flash
from app.utils.helpers import login_required, verificar_formulario_completo
from app.utils.conexion import conexion_basedatos
from app.utils.helpers import allowed_file
from datetime import datetime
import os


rutina_bp = Blueprint('rutina', __name__)


# Ruta de Rutina
@rutina_bp.route('/entrenamiento/rutina/<int:id_entrenamiento>')
@login_required
@verificar_formulario_completo
def rutina(id_entrenamiento):
    user_id = session.get('id_usuario')

    DB = conexion_basedatos()

    # Verificar el rol del usuario
    user_data = DB.execute("""
        SELECT rol FROM usuario WHERE id_usuario = ?
    """, (user_id,)).fetchone()

    if not user_data:
        return "Error: Usuario no encontrado", 400
    
    rol_usuario = user_data[0]

    if rol_usuario == 1:  # Es un alumno
        id_alumno = DB.execute("""
            SELECT id_alumno FROM alumno WHERE id_usuario = ?
        """, (user_id,)).fetchone()
        
        if not id_alumno:
            # Lanzar un flash
            flash("Solos los alumnos pueden registrar su progreso", "error")
            return redirect(url_for('rutina.rutina', id_entrenamiento=id_entrenamiento))
        
        id_alumno = id_alumno[0]
        print(f"ID del Alumno: {id_alumno}") # Debugging

    
    elif rol_usuario == 2:  # Es un entrenador
        # Obtener el ID de un alumno relacionado con el entrenamiento
        id_alumno = DB.execute("""
            SELECT a.id_alumno 
            FROM alumno a
            JOIN entrenamiento e ON a.id_alumno = e.id_alumno
            WHERE e.id_entrenamiento = ?
        """, (id_entrenamiento,)).fetchone()
        
        if not id_alumno:
            return "Error: No hay alumnos asignados a este entrenamiento", 400
        
        id_alumno = id_alumno[0]
    
    else:
        return "Error: Rol de usuario no válido", 400

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

        # Obtener progreso semanal si existe
        progreso_semanal = DB.execute("""
            SELECT observaciones, foto_fisico, 
                   DATE(fecha) as fecha  -- Asegura el formato de fecha
            FROM progreso_semana 
            WHERE id_entrenamiento = ? AND id_semana = ? AND id_alumno = ?
        """, (id_entrenamiento, id_semana, id_alumno)).fetchone()
        
        if progreso_semanal:
            semana['progreso'] = dict(progreso_semanal)
            # Convertir string a objeto date si es necesario
            if isinstance(semana['progreso']['fecha'], str):
                try:
                    semana['progreso']['fecha'] = datetime.strptime(
                        semana['progreso']['fecha'], '%Y-%m-%d'
                    ).date()
                except (ValueError, TypeError):
                    semana['progreso']['fecha'] = None
        else:
            semana['progreso'] = None

        dias = [dict(dia) for dia in DB.execute("""
            SELECT id_dia, numero_dia, nombre_rutina 
            FROM dias 
            WHERE id_semana = ? 
            ORDER BY numero_dia
        """, (id_semana,)).fetchall()]

        for dia in dias:
            id_dia = dia['id_dia']

            ejercicios_con_progreso = DB.execute("""
                SELECT COUNT(*) FROM dia_ejercicio de
                LEFT JOIN progreso_alumno pa ON de.id_dia_ejercicio = pa.id_dia_ejercicio AND pa.id_alumno = ?
                WHERE de.id_dia = ? AND (
                    pa.series_realizadas IS NULL OR pa.repeticiones_realizadas IS NULL
                )
            """, (id_alumno, id_dia)).fetchone()[0]

            if ejercicios_con_progreso == 0:
                # Todos tienen progreso, marcar como completado
                DB.execute("""
                    UPDATE dias SET completado = 1 WHERE id_dia = ?
                """, (id_dia,))
                DB.commit()

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
                           semanas=semanas,
                           semana_actual=1)


@rutina_bp.route('/guardar_progreso_semanal', methods=['POST'])
@login_required
def guardar_progreso_semanal():
    id_entrenamiento = request.form['id_entrenamiento']
    id_semana = request.form['id_semana']
    observaciones = request.form.get('sensations', '')
    
    DB = conexion_basedatos()
    
    # Obtener ID del alumno
    id_alumno = DB.execute("""
        SELECT id_alumno FROM alumno WHERE id_usuario = ?
    """, (session.get('id_usuario'),)).fetchone()[0]
    
    # Obtener datos para la notificación
    ejercicio_data = DB.execute("""
        SELECT e.nombre_entrenamiento, s.numero_semana, e.id_entrenador
        FROM entrenamiento e
        JOIN semanas s ON e.id_entrenamiento = s.id_entrenamiento
        WHERE e.id_entrenamiento = ? AND s.id_semana = ?
    """, (id_entrenamiento, id_semana)).fetchone()

    # Obtener nombre del alumno
    nombre_alumno = DB.execute("""
        SELECT u.nombre_usuario 
        FROM usuario u
        JOIN alumno a ON u.id_usuario = a.id_usuario
        WHERE a.id_alumno = ?
    """, (id_alumno,)).fetchone()[0]
    
    # Crear notificación para el entrenador
    mensaje = f"'{ejercicio_data['nombre_entrenamiento']}': @{nombre_alumno} registró su progreso en la Semana {ejercicio_data['numero_semana']}"

    # Manejar la carga de archivos
    foto_fisico = None
    if 'progress-file' in request.files:
        file = request.files['progress-file']
        if file.filename != '':
            if file and allowed_file(file.filename):
                upload_folder = os.path.join(current_app.root_path, 'static/uploads/weekly_progress')
                os.makedirs(upload_folder, exist_ok=True)
                
                # Eliminar foto anterior si existe
                progreso_existente = DB.execute("""
                    SELECT foto_fisico FROM progreso_semana 
                    WHERE id_entrenamiento = ? AND id_semana = ? AND id_alumno = ?
                """, (id_entrenamiento, id_semana, id_alumno)).fetchone()
                
                if progreso_existente and progreso_existente[0]:
                    try:
                        os.remove(os.path.join(upload_folder, progreso_existente[0]))
                    except FileNotFoundError:
                        pass
                
                # Generar nuevo nombre de archivo
                filename = f"user{id_alumno}-progress-{int(datetime.now().timestamp())}.webp"
                file.save(os.path.join(upload_folder, filename))
                foto_fisico = filename
    
    # Verificar si ya existe progreso para esta semana
    progreso_existente = DB.execute("""
        SELECT id_progreso_semanal, foto_fisico FROM progreso_semana 
        WHERE id_entrenamiento = ? AND id_semana = ? AND id_alumno = ?
    """, (id_entrenamiento, id_semana, id_alumno)).fetchone()
    
    if progreso_existente:
        # Actualizar registro existente
        DB.execute("""
            UPDATE progreso_semana 
            SET observaciones = ?, 
                foto_fisico = COALESCE(?, foto_fisico),
                fecha = ?
            WHERE id_progreso_semanal = ?
        """, (
            observaciones, 
            foto_fisico,
            datetime.now().strftime("%Y-%m-%d"),
            progreso_existente[0]
        ))
        
        # Eliminar foto anterior si se subió una nueva
        if foto_fisico and progreso_existente[1]:
            try:
                os.remove(os.path.join(
                    current_app.root_path,
                    'static/uploads/weekly_progress',
                    progreso_existente[1]
                ))
            except FileNotFoundError:
                pass
    else:
        # Crear nuevo registro
        DB.execute("""
            INSERT INTO progreso_semana 
            (id_entrenamiento, id_alumno, id_semana, observaciones, foto_fisico, fecha)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            id_entrenamiento, 
            id_alumno, 
            id_semana, 
            observaciones, 
            foto_fisico,
            datetime.now().strftime("%Y-%m-%d")
        ))

    DB.execute("""
        INSERT INTO notificaciones (id_usuario, mensaje, id_entrenamiento)
        VALUES (?, ?, ?)
    """, (ejercicio_data['id_entrenador'], mensaje, id_entrenamiento))   
    
    DB.commit()
    DB.close()
    flash('Progreso semanal guardado correctamente', 'success')
    return redirect(url_for('rutina.rutina', id_entrenamiento=id_entrenamiento))


# Ruta de Guardar Progreso
@rutina_bp.route('/guardar_progreso', methods=['POST'])
@login_required
def guardar_progreso():
    # Obtener los datos del formulario
    id_dia_ejercicio = request.form['id_dia_ejercicio']
    id_entrenamiento = request.form['id_entrenamiento']

    # Obtener el ID del alumno
    DB = conexion_basedatos()
    id_alumno = DB.execute("""
        SELECT id_alumno FROM alumno WHERE id_usuario = ?
    """, (session.get('id_usuario'),)).fetchone()

    if not id_alumno:
        flash("Solo los alumnos pueden registrar su progreso", "error")
        return redirect(url_for('rutina.rutina', id_entrenamiento=id_entrenamiento))

    id_alumno = id_alumno[0]

    # Obtener datos del ejercicio y entrenamiento para la notificación
    ejercicio_data = DB.execute("""
        SELECT e.nombre_ejercicio, d.numero_dia, s.numero_semana, 
               en.nombre_entrenamiento, en.id_entrenador
        FROM dia_ejercicio de
        JOIN ejercicios e ON de.id_ejercicio = e.id_ejercicio
        JOIN dias d ON de.id_dia = d.id_dia
        JOIN semanas s ON d.id_semana = s.id_semana
        JOIN entrenamiento en ON s.id_entrenamiento = en.id_entrenamiento
        WHERE de.id_dia_ejercicio = ?
    """, (id_dia_ejercicio,)).fetchone()

    if not ejercicio_data:
        flash("Error al obtener datos del ejercicio", "error")
        return redirect(url_for('rutina.rutina', id_entrenamiento=id_entrenamiento))

    # Obtener nombre de usuario del alumno
    nombre_alumno = DB.execute("""
        SELECT u.nombre_usuario 
        FROM usuario u
        JOIN alumno a ON u.id_usuario = a.id_usuario
        WHERE a.id_alumno = ?
    """, (id_alumno,)).fetchone()[0]

    # Obtener los datos del formulario
    series_realizadas = request.form['series_realizadas']
    repeticiones_realizadas = request.form['repeticiones_realizadas']
    peso_utilizado = request.form['peso_utilizado']
    observaciones = request.form['observaciones']

    # Verificar si ya existe un registro para este ejercicio
    progreso = DB.execute("""
        SELECT id_progreso FROM progreso_alumno WHERE id_dia_ejercicio = ? AND id_alumno = ?
    """, (id_dia_ejercicio, id_alumno)).fetchone()

    if progreso:
        # Actualizar el progreso existente
        DB.execute("""
            UPDATE progreso_alumno
            SET series_realizadas = ?, repeticiones_realizadas = ?, peso_utilizado = ?, observaciones = ?
            WHERE id_progreso = ?
        """, (series_realizadas, repeticiones_realizadas, peso_utilizado, observaciones, progreso[0]))
        flash('Progreso actualizado correctamente.', 'success')
    else:
        # Insertar nuevo registro de progreso
        DB.execute("""
            INSERT INTO progreso_alumno (id_dia_ejercicio, id_alumno, series_realizadas, repeticiones_realizadas, peso_utilizado, observaciones, fecha)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_DATE)
        """, (id_dia_ejercicio, id_alumno, series_realizadas, repeticiones_realizadas, peso_utilizado, observaciones))
        flash('Progreso registrado correctamente.', 'success')

    # Crear notificación para el entrenador
    mensaje = (
        f"'{ejercicio_data['nombre_entrenamiento']}': @{nombre_alumno} registró {ejercicio_data['nombre_ejercicio']} (Semana {ejercicio_data['numero_semana']}/Día {ejercicio_data['numero_dia']})"
    )

    DB.execute("""
        INSERT INTO notificaciones (id_usuario, mensaje, id_entrenamiento)
        VALUES (?, ?, ?)
    """, (ejercicio_data['id_entrenador'], mensaje, id_entrenamiento))

    DB.commit()
    return redirect(url_for('rutina.rutina', id_entrenamiento=id_entrenamiento))