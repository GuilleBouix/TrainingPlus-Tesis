from app.utils.helpers import login_required, entrenador_required, verificar_formulario_completo, verificar_suscripcion
from flask import Blueprint, render_template, session, send_file, flash, redirect, url_for
from app.routes.progreso import obtener_mejores_marcas
from app.utils.conexion import conexion_basedatos
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
from io import BytesIO


dashboard_bp = Blueprint('dashboard', __name__)


# Función para obtener el total de alumnos que tiene un entrenador
def obtener_total_alumnos(id_entrenador):
    conn = conexion_basedatos()
    cur = conn.cursor()
    
    # Consulta para obtener el total de alumnos únicos con planes activos
    query = """
        SELECT COUNT(DISTINCT e.id_alumno) as total_alumnos
        FROM entrenamiento e
        WHERE e.id_entrenador = ?
    """
    
    cur.execute(query, (id_entrenador,))
    resultado = cur.fetchone()
    total = resultado['total_alumnos'] if resultado else 0
    
    conn.close()
    return total


# Función para obtener la adherencia promedio
def obtener_adherencia_promedio(id_entrenador):
    conn = conexion_basedatos()
    cur = conn.cursor()

    # Obtener todos los entrenamientos asignados por el entrenador
    query = """
        SELECT 
            e.id_alumno,
            COUNT(DISTINCT d.id_dia) AS total_dias,
            COUNT(DISTINCT CASE WHEN d.completado = 1 THEN d.id_dia END) AS dias_completados
        FROM entrenamiento e
        JOIN semanas s ON e.id_entrenamiento = s.id_entrenamiento
        JOIN dias d ON s.id_semana = d.id_semana
        WHERE e.id_entrenador = ?
        GROUP BY e.id_alumno
    """

    cur.execute(query, (id_entrenador,))
    resultados = cur.fetchall()

    conn.close()

    if not resultados:
        return 0.0

    # Calcular la adherencia de cada alumno y hacer promedio
    adherencias = []
    for fila in resultados:
        total = fila['total_dias']
        completados = fila['dias_completados']

        if total > 0:
            porcentaje = (completados / total) * 100
            adherencias.append(porcentaje)

    adherencia_promedio = round(sum(adherencias) / len(adherencias), 1) if adherencias else 0.0

    return adherencia_promedio


# Función obtener cumplimiento promedio de todos los alumnos en sus rutinas
def obtener_cumplimiento_promedio(id_entrenador):
    conn = conexion_basedatos()
    cur = conn.cursor()
    
    # Consulta para obtener el progreso de todos los entrenamientos del entrenador
    query = """
        SELECT 
            e.id_entrenamiento,
            e.id_alumno,
            COUNT(DISTINCT de.id_dia_ejercicio) as total_ejercicios,
            COUNT(DISTINCT p.id_progreso) as ejercicios_completados
        FROM entrenamiento e
        JOIN semanas s ON e.id_entrenamiento = s.id_entrenamiento
        JOIN dias d ON s.id_semana = d.id_semana
        JOIN dia_ejercicio de ON d.id_dia = de.id_dia
        LEFT JOIN progreso_alumno p ON de.id_dia_ejercicio = p.id_dia_ejercicio AND p.id_alumno = e.id_alumno
        WHERE e.id_entrenador = ?
        GROUP BY e.id_entrenamiento, e.id_alumno
    """
    
    cur.execute(query, (id_entrenador,))
    resultados = cur.fetchall()
    
    if not resultados:
        conn.close()
        return 0  # Retorna 0 si no hay entrenamientos
    
    # Calcular porcentajes individuales y el promedio
    porcentajes = []
    for resultado in resultados:
        total = resultado['total_ejercicios']
        completados = resultado['ejercicios_completados']
        if total > 0:
            porcentaje = (completados / total) * 100
            porcentajes.append(porcentaje)
    
    promedio = sum(porcentajes) / len(porcentajes) if porcentajes else 0
    promedio_redondeado = round(promedio, 1)
    
    conn.close()
    
    return promedio_redondeado


