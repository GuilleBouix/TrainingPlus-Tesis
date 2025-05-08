from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.helpers import login_required, verificar_formulario_completo, verificar_suscripcion
from app.utils.conexion import conexion_basedatos
from datetime import date


opciones_bp = Blueprint('opciones', __name__)


# Ruta de Opciones
@opciones_bp.route('/opciones', methods=['GET', 'POST'])
@login_required
def opciones():
    return render_template('opciones.html')