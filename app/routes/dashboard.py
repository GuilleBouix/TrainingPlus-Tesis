from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.helpers import login_required, verificar_formulario_completo
from app.utils.conexion import conexion_basedatos
from datetime import date


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



# Ruta de Dashboard
@dashboard_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    id_entrenador = session.get('id_usuario')
    
    # Obtener el total de alumnos con planes activos
    total_alumnos = obtener_total_alumnos(id_entrenador)

    return render_template('dashboard.html',
                           total_alumnos=total_alumnos)


# Ruta de Progreso Alumno
@dashboard_bp.route('/dashboard/progreso-alumno/<alumno_id>', methods=['GET', 'POST'])
@login_required
def progreso_alumno(alumno_id):
    return render_template('progreso_alumno.html', alumno_id=alumno_id)