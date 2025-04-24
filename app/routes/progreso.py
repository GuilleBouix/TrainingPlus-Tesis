from flask import Blueprint, render_template, request, redirect, url_for, session, json
from app.utils.helpers import login_required, verificar_vinculo_y_rutina
from app.utils.conexion import conexion_basedatos
from datetime import datetime, timedelta


progreso_bp = Blueprint('progreso', __name__)


# Función para obtener datos para el gráfico 'rendimiento'
def obtener_datos_rendimiento(id_entrenamiento, id_alumno):
    conn = conexion_basedatos()
    cur = conn.cursor()
    
    # Consulta corregida para obtener el progreso por semana y el peso total
    query = """
        SELECT 
            s.numero_semana,
            COUNT(d.id_dia) as total_dias,
            SUM(CASE WHEN d.completado = 1 THEN 1 ELSE 0 END) as dias_completados,
            COALESCE(SUM(pa.peso_utilizado * pa.repeticiones_realizadas * pa.series_realizadas), 0) as total_peso
        FROM semanas s
        JOIN dias d ON s.id_semana = d.id_semana
        LEFT JOIN dia_ejercicio de ON d.id_dia = de.id_dia
        LEFT JOIN progreso_alumno pa ON de.id_dia_ejercicio = pa.id_dia_ejercicio AND pa.id_alumno = ?
        WHERE s.id_entrenamiento = ?
        GROUP BY s.numero_semana
        ORDER BY s.numero_semana
    """
    
    cur.execute(query, (id_alumno, id_entrenamiento))
    semanas_data = cur.fetchall()
    
    # Procesar los datos para el gráfico
    semanas = []
    porcentajes = []
    total_pesos = []
    max_peso = 1  # Para evitar división por cero
    
    for semana in semanas_data:
        numero_semana, total_dias, dias_completados, peso_total = semana
        porcentaje = round((dias_completados / total_dias) * 100) if total_dias > 0 else 0
        
        semanas.append(f"Sem {numero_semana}")
        porcentajes.append(porcentaje)
        total_pesos.append(peso_total)
        
        if peso_total > max_peso:
            max_peso = peso_total
    
    # Normalizar los pesos para que estén en escala 0-100
    pesos_normalizados = [round((p / max_peso) * 100) for p in total_pesos] if max_peso > 0 else [0] * len(semanas)
    
    conn.close()
    
    return {
        'semanas': semanas,
        'porcentajes': porcentajes,
        'pesos': total_pesos,
        'pesos_normalizados': pesos_normalizados,
        'max_peso': max_peso,
        'total_semanas': len(semanas)
    }

