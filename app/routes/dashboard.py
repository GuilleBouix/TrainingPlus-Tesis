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
    
    # Consulta para obtener el progreso de fuerza por tipo para todos los alumnos del entrenador
    query = """
        SELECT 
            e.tipo_fuerza,
            COUNT(DISTINCT de.id_dia_ejercicio) as total_ejercicios,
            AVG(COALESCE(p.peso_utilizado, 0)) as avg_peso,
            AVG(COALESCE(p.repeticiones_realizadas, 0)) as avg_repeticiones,
            MAX(COALESCE(p.peso_utilizado, 0)) as max_peso,
            MAX(COALESCE(p.repeticiones_realizadas, 0)) as max_repeticiones,
            COUNT(DISTINCT en.id_alumno) as total_alumnos
        FROM dia_ejercicio de
        JOIN ejercicios e ON de.id_ejercicio = e.id_ejercicio
        JOIN dias d ON de.id_dia = d.id_dia
        JOIN semanas s ON d.id_semana = s.id_semana
        JOIN entrenamiento en ON s.id_entrenamiento = en.id_entrenamiento
        LEFT JOIN progreso_alumno p ON de.id_dia_ejercicio = p.id_dia_ejercicio
        WHERE en.id_entrenador = ? AND e.tipo_fuerza IS NOT NULL
        GROUP BY e.tipo_fuerza
    """
    
    cur.execute(query, (id_entrenador,))
    fuerza_data = cur.fetchall()
    
    # Procesar los datos para el gráfico
    tipos_fuerza = ['Empuje', 'Jale', 'Resistencia']
    datos_grafico = {tipo: 0 for tipo in tipos_fuerza}
    total_alumnos = 0
    
    for registro in fuerza_data:
        tipo, total, avg_peso, avg_rep, max_peso, max_rep, alumnos = registro
        
        if tipo in datos_grafico:
            # Calcular un índice de fuerza combinando peso y repeticiones
            if tipo == 'Resistencia':
                indice = (avg_peso * 0.3 + avg_rep * 0.7) * 2
            else:
                indice = (avg_peso * 0.7 + avg_rep * 0.3) * 2
                
            # Multiplicar por el número de alumnos para ponderar
            datos_grafico[tipo] = round(indice * alumnos)
            
            if alumnos > total_alumnos:
                total_alumnos = alumnos
    
    # Normalizar los valores para que el máximo sea 100
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
                'avg_peso': next((r[2] for r in fuerza_data if r[0] == 'Empuje'), 0),
                'alumnos': next((r[6] for r in fuerza_data if r[0] == 'Empuje'), 0)
            },
            'Jale': {
                'avg_peso': next((r[2] for r in fuerza_data if r[0] == 'Jale'), 0),
                'alumnos': next((r[6] for r in fuerza_data if r[0] == 'Jale'), 0)
            },
            'Resistencia': {
                'avg_rep': next((r[3] for r in fuerza_data if r[0] == 'Resistencia'), 0),
                'alumnos': next((r[6] for r in fuerza_data if r[0] == 'Resistencia'), 0)
            }
        }
    }


