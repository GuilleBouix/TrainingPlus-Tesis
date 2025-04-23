from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.helpers import login_required, verificar_formulario_completo
from app.utils.conexion import conexion_basedatos
from datetime import datetime


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


# Función paa obtener el promedio de semanas de las rutinas.
def obtener_promedio_semanas(id_entrenador):
    conn = conexion_basedatos()
    cur = conn.cursor()
    
    # Consulta para obtener el promedio de duración de las rutinas
    query = """
        SELECT AVG(duracion_semanas) as promedio_semanas
        FROM entrenamiento
        WHERE id_entrenador = ?
    """
    
    cur.execute(query, (id_entrenador,))
    resultado = cur.fetchone()
    
    conn.close()
    
    if resultado and resultado['promedio_semanas'] is not None:
        return round(resultado['promedio_semanas'], 1)
    return 0


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
def dashboard():
    id_entrenador = session.get('id_usuario')
    
    # Obtener el total de alumnos con planes activos
    total_alumnos = obtener_total_alumnos(id_entrenador)

    # Obtener el promedio de cumplimiento
    cumplimiento_promedio = obtener_cumplimiento_promedio(id_entrenador)

    # Obtener el promedio de semanas
    promedio_semanas = obtener_promedio_semanas(id_entrenador)

    # Obtener alumnos vinculados
    alumnos_vinculados = obtener_alumnos_vinculados(id_entrenador)

    # Obtener datos de tipos de fuerza para todos los alumnos
    datos_fuerza = obtener_datos_tipos_fuerza(id_entrenador)

    # Obtener ranking de cumplimiento
    ranking_cumplimiento = obtener_ranking_cumplimiento(id_entrenador)

    return render_template('dashboard.html',
                           total_alumnos=total_alumnos,
                           cumplimiento_promedio=cumplimiento_promedio,
                           promedio_semanas=promedio_semanas,
                           alumnos_vinculados=alumnos_vinculados,
                           datos_fuerza=datos_fuerza,
                           ranking_cumplimiento=ranking_cumplimiento)


# Ruta de Progreso Alumno
@dashboard_bp.route('/dashboard/progreso-alumno/<alumno_id>', methods=['GET', 'POST'])
@login_required
def progreso_alumno(alumno_id):
    return render_template('progreso_alumno.html', alumno_id=alumno_id)