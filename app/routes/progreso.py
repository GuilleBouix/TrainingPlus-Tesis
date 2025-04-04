from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.helpers import login_required, verificar_formulario_completo
from app.utils.conexion import conexion_basedatos
from datetime import date


progreso_bp = Blueprint('progreso', __name__)


@progreso_bp.route('/progreso', methods=['GET', 'POST'])
@login_required
def progreso():
    return render_template('progreso.html')