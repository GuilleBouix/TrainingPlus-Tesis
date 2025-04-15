from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.helpers import login_required, verificar_formulario_completo
from app.utils.conexion import conexion_basedatos
from datetime import date


progreso_bp = Blueprint('progreso', __name__)


@progreso_bp.route('/progreso')
@progreso_bp.route('/progreso/<int:id_entrenamiento>')
@login_required
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
        query_entrenamiento = """
            SELECT e.id_entrenamiento, e.nombre_entrenamiento, 
                en.nombre || ' ' || en.apellido as entrenador,
                e.fecha_inicio, e.duracion_semanas
            FROM entrenamiento e
            JOIN entrenador en ON e.id_entrenador = en.id_entrenador
            WHERE e.id_entrenamiento = ? AND e.id_alumno = ?
        """
        cur.execute(query_entrenamiento, (id_entrenamiento, id_alumno))
        entrenamiento_raw = cur.fetchone()

        if entrenamiento_raw:
            columnas = [desc[0] for desc in cur.description]
            entrenamiento_actual = dict(zip(columnas, entrenamiento_raw))
            
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




    conn.close()
    
    return render_template('progreso.html',
                        entrenamientos=entrenamientos,
                        entrenamiento_actual=entrenamiento_actual,
                        id_entrenamiento_actual=id_entrenamiento,
                        dias_completados=dias_completados,
                        total_dias=total_dias,
                        porcentaje_dias=porcentaje_dias)