from flask import Blueprint, render_template
from app.utils.conexion import conexion_basedatos
from app.utils.helpers import login_required, verificar_formulario_completo



rutina_bp = Blueprint('rutina', __name__)


# Ruta de Rutina
@rutina_bp.route('/entrenamiento/rutina/<int:id_entrenamiento>')
@login_required
@verificar_formulario_completo
def rutina(id_entrenamiento):
    conn = conexion_basedatos()
    cursor = conn.cursor()

    # Obtener semanas del entrenamiento
    cursor.execute("SELECT * FROM semanas WHERE id_entrenamiento = ?", (id_entrenamiento,))

    return render_template('rutina.html')