# Función para obtener datos para el gráfico 'fuerza'
def obtener_datos_fuerza(id_entrenamiento, id_alumno):
    conn = conexion_basedatos()
    cur = conn.cursor()
    
    # Consulta para obtener el progreso de fuerza por tipo
    query = """
        SELECT 
            e.tipo_fuerza,
            COUNT(DISTINCT de.id_dia_ejercicio) as total_ejercicios,
            AVG(COALESCE(p.peso_utilizado, 0)) as avg_peso,
            AVG(COALESCE(p.repeticiones_realizadas, 0)) as avg_repeticiones,
            MAX(COALESCE(p.peso_utilizado, 0)) as max_peso,
            MAX(COALESCE(p.repeticiones_realizadas, 0)) as max_repeticiones
        FROM dia_ejercicio de
        JOIN ejercicios e ON de.id_ejercicio = e.id_ejercicio
        JOIN dias d ON de.id_dia = d.id_dia
        JOIN semanas s ON d.id_semana = s.id_semana
        LEFT JOIN progreso_alumno p ON de.id_dia_ejercicio = p.id_dia_ejercicio AND p.id_alumno = ?
        WHERE s.id_entrenamiento = ?
        GROUP BY e.tipo_fuerza
        HAVING e.tipo_fuerza IS NOT NULL
    """
    
    cur.execute(query, (id_alumno, id_entrenamiento))
    fuerza_data = cur.fetchall()
    
    # Procesar los datos para el gráfico
    tipos_fuerza = ['Empuje', 'Jale', 'Resistencia']
    datos_grafico = {tipo: 0 for tipo in tipos_fuerza}
    
    for registro in fuerza_data:
        tipo, total, avg_peso, avg_rep, max_peso, max_rep = registro
        
        # Calcular un índice de fuerza combinando peso y repeticiones
        if tipo in datos_grafico:
            # Fórmula simple: (peso promedio * repeticiones promedio) / 10
            # Para Resistencia: más peso a las repeticiones
            if tipo == 'Resistencia':
                indice = (avg_peso * 0.3 + avg_rep * 0.7) * 2
            else:
                indice = (avg_peso * 0.7 + avg_rep * 0.3) * 2
                
            datos_grafico[tipo] = round(indice)
    
    # Normalizar los valores para que el máximo sea 100
    max_valor = max(datos_grafico.values()) if datos_grafico.values() else 1
    if max_valor > 0:
        for tipo in datos_grafico:
            datos_grafico[tipo] = round((datos_grafico[tipo] / max_valor) * 100)
    
    conn.close()
    
    return {
        'tipos_fuerza': tipos_fuerza,
        'valores': [datos_grafico[tipo] for tipo in tipos_fuerza],
        'detalle': {
            'Empuje': {'avg_peso': next((r[2] for r in fuerza_data if r[0] == 'Empuje'), 0)},
            'Jale': {'avg_peso': next((r[2] for r in fuerza_data if r[0] == 'Jale'), 0)},
            'Resistencia': {'avg_rep': next((r[3] for r in fuerza_data if r[0] == 'Resistencia'), 0)}
        }
    }

# Función para obtener las mejores marcas (ejercicios con mayor peso levantado)
def obtener_mejores_marcas(id_entrenamiento, id_alumno):
    conn = conexion_basedatos()
    cur = conn.cursor()
    
    # Consulta para obtener los ejercicios con mayor peso
    query = """
        SELECT 
            ej.nombre_ejercicio,
            MAX(pa.peso_utilizado) as max_peso,
            pa.repeticiones_realizadas,
            pa.series_realizadas
        FROM progreso_alumno pa
        JOIN dia_ejercicio de ON pa.id_dia_ejercicio = de.id_dia_ejercicio
        JOIN dias d ON de.id_dia = d.id_dia
        JOIN semanas s ON d.id_semana = s.id_semana
        JOIN ejercicios ej ON de.id_ejercicio = ej.id_ejercicio
        WHERE s.id_entrenamiento = ? AND pa.id_alumno = ?
        GROUP BY ej.nombre_ejercicio, pa.repeticiones_realizadas, pa.series_realizadas
        ORDER BY max_peso DESC
        LIMIT 3
    """
    
    cur.execute(query, (id_entrenamiento, id_alumno))
    mejores_marcas = cur.fetchall()
    
    # Formatear los datos
    resultados = []
    for marca in mejores_marcas:
        nombre, peso, repeticiones, series = marca
        resultados.append({
            'nombre': nombre,
            'peso': peso,
            'repeticiones': repeticiones,
            'series': series,
            'display': f"{peso} Kg x {repeticiones}"
        })
    
    # Rellenar con datos vacíos si no hay suficientes resultados
    while len(resultados) < 3:
        resultados.append({
            'nombre': 'Sin datos',
            'peso': 0,
            'repeticiones': 0,
            'series': 0,
            'display': 'No completado'
        })
    
    conn.close()
    return resultados

