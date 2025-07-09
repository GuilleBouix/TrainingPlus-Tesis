from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.conexion import conexion_basedatos
from app.utils.helpers import login_required
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import date
import smtplib
import os


# Cargar las variables de entorno desde el archivo .env
load_dotenv()


EMAIL_DESTINO = os.getenv("EMAIL_GMAIL")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


# Blueprint para opciones
opciones_bp = Blueprint('opciones', __name__)


# Obtener datos del usuario para el formulario de soporte
def obtener_datos_usuario():
    try:
        if 'id_usuario' not in session or 'rol' not in session:
            return None
        
        id_usuario = session['id_usuario']
        rol = session['rol']
        
        conn = conexion_basedatos()
        cursor = conn.cursor()
        
        # Consulta para obtener el email (siempre de la tabla usuario)
        cursor.execute(
            "SELECT email FROM usuario WHERE id_usuario = ?",
            (id_usuario,)
        )
        usuario_data = cursor.fetchone()
        
        if not usuario_data:
            return None
        
        email = usuario_data[0]
        
        # Consulta para nombre y apellido según el rol
        if rol == 1:  # Alumno
            cursor.execute(
                "SELECT nombre, apellido FROM alumno WHERE id_usuario = ?",
                (id_usuario,)
            )
        elif rol == 2:  # Entrenador
            cursor.execute(
                "SELECT nombre, apellido FROM entrenador WHERE id_usuario = ?",
                (id_usuario,)
            )
        else:
            return {'email': email, 'nombre_completo': ''}
        
        datos_personales = cursor.fetchone()
        conn.close()
        
        if datos_personales:
            nombre, apellido = datos_personales
            nombre_completo = f"{nombre} {apellido}" if nombre and apellido else nombre or apellido or ''
        else:
            nombre_completo = ''
        
        return {
            'email': email,
            'nombre_completo': nombre_completo.strip()
        }
    except Exception as e:
        print(f"Error al obtener datos del usuario: {str(e)}")
        flash(f"Error al obtener datos para soporte: {str(e)}", 'error')
        
        return None


# Enviar mensaje de soporte
def enviar_mensaje_soporte(nombre, email_usuario, mensaje_usuario):
    asunto = f"Soporte TRAINING+ - Mensaje de {email_usuario}"
    cuerpo = f"""
    Código de Usuario: {session['id_usuario']}
    Nombre: {nombre}
    Email: {email_usuario}
    Fecha: {date.today().strftime('%d/%m/%Y')}
    
    Mensaje:
    {mensaje_usuario}
    """

    msg = MIMEText(cuerpo, 'plain')
    msg['Subject'] = asunto
    msg['From'] = EMAIL_DESTINO 
    msg['To'] = EMAIL_DESTINO

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(EMAIL_DESTINO, EMAIL_PASSWORD)
        server.sendmail(email_usuario, EMAIL_DESTINO, msg.as_string())


# Ruta de Opciones
@opciones_bp.route('/opciones', methods=['GET', 'POST'])
@login_required
def opciones():
    # Obtener datos para el formulario de soporte
    datos_soporte = obtener_datos_usuario()

    if request.method == 'POST':
        mensaje_usuario = request.form.get('mensaje')

        if not datos_soporte:
            flash('Error al obtener datos del usuario para enviar el mensaje.', 'error')
            return redirect(url_for('opciones.opciones'))

        try:
            enviar_mensaje_soporte(
                datos_soporte['nombre_completo'],
                datos_soporte['email'],
                mensaje_usuario
            )
            flash('Mensaje enviado correctamente.', 'success')
        except Exception as e:
            print(f"Error al enviar correo: {e}")
            flash('Hubo un error al enviar el mensaje. Intenta más tarde.', 'error')

        return redirect(url_for('opciones.opciones'))

    return render_template('opciones.html', 
                           datos_soporte=datos_soporte)