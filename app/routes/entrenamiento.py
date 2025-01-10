from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.helpers import login_required, verificar_formulario_completo



entrenamiento_bp = Blueprint('entrenamiento', __name__)



# Ruta de Entrenamiento
@entrenamiento_bp.route('/entrenamiento')
@login_required
@verificar_formulario_completo
def entrenamiento():    
    user_role = session.get('rol')
    return render_template('entrenamiento.html', user_role=user_role)