# Función para obtener alumnos vinculados y sus rutinas de entrenamiento
def obtener_alumnos_vinculados(id_entrenador):
    conn = conexion_basedatos()
    cur = conn.cursor()
    
    # Consulta para obtener alumnos vinculados y sus rutinas
    query = """
        SELECT 
            a.id_alumno,
            a.nombre,
            a.apellido,
            COALESCE(a.foto_perfil, 'profile.webp') as foto_perfil,
            e.nombre_entrenamiento,
            e.fecha_inicio,
            e.id_entrenamiento
        FROM vinculaciones v
        JOIN alumno a ON v.id_usuario_destino = a.id_usuario
        LEFT JOIN entrenamiento e ON a.id_alumno = e.id_alumno AND e.id_entrenador = ?
        WHERE v.id_usuario_origen = ? AND v.estado = 'aceptada'
        GROUP BY a.id_alumno
        ORDER BY a.apellido, a.nombre
    """
    
    cur.execute(query, (id_entrenador, id_entrenador))
    alumnos = cur.fetchall()
    
    conn.close()
    
    # Formatear los datos
    resultados = []
    for alumno in alumnos:
        if alumno['fecha_inicio']:
            fecha_obj = datetime.strptime(alumno['fecha_inicio'], '%Y-%m-%d')
            fecha_formateada = fecha_obj.strftime('%#d/%#m/%Y')  # ✅ esto funciona en Windows
        else:
            fecha_formateada = '- - / - - / - - - -'

        resultados.append({
            'id_alumno': alumno['id_alumno'],
            'nombre_completo': f"{alumno['nombre']} {alumno['apellido']}",
            'foto_perfil': alumno['foto_perfil'],
            'rutina': alumno['nombre_entrenamiento'] if alumno['nombre_entrenamiento'] else 'Sin rutina asignada',
            'fecha': fecha_formateada,
            'tiene_rutina': bool(alumno['nombre_entrenamiento'])
        })
    
    return resultados


# Función para obtener datos de los tipos de fuerza en general
def obtener_datos_tipos_fuerza(id_entrenador):
    conn = conexion_basedatos()
    cur = conn.cursor()
    
    # Consulta corregida que solo considera ejercicios CON progreso registrado
    query = """
        SELECT 
            e.tipo_fuerza,
            COUNT(DISTINCT de.id_dia_ejercicio) as total_ejercicios,
            AVG(p.peso_utilizado) as avg_peso,
            AVG(p.repeticiones_realizadas) as avg_rep,
            MAX(p.peso_utilizado) as max_peso,
            MAX(p.repeticiones_realizadas) as max_rep,
            COUNT(DISTINCT en.id_alumno) as total_alumnos
        FROM dia_ejercicio de
        JOIN ejercicios e ON de.id_ejercicio = e.id_ejercicio
        JOIN dias d ON de.id_dia = d.id_dia
        JOIN semanas s ON d.id_semana = s.id_semana
        JOIN entrenamiento en ON s.id_entrenamiento = en.id_entrenamiento
        INNER JOIN progreso_alumno p ON de.id_dia_ejercicio = p.id_dia_ejercicio  -- CAMBIÉ A INNER JOIN
        WHERE en.id_entrenador = ? 
          AND e.tipo_fuerza IS NOT NULL
          AND p.peso_utilizado IS NOT NULL 
          AND p.repeticiones_realizadas IS NOT NULL
        GROUP BY e.tipo_fuerza
    """
    
    cur.execute(query, (id_entrenador,))
    fuerza_data = cur.fetchall()
    
    # Procesamiento de datos
    tipos_fuerza = ['Empuje', 'Jale', 'Resistencia']
    datos_grafico = {tipo: 0 for tipo in tipos_fuerza}
    total_alumnos = 0
    
    for registro in fuerza_data:
        tipo, total, avg_peso, avg_rep, max_peso, max_rep, alumnos = registro
        
        if tipo in datos_grafico:
            # Asegurar que no hay valores None
            avg_peso = avg_peso or 0
            avg_rep = avg_rep or 0
            
            if tipo == 'Resistencia':
                indice = (avg_peso * 0.3 + avg_rep * 0.7) * 2
            else:
                indice = (avg_peso * 0.7 + avg_rep * 0.3) * 2
                
            datos_grafico[tipo] = round(indice * alumnos)
            
            if alumnos > total_alumnos:
                total_alumnos = alumnos
    
    # Normalización
    if total_alumnos > 0:
        max_valor = max(datos_grafico.values()) if datos_grafico.values() else 1
        if max_valor > 0:
            for tipo in datos_grafico:
                datos_grafico[tipo] = round((datos_grafico[tipo] / max_valor) * 100)
    
    conn.close()
    
    return {
        'tipos_fuerza': tipos_fuerza,
        'valores': [datos_grafico[tipo] for tipo in tipos_fuerza],
        'detalle': {
            'Empuje': {
                'avg_peso': next((round(r[2], 1) if r[2] else 0 for r in fuerza_data if r[0] == 'Empuje'), 0),
                'avg_rep': next((round(r[3], 1) if r[3] else 0 for r in fuerza_data if r[0] == 'Empuje'), 0),
                'alumnos': next((r[6] for r in fuerza_data if r[0] == 'Empuje'), 0)
            },
            'Jale': {
                'avg_peso': next((round(r[2], 1) if r[2] else 0 for r in fuerza_data if r[0] == 'Jale'), 0),
                'avg_rep': next((round(r[3], 1) if r[3] else 0 for r in fuerza_data if r[0] == 'Jale'), 0),
                'alumnos': next((r[6] for r in fuerza_data if r[0] == 'Jale'), 0)
            },
            'Resistencia': {
                'avg_peso': next((round(r[2], 1) if r[2] else 0 for r in fuerza_data if r[0] == 'Resistencia'), 0),
                'avg_rep': next((round(r[3], 1) if r[3] else 0 for r in fuerza_data if r[0] == 'Resistencia'), 0),
                'alumnos': next((r[6] for r in fuerza_data if r[0] == 'Resistencia'), 0)
            }
        }
    }

