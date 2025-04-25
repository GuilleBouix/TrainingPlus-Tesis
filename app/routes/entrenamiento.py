from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.helpers import login_required, verificar_formulario_completo
from app.utils.conexion import conexion_basedatos
from datetime import date


entrenamiento_bp = Blueprint('entrenamiento', __name__)


# Ruta de Entrenamiento
@entrenamiento_bp.route('/entrenamiento')
@login_required
@verificar_formulario_completo
def entrenamiento():
    user_id = session.get('id_usuario')
    db = conexion_basedatos()

    # Obtener id_alumno si el usuario es un alumno
    alumno = db.execute("SELECT id_alumno FROM alumno WHERE id_usuario = ?", (user_id,)).fetchone()
    id_alumno = alumno['id_alumno'] if alumno else None

    # Obtener el rol del usuario logueado
    usuario = db.execute("SELECT rol FROM usuario WHERE id_usuario = ?", (user_id,)).fetchone()
    rol_usuario = usuario["rol"] if usuario else None

    # Función para calcular progreso basado en ejercicios completados
    def calcular_progreso(id_entrenamiento, id_alumno_entrenamiento=None):
        # Si se provee un id_alumno_entrenamiento (para entrenadores), usarlo
        # Si no, usar el id_alumno del usuario logueado (para alumnos)
        alumno_id = id_alumno_entrenamiento if id_alumno_entrenamiento else id_alumno
        
        query = """
            SELECT 
                COUNT(DISTINCT p.id_progreso) * 100.0 / NULLIF(COUNT(DISTINCT de.id_dia_ejercicio), 0) AS progreso
            FROM entrenamiento e
            JOIN semanas s ON e.id_entrenamiento = s.id_entrenamiento
            JOIN dias d ON s.id_semana = d.id_semana
            JOIN dia_ejercicio de ON d.id_dia = de.id_dia
            LEFT JOIN progreso_alumno p ON de.id_dia_ejercicio = p.id_dia_ejercicio AND p.id_alumno = ?
            WHERE e.id_entrenamiento = ?
            GROUP BY e.id_entrenamiento;
        """
        result = db.execute(query, (alumno_id, id_entrenamiento)).fetchone()
        return round(result["progreso"], 1) if result and result["progreso"] is not None else 0.0

    entrenamientos = []
    
    if rol_usuario == 2:  # Entrenador
        # Entrenamientos creados por el entrenador
        entrenamientos += db.execute("""
            SELECT 
                e.*, 
                d.nombre AS nombre_disciplina,
                a.nombre AS alumno_nombre,
                a.apellido AS alumno_apellido,
                COALESCE(a.foto_perfil, 'profile.webp') AS alumno_foto_perfil
            FROM entrenamiento e
            LEFT JOIN disciplina d ON e.id_disciplina = d.id_disciplina
            LEFT JOIN alumno a ON e.id_alumno = a.id_alumno
            WHERE e.id_entrenador = ?
        """, (user_id,)).fetchall()
    
    elif rol_usuario == 1 and id_alumno:  # Alumno
        # Entrenamientos asignados al alumno
        entrenamientos += db.execute("""
            SELECT 
                e.*, 
                d.nombre AS nombre_disciplina,
                t.nombre AS entrenador_nombre,
                t.apellido AS entrenador_apellido,
                COALESCE(t.foto_perfil, 'profile.webp') AS entrenador_foto_perfil
            FROM entrenamiento e
            LEFT JOIN disciplina d ON e.id_disciplina = d.id_disciplina
            LEFT JOIN entrenador t ON e.id_entrenador = t.id_usuario
            WHERE e.id_alumno = ?
        """, (id_alumno,)).fetchall()

    # Agregar progreso a cada entrenamiento
    entrenamientos_con_progreso = []
    for entrenamiento in entrenamientos:
        # Para entrenadores, usar el id_alumno del entrenamiento
        id_alumno_entrenamiento = entrenamiento["id_alumno"] if rol_usuario == 2 else None
        progreso = calcular_progreso(entrenamiento["id_entrenamiento"], id_alumno_entrenamiento)
        entrenamiento_dict = dict(entrenamiento)
        entrenamiento_dict["progreso"] = progreso
        entrenamientos_con_progreso.append(entrenamiento_dict)

    return render_template('entrenamiento.html',
                           entrenamientos=entrenamientos_con_progreso,
                           rol_usuario=rol_usuario)


