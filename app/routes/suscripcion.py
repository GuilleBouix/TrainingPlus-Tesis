from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.helpers import login_required
from app.utils.conexion import conexion_basedatos
from datetime import date


suscripcion_bp = Blueprint('suscripcion', __name__)


# Ruta de Entrenamiento
@suscripcion_bp.route('/suscripcion', methods=['GET', 'POST'])
@login_required
def suscripcion():
    return render_template('suscripcion.html')