# Función para obtener el progreso semanal
def obtener_progreso_semanal(id_entrenamiento, id_alumno):
    conn = conexion_basedatos()
    cur = conn.cursor()
    
    # Obtener la fecha de inicio del entrenamiento
    cur.execute("SELECT fecha_inicio FROM entrenamiento WHERE id_entrenamiento = ?", (id_entrenamiento,))
    fecha_inicio = cur.fetchone()[0]
    
    # Consulta para obtener el progreso por semana
    query = """
        SELECT 
            s.numero_semana,
            COUNT(DISTINCT d.id_dia) as total_dias,
            SUM(CASE WHEN d.completado = 1 THEN 1 ELSE 0 END) as dias_completados,
            COUNT(DISTINCT de.id_dia_ejercicio) as total_ejercicios,
            COUNT(DISTINCT CASE WHEN p.id_progreso IS NOT NULL THEN de.id_dia_ejercicio END) as ejercicios_completados
        FROM semanas s
        LEFT JOIN dias d ON s.id_semana = d.id_semana
        LEFT JOIN dia_ejercicio de ON d.id_dia = de.id_dia
        LEFT JOIN progreso_alumno p ON de.id_dia_ejercicio = p.id_dia_ejercicio AND p.id_alumno = ?
        WHERE s.id_entrenamiento = ?
        GROUP BY s.numero_semana
        ORDER BY s.numero_semana
    """
    
    cur.execute(query, (id_alumno, id_entrenamiento))
    semanas_data = cur.fetchall()
    
    # Procesar los datos para el template
    progreso_semanal = []
    for semana in semanas_data:
        numero_semana, total_dias, dias_completados, total_ejercicios, ejercicios_completados = semana
        
        # Calcular fecha de la semana (fecha_inicio + (numero_semana-1) semanas)
        fecha_semana = None
        if fecha_inicio:
            fecha_semana = (datetime.strptime(fecha_inicio, '%Y-%m-%d') + 
                          timedelta(weeks=numero_semana-1)).strftime('%d/%m/%Y')
        
        progreso_semanal.append({
            'numero_semana': numero_semana,
            'fecha_semana': fecha_semana or "Sin fecha",
            'dias_completados': f"{dias_completados}/{total_dias}",
            'ejercicios_completados': f"{ejercicios_completados}/{total_ejercicios}"
        })
    
    conn.close()
    return progreso_semanal


