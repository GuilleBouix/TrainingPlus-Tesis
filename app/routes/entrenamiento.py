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

    # Obtener información del alumno o entrenador asociado
    if rol_usuario == 1:  # Alumno
        info_entrenador = db.execute("""
            SELECT e.nombre AS nombre, e.apellido AS apellido, COALESCE(e.foto_perfil, 'profile.webp') AS foto_perfil
            FROM entrenador e
            JOIN entrenamiento et ON e.id_usuario = et.id_entrenador
            WHERE et.id_alumno = ?
        """, (user_id,)).fetchone()
        asociacion = {"tipo": "Entrenador", "datos": info_entrenador}
    elif rol_usuario == 2:  # Entrenador
        info_alumno = db.execute("""
            SELECT a.nombre AS nombre, a.apellido AS apellido, COALESCE(a.foto_perfil, 'profile.webp') AS foto_perfil
            FROM alumno a
            JOIN entrenamiento et ON a.id_usuario = et.id_alumno
            WHERE et.id_entrenador = ?
        """, (user_id,)).fetchone()
        asociacion = {"tipo": "Alumno", "datos": info_alumno}
    else:
        asociacion = None

    # Buscar entrenamientos del usuario logueado
    entrenamientos = []

    # Función para calcular progreso basado en ejercicios completados
    def calcular_progreso(id_entrenamiento):
        query = """
        SELECT 
            COUNT(DISTINCT p.id_progreso) * 100.0 / COUNT(DISTINCT de.id_dia_ejercicio) AS progreso
        FROM entrenamiento e
        JOIN semanas s ON e.id_entrenamiento = s.id_entrenamiento
        JOIN dias d ON s.id_semana = d.id_semana
        JOIN dia_ejercicio de ON d.id_dia = de.id_dia
        LEFT JOIN progreso_alumno p ON de.id_dia_ejercicio = p.id_dia_ejercicio
        WHERE e.id_entrenamiento = ?
        GROUP BY e.id_entrenamiento;
        """
        result = db.execute(query, (id_entrenamiento,)).fetchone()
        return round(result["progreso"], 1) if result and result["progreso"] is not None else 0.0

    # Si el usuario es entrenador, buscar entrenamientos donde id_entrenador = id_usuario
    entrenamientos += db.execute("""
        SELECT entrenamiento.*, 
            COALESCE(entrenador.nombre, 'Desconocido') AS entrenador_nombre, 
            COALESCE(entrenador.apellido, '') AS entrenador_apellido,
            disciplina.nombre AS nombre_disciplina
        FROM entrenamiento
        LEFT JOIN entrenador ON entrenamiento.id_entrenador = entrenador.id_usuario
        LEFT JOIN disciplina ON entrenamiento.id_disciplina = disciplina.id_disciplina
        WHERE entrenamiento.id_entrenador = ?
    """, (user_id,)).fetchall()

    # Si el usuario es alumno, buscar entrenamientos donde id_alumno = id_alumno
    if id_alumno:
        entrenamientos += db.execute("""
            SELECT entrenamiento.*, 
                COALESCE(entrenador.nombre, 'Desconocido') AS entrenador_nombre, 
                COALESCE(entrenador.apellido, '') AS entrenador_apellido,
                disciplina.nombre AS nombre_disciplina
            FROM entrenamiento
            LEFT JOIN entrenador ON entrenamiento.id_entrenador = entrenador.id_usuario
            LEFT JOIN disciplina ON entrenamiento.id_disciplina = disciplina.id_disciplina
            WHERE entrenamiento.id_alumno = ?
        """, (id_alumno,)).fetchall()

    # Agregar progreso a cada entrenamiento
    entrenamientos_con_progreso = []
    for entrenamiento in entrenamientos:
        progreso = calcular_progreso(entrenamiento["id_entrenamiento"])
        entrenamiento_dict = dict(entrenamiento)
        entrenamiento_dict["progreso"] = progreso
        entrenamientos_con_progreso.append(entrenamiento_dict)

    return render_template('entrenamiento.html',
                           entrenamientos=entrenamientos_con_progreso,
                           asociacion=asociacion,
                           rol_usuario=rol_usuario)


# Ruta de Crear Entrenamiento (Todo en uno)
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

            # Insertar notificación para el alumno con el formato deseado
            mensaje = f"El entrenador @{entrenador['nombre_usuario']} ha creado un nuevo plan de entrenamiento: {nombre_entrenamiento}."

            cursor.execute('''INSERT INTO notificaciones (id_usuario, mensaje, id_entrenamiento)
                            VALUES (?, ?, ?)''', (id_alumno, mensaje, id_entrenamiento))


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
