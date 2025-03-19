from flask import Blueprint, render_template, session
from app.utils.conexion import conexion_basedatos
from app.utils.helpers import login_required, verificar_formulario_completo



rutina_bp = Blueprint('rutina', __name__)


# Ruta de Rutina
@rutina_bp.route('/entrenamiento/rutina/<int:id_entrenamiento>')
@login_required
@verificar_formulario_completo
def rutina(id_entrenamiento):
    user_id = session.get('id_usuario')
    DB = conexion_basedatos()

    # Obtener datos del entrenamiento
    entrenamiento = DB.execute("""
        SELECT nombre_entrenamiento, disciplina, duracion_semanas
        FROM entrenamiento 
        WHERE id_entrenamiento = ?
    """, (id_entrenamiento,)).fetchone()

    if not entrenamiento:
        return "Entrenamiento no encontrado", 404

    # Obtener semanas del entrenamiento
    semanas = DB.execute("""
        SELECT id_semana, numero_semana 
        FROM semanas 
        WHERE id_entrenamiento = ? 
        ORDER BY numero_semana
    """, (id_entrenamiento,)).fetchall()

    # Obtener días y ejercicios por semana
    semanas_completas = []
    for semana in semanas:
        semana = dict(semana)  # Convertir `semana` a un diccionario
        id_semana = semana['id_semana']

        dias = DB.execute("""
            SELECT id_dia, numero_dia, nombre_rutina 
            FROM dias 
            WHERE id_semana = ? 
            ORDER BY numero_dia
        """, (id_semana,)).fetchall()

        # Obtener ejercicios por día
        dias_completos = []
        for dia in dias:
            dia = dict(dia)  # Convertir `dia` a un diccionario
            id_dia = dia['id_dia']

            ejercicios = DB.execute("""
                SELECT de.id_dia_ejercicio, e.nombre_ejercicio AS nombre_ejercicio, 
                    de.series, de.repeticiones, de.peso, de.tiempo_descanso
                FROM dia_ejercicio de
                JOIN ejercicios e ON de.id_ejercicio = e.id_ejercicio
                WHERE de.id_dia = ?
            """, (id_dia,)).fetchall()

            dia["ejercicios"] = [dict(ejercicio) for ejercicio in ejercicios]  # Convertir ejercicios a diccionarios
            dias_completos.append(dia)

        semana["dias"] = dias_completos
        semanas_completas.append(semana)

    return render_template('rutina.html', 
                           entrenamiento=entrenamiento,
                           semanas=semanas_completas)