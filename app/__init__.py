from flask import Flask, redirect, url_for
from app.utils.helpers import allowed_file
import os



def create_app():
    # Crear la instancia de la aplicación
    app = Flask(__name__)
    


    # Configurar la clave secreta para las sesiones
    app.config['SECRET_KEY'] = 'trainingpluskey'



    # Configuración de la carpeta para guardar las imágenes subidas
    UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}



    # Asegurarse de que la carpeta para subidas exista
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)



    # Registrar rutas desde la carpeta `routes`
    from .routes.entrenamiento import entrenamiento_bp
    from .routes.auth import auth_bp
    from .routes.suscripcion import suscripcion_bp
    from .routes.perfil import perfil_bp
    from .routes.buscador import buscador_bp
    from .routes.usuario import usuario_bp
    from .routes.notificaciones import notificaciones_bp
    from .routes.form_entrenador import form_entrenador_bp
    from .routes.rutina import rutina_bp
    from .routes.dashboard import dashboard_bp
    from .routes.progreso import progreso_bp
    from .routes.cuestionario import cuestionario_bp



    # Registrar Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(suscripcion_bp)
    app.register_blueprint(entrenamiento_bp)
    app.register_blueprint(perfil_bp)
    app.register_blueprint(buscador_bp)
    app.register_blueprint(usuario_bp)
    app.register_blueprint(notificaciones_bp)
    app.register_blueprint(form_entrenador_bp)
    app.register_blueprint(rutina_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(progreso_bp)
    app.register_blueprint(cuestionario_bp)



    # Ruta de redirección de la raíz
    @app.route('/')
    def home():
        return redirect(url_for('auth.login'))



    return app