# Ruta principal para el progreso del alumno
@progreso_bp.route('/progreso')
@progreso_bp.route('/progreso/<int:id_entrenamiento>')
@login_required
@verificar_vinculo_y_rutina
def progreso(id_entrenamiento=None):
    id_usuario = session.get('id_usuario')
    
    conn = conexion_basedatos()
    cur = conn.cursor()
    
    # Obtener el id_alumno basado en el id_usuario de la sesión
    cur.execute("SELECT id_alumno FROM alumno WHERE id_usuario = ?", (id_usuario,))
    alumno = cur.fetchone()
    
    if not alumno:
        conn.close()
        return redirect(url_for('index'))
    
    id_alumno = alumno[0]
    
    # Obtener TODOS los entrenamientos del alumno con su progreso
    query_entrenamientos = """
        SELECT e.id_entrenamiento, e.nombre_entrenamiento, 
               COALESCE(
                   (SELECT COUNT(DISTINCT p.id_progreso) * 100.0 / NULLIF(COUNT(DISTINCT de.id_dia_ejercicio), 0)
                   FROM semanas s 
                   JOIN dias d ON s.id_semana = d.id_semana
                   JOIN dia_ejercicio de ON d.id_dia = de.id_dia
                   LEFT JOIN progreso_alumno p ON de.id_dia_ejercicio = p.id_dia_ejercicio AND p.id_alumno = ?
                   WHERE s.id_entrenamiento = e.id_entrenamiento
               ), 0) as progreso
        FROM entrenamiento e
        WHERE e.id_alumno = ?
        ORDER BY e.fecha_inicio DESC
    """
    cur.execute(query_entrenamientos, (id_alumno, id_alumno))
    columnas = [desc[0] for desc in cur.description]
    entrenamientos = [dict(zip(columnas, row)) for row in cur.fetchall()]
    
    # Redirigir al primer entrenamiento si no se especificó uno
    if not id_entrenamiento and entrenamientos:
        conn.close()
        return redirect(url_for('progreso.progreso', id_entrenamiento=entrenamientos[0]['id_entrenamiento']))
    
    entrenamiento_actual = None
    entrenamiento_actual = None
    dias_completados = 0
    total_dias = 0
    porcentaje_dias = 0

    # Si se seleccionó un entrenamiento, obtener sus datos específicos
    if id_entrenamiento:
        # Consulta modificada para manejar correctamente la relación con el entrenador
        query_entrenamiento = """
            SELECT e.id_entrenamiento, e.nombre_entrenamiento, 
                en.nombre, en.apellido, u.id_usuario,
                e.fecha_inicio, e.duracion_semanas
            FROM entrenamiento e
            JOIN usuario u ON e.id_entrenador = u.id_usuario
            JOIN entrenador en ON u.id_usuario = en.id_usuario
            WHERE e.id_entrenamiento = ? AND e.id_alumno = ?
        """
        cur.execute(query_entrenamiento, (id_entrenamiento, id_alumno))
        entrenamiento_raw = cur.fetchone()

        if entrenamiento_raw:
            columnas = [desc[0] for desc in cur.description]
            entrenamiento_actual = dict(zip(columnas, entrenamiento_raw))
            # Construir el nombre completo del entrenador
            entrenamiento_actual['entrenador'] = f"{entrenamiento_actual['nombre']} {entrenamiento_actual['apellido']}"
            
            # Buscar el progreso en la lista de entrenamientos
            for ent in entrenamientos:
                if ent['id_entrenamiento'] == id_entrenamiento:
                    entrenamiento_actual['progreso'] = ent['progreso']
                    break

        # Consulta para obtener días completados y total de días
        query_dias = """
            SELECT 
                SUM(CASE WHEN d.completado = 1 THEN 1 ELSE 0 END) as dias_completados,
                COUNT(d.id_dia) as total_dias
            FROM entrenamiento e
            JOIN semanas s ON e.id_entrenamiento = s.id_entrenamiento
            JOIN dias d ON s.id_semana = d.id_semana
            WHERE e.id_entrenamiento = ?
        """
        cur.execute(query_dias, (id_entrenamiento,))
        dias_data = cur.fetchone()
    
        if dias_data:
            dias_completados = dias_data[0] if dias_data[0] is not None else 0
            total_dias = dias_data[1] if dias_data[1] is not None else 0
            porcentaje_dias = round((dias_completados / total_dias) * 100) if total_dias > 0 else 0

            print(f"Dias completados: {dias_completados}")
            print(f"Total de dias: {total_dias}")
            print(f"Porcentaje de dias: {porcentaje_dias}")

    # -------- Gráficos y datos adicionales -----------

    # Obtener datos para el gráfico de rendimiento
    datos_rendimiento = None
    if id_entrenamiento:
        datos_rendimiento = obtener_datos_rendimiento(id_entrenamiento, id_alumno)
    
    # Convertir datos a JSON para pasarlos al template
    datos_json = json.dumps(datos_rendimiento) if datos_rendimiento else 'null'

    # Obtener datos para el gráfico de fuerza
    datos_fuerza = None
    if id_entrenamiento:
        datos_fuerza = obtener_datos_fuerza(id_entrenamiento, id_alumno)

    # Obtener top 3 de los mejores ejercicios
    mejores_marcas = None
    if id_entrenamiento:
        mejores_marcas = obtener_mejores_marcas(id_entrenamiento, id_alumno)
    
    # Obtener datos de progreso semanal
    progreso_semanal = None
    if id_entrenamiento:
        progreso_semanal = obtener_progreso_semanal(id_entrenamiento, id_alumno)

    conn.close()
    
    return render_template('progreso.html',
                        entrenamientos=entrenamientos,
                        entrenamiento_actual=entrenamiento_actual,
                        id_entrenamiento_actual=id_entrenamiento,
                        dias_completados=dias_completados,
                        total_dias=total_dias,
                        porcentaje_dias=porcentaje_dias,
                        datos_rendimiento_json=datos_json,
                        datos_fuerza_json=json.dumps(datos_fuerza) if datos_fuerza else 'null',
                        mejores_marcas=mejores_marcas,
                        progreso_semanal=progreso_semanal)