from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.conexion import conexion_basedatos
from app.utils.helpers import login_required, verificar_formulario_completo



rutina_bp = Blueprint('rutina', __name__)



# Ruta de Rutina
@rutina_bp.route('/entrenamiento/rutina/<int:id>')
@login_required
@verificar_formulario_completo
def rutina(id):
    user_role = session.get('user_role', 'Invitado')
    return render_template('rutina.html', user_role=user_role, id=id)