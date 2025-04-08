from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.helpers import login_required, verificar_formulario_completo
from app.utils.conexion import conexion_basedatos
from datetime import date


dashboard_bp = Blueprint('dashboard', __name__)


# Ruta de Dashboard
@dashboard_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    return render_template('dashboard.html')


# Ruta de Progreso Alumno
@dashboard_bp.route('/dashboard/progreso-alumno/<alumno_id>', methods=['GET', 'POST'])
@login_required
def progreso_alumno(alumno_id):
    return render_template('progreso_alumno.html', alumno_id=alumno_id)