# Función para obtener la evolución del peso mensual de los alumnos
def obtener_evolucion_peso_mensual(id_entrenador):
    conn = conexion_basedatos()
    cur = conn.cursor()

    query = """
        SELECT 
            a.id_alumno,
            a.nombre || ' ' || a.apellido as nombre_alumno,
            pa.fecha,
            pa.peso_utilizado,
            pa.series_realizadas,
            pa.repeticiones_realizadas
        FROM progreso_alumno pa
        JOIN alumno a ON pa.id_alumno = a.id_alumno
        JOIN entrenamiento en ON a.id_alumno = en.id_alumno
        WHERE en.id_entrenador = ? AND pa.fecha IS NOT NULL
        ORDER BY a.id_alumno, pa.fecha
    """

    cur.execute(query, (id_entrenador,))
    resultados = cur.fetchall()

    # Diccionario para almacenar los datos por alumno
    alumnos_data = {}

    for fila in resultados:
        id_alumno, nombre_alumno, fecha_str, peso, series, reps = fila

        if not fecha_str or not peso or not series or not reps:
            continue

        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        mes_key = fecha.strftime("%Y-%m")

        if id_alumno not in alumnos_data:
            alumnos_data[id_alumno] = {
                'nombre': nombre_alumno,
                'data': {}
            }

        peso_total = peso * series * reps
        alumnos_data[id_alumno]['data'][mes_key] = alumnos_data[id_alumno]['data'].get(mes_key, 0) + peso_total

    # Procesar los datos para tener todos los meses consistentes
    todos_los_meses = set()
    for alumno in alumnos_data.values():
        todos_los_meses.update(alumno['data'].keys())
    
    meses_ordenados = sorted(todos_los_meses)

    # Preparar los datos finales
    datos_grafico = {
        'meses': meses_ordenados,
        'alumnos': []
    }

    # Generar colores únicos para cada alumno
    colores = [
        '#9333EA', '#3B82F6', '#10B981', '#F59E0B', 
        '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6'
    ]

    for i, (id_alumno, alumno_data) in enumerate(alumnos_data.items()):
        datos_alumno = {
            'id': id_alumno,
            'nombre': alumno_data['nombre'],
            'color': colores[i % len(colores)],
            'totales': []
        }

        for mes in meses_ordenados:
            datos_alumno['totales'].append(round(alumno_data['data'].get(mes, 0), 1))

        datos_grafico['alumnos'].append(datos_alumno)

    conn.close()

    return datos_grafico