# Ruta para Crear Entrenamiento (Todo en uno)
@entrenamiento_bp.route('/crear_entrenamiento', methods=['GET', 'POST'])
@login_required
def crear_entrenamiento():
    # Obtener el rol del usuario de la sesion
    rol = session.get('rol')

    id_entrenador = session['id_usuario']

    # Obtener alumnos con vinculación aceptada
    conexion = conexion_basedatos()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT a.id_alumno, a.nombre, a.apellido
        FROM vinculaciones v
        JOIN alumno a ON v.id_usuario_destino = a.id_usuario
        WHERE v.id_usuario_origen = ? AND v.estado = 'aceptada'
    """, (id_entrenador,))
    alumnos = cursor.fetchall()

    # Obtener la lista de ejercicios disponibles
    cursor.execute("SELECT id_ejercicio, nombre_ejercicio FROM ejercicios ORDER BY nombre_ejercicio ASC")
    ejercicios = cursor.fetchall()

    if request.method == 'POST':
        try:
            # Recoger datos básicos del formulario
            id_alumno = request.form.get('id_alumno')
            nombre_entrenamiento = request.form.get('nombre_entrenamiento')
            disciplina = request.form.get('disciplina')
            duracion_semanas = int(request.form.get('duracion_semanas'))
            fecha_inicio = date.today().strftime('%Y-%m-%d')

            # Insertar en la tabla entrenamiento
            cursor.execute("""
                INSERT INTO entrenamiento (id_entrenador, id_alumno, nombre_entrenamiento, id_disciplina, duracion_semanas, fecha_inicio)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (id_entrenador, id_alumno, nombre_entrenamiento, disciplina, duracion_semanas, fecha_inicio))
            id_entrenamiento = cursor.lastrowid

            # Obtener datos del entrenador
            entrenador = cursor.execute("""
                SELECT u.nombre_usuario, e.nombre, e.apellido 
                FROM usuario u
                JOIN entrenador e ON u.id_usuario = e.id_usuario
                WHERE u.id_usuario = ?
            """, (id_entrenador,)).fetchone()

            # Insertar notificación para el alumno con el formato deseado. Buscar el id_usuario correspondiente al id_alumno
            cursor.execute("SELECT id_usuario FROM alumno WHERE id_alumno = ?", (id_alumno,)) 
            usuario_alumno = cursor.fetchone()
            id_usuario_alumno = usuario_alumno['id_usuario']
    
            mensaje = f"El entrenador @{entrenador['nombre_usuario']} ha creado un nuevo plan de entrenamiento: {nombre_entrenamiento}."

            cursor.execute('''INSERT INTO notificaciones (id_usuario, mensaje, id_entrenamiento)
                            VALUES (?, ?, ?)''', (id_usuario_alumno, mensaje, id_entrenamiento))

            # Procesar semanas, días y ejercicios
            for semana in range(1, duracion_semanas + 1):
                # Insertar semana
                cursor.execute("""
                    INSERT INTO semanas (id_entrenamiento, numero_semana)
                    VALUES (?, ?)
                """, (id_entrenamiento, semana))
                id_semana = cursor.lastrowid

                # Obtener el número de días para esta semana
                dias_semana = int(request.form.get(f'semanas[{semana}][dias]'))

                for dia in range(1, dias_semana + 1):
                    # Insertar día
                    nombre_rutina = request.form.get(f'semanas[{semana}][dias][{dia}][nombre_rutina]')
                    cursor.execute("""
                        INSERT INTO dias (id_semana, numero_dia, nombre_rutina)
                        VALUES (?, ?, ?)
                    """, (id_semana, dia, nombre_rutina))
                    id_dia = cursor.lastrowid

                    # Obtener el número de ejercicios para este día
                    ejercicios_dia = int(request.form.get(f'semanas[{semana}][dias][{dia}][ejercicios]'))

                    for ejercicio in range(1, ejercicios_dia + 1):
                        # Obtener el id_ejercicio seleccionado
                        id_ejercicio = int(request.form.get(f'semanas[{semana}][dias][{dia}][ejercicios][{ejercicio}][id_ejercicio]'))
                        series = int(request.form.get(f'semanas[{semana}][dias][{dia}][ejercicios][{ejercicio}][series]'))
                        repeticiones = int(request.form.get(f'semanas[{semana}][dias][{dia}][ejercicios][{ejercicio}][repeticiones]'))
                        peso = float(request.form.get(f'semanas[{semana}][dias][{dia}][ejercicios][{ejercicio}][peso]'))
                        tiempo_descanso = int(request.form.get(f'semanas[{semana}][dias][{dia}][ejercicios][{ejercicio}][tiempo_descanso]'))

                        # Insertar en dia_ejercicio
                        cursor.execute("""
                            INSERT INTO dia_ejercicio (id_dia, id_ejercicio, series, repeticiones, peso, tiempo_descanso)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (id_dia, id_ejercicio, series, repeticiones, peso, tiempo_descanso))

            # Confirmar cambios en la base de datos
            conexion.commit()

            flash("¡Entrenamiento creado exitosamente!", "success")
            return redirect(url_for('entrenamiento.entrenamiento'))

        except Exception as e:
            # Revertir cambios en caso de error
            conexion.rollback()

            return redirect(url_for('entrenamiento.crear_entrenamiento'))

        finally:
            # Cerrar la conexión a la base de datos
            conexion.close()

    return render_template('crear_entrenamiento.html',
                           alumnos=alumnos,
                           ejercicios=ejercicios,
                           rol=rol)


# Ruta para Editar Entrenamiento
@entrenamiento_bp.route('/editar_entrenamiento/<int:id_entrenamiento>', methods=['GET', 'POST'])
@login_required
@verificar_formulario_completo
def editar_entrenamiento(id_entrenamiento):
    user_id = session.get('id_usuario')
    db = conexion_basedatos()
    
    try:
        # Verificar que el entrenamiento pertenece al entrenador
        entrenamiento = db.execute("""
            SELECT * FROM entrenamiento 
            WHERE id_entrenamiento = ? AND id_entrenador = ?
        """, (id_entrenamiento, user_id)).fetchone()
        
        if not entrenamiento:
            flash("Entrenamiento no encontrado o no tienes permisos para editarlo", "error")
            return redirect(url_for('entrenamiento.entrenamiento'))
        
        # Obtener ejercicios disponibles
        ejercicios = db.execute("SELECT id_ejercicio, nombre_ejercicio FROM ejercicios ORDER BY nombre_ejercicio").fetchall()
        
        if request.method == 'GET':
            # Obtener la estructura actual del entrenamiento
            dias = db.execute("""
                SELECT d.id_dia, d.nombre_rutina, s.numero_semana, d.numero_dia
                FROM dias d
                JOIN semanas s ON d.id_semana = s.id_semana
                WHERE s.id_entrenamiento = ?
                ORDER BY s.numero_semana, d.numero_dia
            """, (id_entrenamiento,)).fetchall()
            
            ejercicios_por_dia = {}
            for dia in dias:
                ejercicios_dia = db.execute("""
                    SELECT de.*, e.nombre_ejercicio 
                    FROM dia_ejercicio de
                    JOIN ejercicios e ON de.id_ejercicio = e.id_ejercicio
                    WHERE de.id_dia = ?
                    ORDER BY de.id_dia_ejercicio
                """, (dia['id_dia'],)).fetchall()
                ejercicios_por_dia[dia['id_dia']] = ejercicios_dia
            
            # Convertir los datos en diccionarios antes de pasarlos a la plantilla
            dias = [dict(dia) for dia in dias]
            ejercicios_por_dia = {dia_id: [dict(ejercicio) for ejercicio in ejercicios] for dia_id, ejercicios in ejercicios_por_dia.items()}

            return render_template('editar_entrenamiento.html',
                                   entrenamiento=dict(entrenamiento),
                                   dias=dias,
                                   ejercicios_por_dia=ejercicios_por_dia,
                                   ejercicios=[dict(ejercicio) for ejercicio in ejercicios])
        
        elif request.method == 'POST':
            # Procesar cambios
            nuevo_nombre = request.form.get('nombre_entrenamiento')
            
            # Actualizar nombre del entrenamiento
            db.execute("""
                UPDATE entrenamiento 
                SET nombre_entrenamiento = ?
                WHERE id_entrenamiento = ?
            """, (nuevo_nombre, id_entrenamiento))
            
            # Procesar cambios en días y ejercicios
            for key, value in request.form.items():
                if key.startswith('nombre_dia_'):
                    dia_id = key.replace('nombre_dia_', '')
                    db.execute("""
                        UPDATE dias 
                        SET nombre_rutina = ?
                        WHERE id_dia = ?
                    """, (value, dia_id))
                
                elif key.startswith('ejercicio_'):
                    parts = key.split('_')
                    if len(parts) < 2:
                        continue  # Evitar errores si el formato de la clave no es el esperado
                    dia_ejercicio_id = parts[1]  # Corregir índice para obtener el ID correcto
                    
                    # Actualizar datos del ejercicio
                    db.execute("""
                        UPDATE dia_ejercicio 
                        SET id_ejercicio = ?,
                            series = ?,
                            repeticiones = ?,
                            peso = ?,
                            tiempo_descanso = ?
                        WHERE id_dia_ejercicio = ?
                    """, (
                        request.form.get(f'ejercicio_{dia_ejercicio_id}', None),
                        request.form.get(f'series_{dia_ejercicio_id}', 1),
                        request.form.get(f'repeticiones_{dia_ejercicio_id}', 1),
                        request.form.get(f'peso_{dia_ejercicio_id}', 0),
                        request.form.get(f'descanso_{dia_ejercicio_id}', 0),
                        dia_ejercicio_id
                    ))

            # Procesar nuevos ejercicios agregados
            for key in request.form:
                if key.startswith('nuevo_ejercicio_'):
                    dia_id = key.replace('nuevo_ejercicio_', '')
                    if request.form.get(key):
                        db.execute("""
                            INSERT INTO dia_ejercicio (id_dia, id_ejercicio, series, repeticiones, peso, tiempo_descanso)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            dia_id,
                            request.form.get(key),
                            request.form.get(f'nuevo_series_{dia_id}', 1),
                            request.form.get(f'nuevo_repeticiones_{dia_id}', 1),
                            request.form.get(f'nuevo_peso_{dia_id}', 0),
                            request.form.get(f'nuevo_descanso_{dia_id}', 0)
                        ))
            
            # Procesar ejercicios eliminados (solo si no tienen progreso)
            ejercicios_eliminados = request.form.getlist('eliminar_ejercicio')
            for dia_ejercicio_id in ejercicios_eliminados:
                # Verificar si tiene progreso antes de eliminar
                tiene_progreso = db.execute("""
                    SELECT 1 FROM progreso_alumno 
                    WHERE id_dia_ejercicio = ? 
                    LIMIT 1
                """, (dia_ejercicio_id,)).fetchone()
                
                if not tiene_progreso:
                    db.execute("DELETE FROM dia_ejercicio WHERE id_dia_ejercicio = ?", (dia_ejercicio_id,))
            
            db.commit()
            flash("Entrenamiento actualizado exitosamente", "success")
            return redirect(url_for('entrenamiento.entrenamiento'))
    
    except Exception as e:
        db.rollback()
        flash(f"Error al actualizar el entrenamiento: {str(e)}", "error")
        return redirect(url_for('entrenamiento.editar_entrenamiento', id_entrenamiento=id_entrenamiento))
    
    finally:
        db.close()