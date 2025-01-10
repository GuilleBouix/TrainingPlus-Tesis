from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.conexion import conexion_basedatos
from app.utils.helpers import insertar_usuario
from werkzeug.security import generate_password_hash, check_password_hash



auth_bp = Blueprint('auth', __name__)



# Ruta de Login
@auth_bp.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        contrasena = request.form['contrasena']
        
        # Validar el usuario en la BD
        try:
            conn = conexion_basedatos()
            cursor = conn.cursor()
            cursor.execute("SELECT id_usuario, nombre_usuario, contrasena, rol FROM usuario WHERE email = ?", (email,))
            user = cursor.fetchone()
        except Exception as e:
            flash(f"Error de base de datos: {str(e)}.", 'error')
            return redirect(url_for('auth.login'))
        finally:
            conn.close()

        if user and check_password_hash(user[2], contrasena):  # Corrige el índice de la contraseña
            session['id_usuario'] = user[0]
            session['nombre_usuario'] = user[1]  # Guarda el nombre de usuario en la sesión
            session['rol'] = user[3]

            # Si el usuario es entrenador, comprobar si tiene el formulario completo
            if user[3] == 2:  # Rol de entrenador
                try:
                    conn = conexion_basedatos()
                    cursor = conn.cursor()
                    cursor.execute("SELECT form_complete FROM entrenador WHERE id_usuario = ?", (user[0],))
                    form_status = cursor.fetchone()
                except Exception as e:
                    flash(f"Error al verificar el estado del formulario: {str(e)}", 'error')
                    return redirect(url_for('auth.login'))
                finally:
                    conn.close()
                
                # Si el formulario no está completo, redirigir a completar perfil
                if form_status and form_status[0] == 'false':
                    return redirect(url_for('form_entrenador.form_entrenador'))

            # Redirigir según la página solicitada o la página de entrenamiento
            next_page = request.args.get('next')
            return redirect(next_page or url_for('entrenamiento.entrenamiento'))
        else:
            flash('Datos incorrectos.', 'error')
            return redirect(url_for('auth.login'))

    return render_template('login.html')





# Ruta de Signup
@auth_bp.route('/auth/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        nombre_usuario = request.form['nombre_usuario']
        contrasena = request.form['contrasena']
        rol = request.form['rol']

        # Validación del rol (si no es 1 ni 2)
        if rol not in ['1', '2']:
            flash('Rol inválido.', 'error')
            return redirect(url_for('auth.signup'))

        # Convertir rol
        rol = 1 if rol == '1' else 2

        # Validar si el correo ya está registrado
        try:
            conn = conexion_basedatos()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM usuario WHERE email = ?", (email,))
            existing_user = cursor.fetchone()
        except Exception as e:
            flash(f"Error de base de datos: {str(e)}", 'error')
            return redirect(url_for('auth.signup'))

        if existing_user:
            flash('Correo ya registrado.', 'error')
            return redirect(url_for('auth.signup'))

        # Insertar el nuevo usuario con contraseña hasheada
        try:
            contrasena_hash = generate_password_hash(contrasena)
            conn = conexion_basedatos()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuario (email, nombre_usuario, contrasena, rol) VALUES (?, ?, ?, ?)",
                (email, nombre_usuario, contrasena_hash, rol)
            )
            conn.commit()
            id_usuario = cursor.lastrowid  # Obtener el ID del usuario recién creado

            # Crear registro en la tabla correspondiente según el rol
            if rol == 1:  # Alumno
                cursor.execute(
                    "INSERT INTO alumno (id_usuario) VALUES (?)",
                    (id_usuario,)  # Nota la coma para hacer una tupla
                )
            elif rol == 2:  # Entrenador
                cursor.execute(
                    "INSERT INTO entrenador (id_usuario, form_complete) VALUES (?, ?)",
                    (id_usuario, 'false')  # Guardar 'false' como texto
                )
            conn.commit()
            
            flash('Registro exitoso.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            print(f"Error al registrar el usuario: {e}")  # Esto imprime el error
            flash(f"Error al registrar el usuario: {str(e)}", 'error')
            return redirect(url_for('auth.signup'))
        finally:
            conn.close()
    
    return render_template('signup.html')





# Ruta Cerrar Sesión
@auth_bp.route('/auth/logout')
def logout():
    # Eliminar todos los datos de la sesión
    session.pop('id_usuario', None)
    session.pop('rol', None)
    session.clear()

    # Redirigir al login
    return redirect(url_for('auth.login'))