# Ruta de Dashboard
@dashboard_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
@entrenador_required
@verificar_suscripcion
@verificar_formulario_completo
def dashboard():
    id_entrenador = session.get('id_usuario')
    
    # Verificar si el entrenador tiene al menos un entrenamiento asignado
    conexion = conexion_basedatos()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM entrenamiento 
        WHERE id_entrenador = ?
    """, (id_entrenador,))
    resultado = cursor.fetchone()
    conexion.close()

    if resultado[0] == 0:
        flash("Debes tener al menos una rutina de entrenamiento activa para acceder al dashboard.", "error")
        return redirect(url_for('entrenamiento.entrenamiento'))

    # Obtener el total de alumnos con planes activos
    total_alumnos = obtener_total_alumnos(id_entrenador)

    # Obtener el promedio de adherencia
    adherencia_promedio = obtener_adherencia_promedio(id_entrenador)

    # Obtener el promedio de cumplimiento
    cumplimiento_promedio = obtener_cumplimiento_promedio(id_entrenador)

    # Obtener alumnos vinculados
    alumnos_vinculados = obtener_alumnos_vinculados(id_entrenador)

    # Obtener datos de tipos de fuerza para todos los alumnos
    datos_fuerza = obtener_datos_tipos_fuerza(id_entrenador)

    # Obtener evolución del peso mensual de los alumnos
    evolucion_peso = obtener_evolucion_peso_mensual(id_entrenador)


    return render_template('dashboard.html',
                           total_alumnos=total_alumnos,
                           adherencia_promedio=adherencia_promedio,
                           cumplimiento_promedio=cumplimiento_promedio,
                           alumnos_vinculados=alumnos_vinculados,
                           datos_fuerza=datos_fuerza,
                           evolucion_peso=evolucion_peso)


# Obtener nombre, apellido y foto de perfil del alumno
def obtener_datos_alumno(alumno_id):
    conn = conexion_basedatos()
    cursor = conn.cursor()

    cursor.execute('SELECT id_alumno, nombre, apellido, foto_perfil FROM alumno WHERE id_alumno = ?', (alumno_id,))
    alumno = cursor.fetchone()
    conn.close()

    if alumno:
        alumno_id = alumno['id_alumno']
        nombre = alumno['nombre']
        apellido = alumno['apellido']
        foto = alumno['foto_perfil'] if alumno['foto_perfil'] else 'profile.webp'
        return {
            'id_alumno': alumno_id,
            'nombre': nombre,
            'apellido': apellido,
            'foto_perfil': f'uploads/users/{foto}'
        }
    else:
        return None


# Obtener entrenamiento del alumno
def obtener_entrenamiento(alumno_id, entrenador_id):
    conn = conexion_basedatos()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id_entrenamiento, nombre_entrenamiento, fecha_inicio
        FROM entrenamiento
        WHERE id_alumno = ? AND id_entrenador = ?
        LIMIT 1
    ''', (alumno_id, entrenador_id))
    row = cursor.fetchone()
    conn.close()

    if row:
        id_entrenamiento = row[0]
        nombre = row[1]
        fecha_str = row[2]

        # Si hay fecha, formatearla
        if fecha_str:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
            fecha_formateada = fecha_obj.strftime('%d/%m/%Y')
        else:
            fecha_formateada = None

        return {
            'id_entrenamiento': id_entrenamiento,
            'nombre_entrenamiento': nombre,
            'fecha_inicio': fecha_formateada
        }
    else:
        return None


# Obtener el porcentaje de progreso del alumno en su entrenamiento
def obtener_porcentaje_progreso(alumno_id, id_entrenamiento):
    conn = conexion_basedatos()
    cur = conn.cursor()

    query = """
        SELECT 
            COALESCE(
                (SELECT COUNT(DISTINCT p.id_progreso) * 100.0 / NULLIF(COUNT(DISTINCT de.id_dia_ejercicio), 0)
                 FROM semanas s 
                 JOIN dias d ON s.id_semana = d.id_semana
                 JOIN dia_ejercicio de ON d.id_dia = de.id_dia
                 LEFT JOIN progreso_alumno p 
                    ON de.id_dia_ejercicio = p.id_dia_ejercicio AND p.id_alumno = ?
                 WHERE s.id_entrenamiento = ?
                ), 0) as progreso
    """
    cur.execute(query, (alumno_id, id_entrenamiento))
    resultado = cur.fetchone()
    conn.close()

    return resultado[0] if resultado else 0


# Obtener datos del cuestionario del alumno
def obtener_datos_cuestionario(alumno_id):
    conn = conexion_basedatos()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM cuestionario WHERE id_alumno = ?', (alumno_id,))
    fila = cursor.fetchone()
    conn.close()

    if fila:
        columnas = [
            "id_cuestionario", "id_alumno", "objetivo_general", "edad", "altura", "peso",
            "nivel_actividad", "experiencia", "frecuencia_entreno", "duracion_sesion",
            "estado_salud", "lesiones", "condicion_cardio", "nivel_estres",
            "notas_alumno", "fecha_completado"
        ]
        return dict(zip(columnas, fila))
    else:
        return None


# Obtener el rendimiento por semana del alumno en la rutina
def obtener_rendimiento_semanal(alumno_id, id_entrenamiento):
    conn = None
    try:
        conn = conexion_basedatos()
        cur = conn.cursor()
        
        # Consulta para obtener el volumen de entrenamiento por semana
        query = """
            SELECT 
                s.numero_semana,
                SUM(pa.peso_utilizado * pa.repeticiones_realizadas * pa.series_realizadas) as volumen_total
            FROM semanas s
            JOIN dias d ON s.id_semana = d.id_semana
            JOIN dia_ejercicio de ON d.id_dia = de.id_dia
            JOIN progreso_alumno pa ON de.id_dia_ejercicio = pa.id_dia_ejercicio
            WHERE s.id_entrenamiento = ? AND pa.id_alumno = ?
            GROUP BY s.numero_semana
            ORDER BY s.numero_semana ASC
        """
        
        cur.execute(query, (id_entrenamiento, alumno_id))
        rendimiento_data = cur.fetchall()
        
        # Obtener el número total de semanas del entrenamiento
        query_semanas = """
            SELECT duracion_semanas 
            FROM entrenamiento 
            WHERE id_entrenamiento = ?
        """
        cur.execute(query_semanas, (id_entrenamiento,))
        total_semanas = cur.fetchone()[0]
        
        # Preparar los datos para el gráfico
        semanas = []
        volumenes = []
        
        # Inicializar todas las semanas con volumen 0
        for semana in range(1, total_semanas + 1):
            semanas.append(f"Sem {semana}")
            volumenes.append(0)
        
        # Llenar los datos reales
        for registro in rendimiento_data:
            num_semana = registro[0]
            volumen = registro[1] if registro[1] else 0
            if 1 <= num_semana <= total_semanas:
                volumenes[num_semana - 1] = round(volumen)
        
        # Normalizar los valores para que el máximo sea 100 (opcional)
        max_volumen = max(volumenes) if volumenes else 1
        if max_volumen > 0:
            volumenes_normalizados = [round((v / max_volumen) * 100) for v in volumenes]
        else:
            volumenes_normalizados = volumenes
        
        return {
            'semanas': semanas,
            'volumenes': volumenes,
            'volumenes_normalizados': volumenes_normalizados,
            'detalle': [
                {
                    'semana': registro[0],
                    'volumen': round(registro[1]) if registro[1] else 0
                } for registro in rendimiento_data
            ]
        }
        
    except Exception as e:
        print(f"Error en obtener_rendimiento_semanal: {str(e)}")
        return {
            'semanas': [],
            'volumenes': [],
            'volumenes_normalizados': [],
            'detalle': []
        }
    finally:
        if conn:
            conn.close()


# Obtener progreso de fuerza (empuje, jale y resistencia) del alumno en la rutina
def obtener_progreso_fuerza(alumno_id, id_entrenamiento):
    conn = None
    try:
        conn = conexion_basedatos()
        cur = conn.cursor()
        
        # Consulta para obtener el progreso de fuerza por tipo y por semana
        query = """
            SELECT 
                s.numero_semana,
                e.tipo_fuerza,
                AVG(COALESCE(pa.peso_utilizado, 0)) as avg_peso,
                AVG(COALESCE(pa.repeticiones_realizadas, 0)) as avg_repeticiones,
                COUNT(DISTINCT de.id_dia_ejercicio) as total_ejercicios
            FROM semanas s
            JOIN dias d ON s.id_semana = d.id_semana
            JOIN dia_ejercicio de ON d.id_dia = de.id_dia
            JOIN ejercicios e ON de.id_ejercicio = e.id_ejercicio
            LEFT JOIN progreso_alumno pa ON de.id_dia_ejercicio = pa.id_dia_ejercicio AND pa.id_alumno = ?
            WHERE s.id_entrenamiento = ? AND e.tipo_fuerza IN ('Empuje', 'Jale', 'Resistencia')
            GROUP BY s.numero_semana, e.tipo_fuerza
            ORDER BY s.numero_semana ASC, e.tipo_fuerza
        """
        
        cur.execute(query, (alumno_id, id_entrenamiento))
        fuerza_data = cur.fetchall()
        
        # Obtener el número total de semanas del entrenamiento
        query_semanas = """
            SELECT duracion_semanas 
            FROM entrenamiento 
            WHERE id_entrenamiento = ?
        """
        cur.execute(query_semanas, (id_entrenamiento,))
        total_semanas = cur.fetchone()[0]
        
        # Preparar los datos para el gráfico
        semanas = [f"Semana {i}" for i in range(1, total_semanas + 1)]
        
        # Inicializar datos para cada tipo de fuerza
        empuje = [0] * total_semanas
        jale = [0] * total_semanas
        resistencia = [0] * total_semanas
        
        # Procesar los datos obtenidos
        for registro in fuerza_data:
            semana = registro[0] - 1  # Convertir a índice 0-based
            tipo = registro[1]
            avg_peso = registro[2]
            avg_rep = registro[3]
            total_ej = registro[4]
            
            # Calcular índice de fuerza (fórmula ajustable)
            if tipo == 'Empuje':
                indice = (avg_peso * 0.7 + avg_rep * 0.3) * (total_ej / 10)  # Ajustar división según necesidad
                if semana < len(empuje):
                    empuje[semana] = round(indice)
            elif tipo == 'Jale':
                indice = (avg_peso * 0.6 + avg_rep * 0.4) * (total_ej / 10)
                if semana < len(jale):
                    jale[semana] = round(indice)
            elif tipo == 'Resistencia':
                indice = (avg_peso * 0.3 + avg_rep * 0.7) * (total_ej / 10)
                if semana < len(resistencia):
                    resistencia[semana] = round(indice)
        
        # Normalizar los valores para que el máximo sea 100
        max_valor = max(max(empuje), max(jale), max(resistencia)) or 1
        empuje_norm = [round((v / max_valor) * 100) for v in empuje]
        jale_norm = [round((v / max_valor) * 100) for v in jale]
        resistencia_norm = [round((v / max_valor) * 100) for v in resistencia]
        
        return {
            'semanas': semanas,
            'empuje': empuje_norm,
            'jale': jale_norm,
            'resistencia': resistencia_norm,
            'detalle': [
                {
                    'semana': registro[0],
                    'tipo': registro[1],
                    'avg_peso': registro[2],
                    'avg_rep': registro[3],
                    'total_ejercicios': registro[4]
                } for registro in fuerza_data
            ]
        }
        
    except Exception as e:
        print(f"Error en obtener_progreso_fuerza: {str(e)}")
        return {
            'semanas': [],
            'empuje': [],
            'jale': [],
            'resistencia': [],
            'detalle': []
        }
    finally:
        if conn:
            conn.close()


# Obtener progreso semanal del alumno en la rutina
def obtener_progreso_semanal(alumno_id, id_entrenamiento):
    conn = None
    try:
        conn = conexion_basedatos()
        cur = conn.cursor()
        
        # Consulta simplificada sin la fecha
        query = """
            SELECT 
                s.numero_semana,
                ps.observaciones,
                ps.foto_fisico
            FROM progreso_semana ps
            JOIN semanas s ON ps.id_semana = s.id_semana
            WHERE ps.id_alumno = ? AND ps.id_entrenamiento = ?
            ORDER BY s.numero_semana ASC
        """
        
        cur.execute(query, (alumno_id, id_entrenamiento))
        progreso_data = cur.fetchall()
        
        # Procesamiento seguro de los datos
        observaciones_semanales = []
        for semana, observacion, foto in progreso_data:
            observaciones_semanales.append({
                'semana': f"Semana {semana}",
                'observacion': observacion if observacion else "Sin observaciones",
                'foto': f"/static/uploads/weekly_progress/{foto}" if foto else None
            })
        
        print(f"Datos obtenidos: {observaciones_semanales}")  # Para depuración
        return observaciones_semanales
        
    except Exception as e:
        print(f"Error al obtener progreso semanal: {str(e)}")
        return []  # Devuelve lista vacía si hay error
    finally:
        if conn:
            conn.close()


# Ruta para descargar la ficha del alumno en PDF
@dashboard_bp.route('/descargar_ficha_pdf/<int:alumno_id>', methods=['GET'])
@login_required
@entrenador_required
@verificar_suscripcion
@verificar_formulario_completo
def descargar_ficha_pdf(alumno_id):
    # Obtener datos del alumno
    alumno = obtener_datos_alumno(alumno_id)
    if not alumno:
        return "Alumno no encontrado", 404
    
    # Obtener datos del cuestionario
    cuestionario = obtener_datos_cuestionario(alumno_id)
    if not cuestionario:
        return "Cuestionario no encontrado", 404

    # Crear buffer en memoria
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Estilos
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, height - 50, f"Ficha de {alumno['nombre']} {alumno['apellido']}")
    
    # Información Personal
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, height - 80, "1. Información Personal")
    
    p.setFont("Helvetica", 12)
    y = height - 110
    p.drawString(100, y, f"     Edad: {cuestionario.get('edad', 'N/A')} años")
    y -= 20
    p.drawString(100, y, f"     Experiencia: {cuestionario.get('experiencia', 'N/A').capitalize()}")
    y -= 20
    p.drawString(100, y, f"     Objetivo: {cuestionario.get('objetivo_general', 'N/A')}")
    y -= 40

    # Datos Físicos
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y, "2. Datos Físicos")
    
    p.setFont("Helvetica", 12)
    y -= 30
    p.drawString(100, y, f"     Peso: {cuestionario.get('peso', 'N/A')} kg")
    y -= 20
    p.drawString(100, y, f"     Altura: {cuestionario.get('altura', 'N/A')} cm")
    y -= 40

    # Entrenamiento
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y, "3. Entrenamiento")
    
    p.setFont("Helvetica", 12)
    y -= 30
    p.drawString(100, y, f"     Nivel de Actividad: {cuestionario.get('nivel_actividad', 'N/A').capitalize()}")
    y -= 20
    p.drawString(100, y, f"     Frecuencia: {cuestionario.get('frecuencia_entreno', 'N/A').capitalize()}")
    y -= 20
    p.drawString(100, y, f"     Duración de Entrenamiento: {cuestionario.get('duracion_sesion', 'N/A')}")
    y -= 40

    # Estado de Salud
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y, "4. Estado de Salud")
    
    p.setFont("Helvetica", 12)
    y -= 30
    p.drawString(100, y, f"     Estado General: {cuestionario.get('estado_salud', 'N/A').capitalize()}")
    y -= 20
    p.drawString(100, y, f"     Lesiones: {cuestionario.get('lesiones', 'N/A').capitalize()}")
    y -= 20
    p.drawString(100, y, f"     Condición Cardiovascular: {cuestionario.get('condicion_cardio', 'N/A').capitalize()}")
    y -= 20
    p.drawString(100, y, f"     Nivel de Estrés: {cuestionario.get('nivel_estres', 'N/A').capitalize()}")
    y -= 40

    # Notas Adicionales
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y, "5. Notas Adicionales")
    
    p.setFont("Helvetica", 12)
    y -= 30
    nota = cuestionario.get('nota_adicional', 'No hay notas adicionales.')
    # Dividir texto largo en múltiples líneas
    nota_lines = []
    max_line_length = 80
    words = nota.split()
    current_line = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + len(current_line) <= max_line_length:
            current_line.append(word)
            current_length += len(word)
        else:
            nota_lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
    
    if current_line:
        nota_lines.append(' '.join(current_line))
    
    for line in nota_lines:
        if y < 100:  # Si nos quedamos sin espacio, crear nueva página
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 12)
        p.drawString(100, y, f"     {line}")
        y -= 20

    # Pie de página
    p.setFont("Helvetica", 10)
    p.drawString(100, 30, f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    p.showPage()
    p.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"ficha_{alumno['nombre']}_{alumno['apellido']}.pdf",
        mimetype='application/pdf'
    )


# Ruta de Progreso Alumno
@dashboard_bp.route('/dashboard/progreso-alumno/<alumno_id>', methods=['GET', 'POST'])
@login_required
@entrenador_required
@verificar_suscripcion
@verificar_formulario_completo
def progreso_alumno(alumno_id):
    id_entrenador = session.get('id_usuario')

    # Obtener datos del alumno
    datos_alumno = obtener_datos_alumno(alumno_id)

    # Obtener entrenamiento asociado al entrenador de la sesión
    entrenamiento = obtener_entrenamiento(alumno_id, id_entrenador)
    id_entrenamiento = entrenamiento['id_entrenamiento']
    porcentaje_progreso = obtener_porcentaje_progreso(alumno_id, id_entrenamiento)

    # Obtener datos del cuestionario del alumno
    datos_cuestionario = obtener_datos_cuestionario(alumno_id)

    # --------------- Gráficos ---------------
    rendimiento_semanal = obtener_rendimiento_semanal(alumno_id, id_entrenamiento)
    
    progreso_fuerza = obtener_progreso_fuerza(alumno_id, id_entrenamiento)
    print(f"Progreso de fuerza: {progreso_fuerza}")

    mejores_marcas = obtener_mejores_marcas(entrenamiento['id_entrenamiento'], alumno_id)

    observaciones_semanales = obtener_progreso_semanal(alumno_id, id_entrenamiento)
    print(f"Observaciones semanales: {observaciones_semanales}")


    return render_template('progreso_alumno.html',
                           alumno=datos_alumno,
                           entrenamiento=entrenamiento,
                           porcentaje_progreso=porcentaje_progreso,
                           cuestionario=datos_cuestionario,
                           rendimiento_semanal=rendimiento_semanal,
                           progreso_fuerza=progreso_fuerza,
                           mejores_marcas=mejores_marcas,
                           observaciones_semanales=observaciones_semanales)


# Ruta para ver observaciones del alumno
@dashboard_bp.route('/dashboard/progreso-alumno/<alumno_id>/observaciones', methods=['GET'])
@login_required
@entrenador_required
@verificar_suscripcion
@verificar_formulario_completo
def reporte_observaciones(alumno_id):
    id_entrenador = session.get('id_usuario')

    conexion = conexion_basedatos()
    cursor = conexion.cursor()

    # Obtener nombre y apellido del alumno
    cursor.execute("""
        SELECT nombre, apellido 
        FROM alumno 
        WHERE id_alumno = ?
    """, (alumno_id,))
    datos_alumno = cursor.fetchone()

    if not datos_alumno:
        conexion.close()
        flash("Alumno no encontrado", "error")
        return redirect(url_for('dashboard.dashboard'))

    alumno = {
        'nombre': datos_alumno[0],
        'apellido': datos_alumno[1]
    }

    # Obtener observaciones con datos relacionados
    cursor.execute("""
        SELECT 
            pa.fecha,
            s.numero_semana,
            d.numero_dia,
            e.nombre_ejercicio,
            e.tipo_fuerza,
            pa.observaciones
        FROM progreso_alumno pa
        JOIN dia_ejercicio de ON pa.id_dia_ejercicio = de.id_dia_ejercicio
        JOIN dias d ON de.id_dia = d.id_dia
        JOIN semanas s ON d.id_semana = s.id_semana
        JOIN ejercicios e ON de.id_ejercicio = e.id_ejercicio
        WHERE pa.id_alumno = ?
        AND pa.observaciones IS NOT NULL
        AND TRIM(pa.observaciones) != ''
        ORDER BY pa.fecha DESC
    """, (alumno_id,))
    observaciones = cursor.fetchall()
    conexion.close()

    # Formatear para pasar al HTML
    lista_observaciones = []
    for obs in observaciones:
        fecha_formateada = datetime.strptime(obs[0], '%Y-%m-%d').strftime('%d/%m/%Y') if obs[0] else ''
        lista_observaciones.append({
            'fecha': fecha_formateada,
            'semana': obs[1],
            'dia': obs[2],
            'ejercicio': obs[3],
            'movimiento': obs[4],
            'observacion': obs[5]
        })



    return render_template('reporte_observaciones.html',
                           alumno_id=alumno_id,
                           alumno=alumno,
                           observaciones=lista_observaciones)