# Función para el ranking de cumplimiento de los alumnos
def obtener_ranking_cumplimiento(id_entrenador):
    conn = None
    try:
        conn = conexion_basedatos()
        cur = conn.cursor()
        
        # Consulta para obtener el cumplimiento por día
        query = """
            SELECT 
                a.nombre || ' ' || COALESCE(a.apellido, '') as nombre_completo,
                COUNT(DISTINCT CASE WHEN d.completado = 1 OR pa.id_progreso IS NOT NULL THEN d.id_dia END) as dias_completados,
                COUNT(DISTINCT d.id_dia) as dias_totales,
                (COUNT(DISTINCT CASE WHEN d.completado = 1 OR pa.id_progreso IS NOT NULL THEN d.id_dia END) * 100.0 / 
                 COUNT(DISTINCT d.id_dia)) as porcentaje_cumplimiento
            FROM alumno a
            JOIN entrenamiento en ON a.id_alumno = en.id_alumno
            JOIN semanas s ON en.id_entrenamiento = s.id_entrenamiento
            JOIN dias d ON s.id_semana = d.id_semana
            LEFT JOIN dia_ejercicio de ON d.id_dia = de.id_dia
            LEFT JOIN progreso_alumno pa ON de.id_dia_ejercicio = pa.id_dia_ejercicio AND a.id_alumno = pa.id_alumno
            WHERE en.id_entrenador = ?
            GROUP BY a.id_alumno, a.nombre, a.apellido
            HAVING dias_totales > 0
            ORDER BY porcentaje_cumplimiento DESC
            LIMIT 6
        """
        
        print(f"Ejecutando consulta para el entrenador: {id_entrenador}")
        cur.execute(query, (id_entrenador,))
        cumplimiento_data = cur.fetchall()
        
        # Depuración
        print(f"Datos crudos obtenidos: {cumplimiento_data}")
        
        # Procesar los datos para el gráfico
        nombres = []
        porcentajes = []
        
        for registro in cumplimiento_data:
            nombre = registro[0] if registro[0] else "Alumno sin nombre"
            completados = registro[1] if registro[1] else 0
            totales = registro[2] if registro[2] else 1  # Evitar división por cero
            porcentaje = (completados * 100.0 / totales) if totales > 0 else 0
            
            nombres.append(nombre)
            porcentajes.append(round(porcentaje))
        
        # Si no hay datos, devolver valores por defecto
        if not cumplimiento_data:
            print("No se encontraron datos de cumplimiento diario")
            return {
                'nombres': ["No hay datos"],
                'porcentajes': [0],
                'detalle': [{
                    'nombre': "No hay datos",
                    'completados': 0,
                    'totales': 1,
                    'porcentaje': 0
                }]
            }
        
        print(f"Datos procesados - Nombres: {nombres}, Porcentajes: {porcentajes}")
        
        return {
            'nombres': nombres,
            'porcentajes': porcentajes,
            'detalle': [
                {
                    'nombre': registro[0] if registro[0] else "Alumno sin nombre",
                    'completados': registro[1] if registro[1] else 0,
                    'totales': registro[2] if registro[2] else 1,
                    'porcentaje': round((registro[1] * 100.0 / registro[2]) if registro[2] > 0 else 0)
                } for registro in cumplimiento_data
            ]
        }
        
    except Exception as e:
        print(f"Error en obtener_ranking_cumplimiento: {str(e)}")
        # Devuelve una estructura vacía pero válida
        return {
            'nombres': ["Error en datos"],
            'porcentajes': [0],
            'detalle': [{
                'nombre': "Error al obtener datos",
                'completados': 0,
                'totales': 1,
                'porcentaje': 0
            }]
        }
    finally:
        if conn:
            conn.close()


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

    # Obtener el promedio de cumplimiento
    cumplimiento_promedio = obtener_cumplimiento_promedio(id_entrenador)

    # Obtener alumnos vinculados
    alumnos_vinculados = obtener_alumnos_vinculados(id_entrenador)

    # Obtener datos de tipos de fuerza para todos los alumnos
    datos_fuerza = obtener_datos_tipos_fuerza(id_entrenador)

    # Obtener ranking de cumplimiento
    ranking_cumplimiento = obtener_ranking_cumplimiento(id_entrenador)

    return render_template('dashboard.html',
                           total_alumnos=total_alumnos,
                           cumplimiento_promedio=cumplimiento_promedio,
                           alumnos_vinculados=alumnos_vinculados,
                           datos_fuerza=datos_fuerza,
                           ranking_cumplimiento=ranking_cumplimiento)


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

    # --------------- Gráfios ---------------
    rendimiento_semanal = obtener_rendimiento_semanal(alumno_id, id_entrenamiento)
    
    progreso_fuerza = obtener_progreso_fuerza(alumno_id, id_entrenamiento)
    print(f"Progreso de fuerza: {progreso_fuerza}")

    mejores_marcas = obtener_mejores_marcas(entrenamiento['id_entrenamiento'], alumno_id)

    observaciones_semanales = obtener_progreso_semanal(alumno_id, id_entrenamiento)
    print(f"Observaciones semanales: {observaciones_semanales}")  # Para verificar


    return render_template('progreso_alumno.html',
                           alumno=datos_alumno,
                           entrenamiento=entrenamiento,
                           porcentaje_progreso=porcentaje_progreso,
                           cuestionario=datos_cuestionario,
                           rendimiento_semanal=rendimiento_semanal,
                           progreso_fuerza=progreso_fuerza,
                           mejores_marcas=mejores_marcas,
                           observaciones_semanales=observaciones_semanales)