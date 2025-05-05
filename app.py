from dotenv import load_dotenv
from app import create_app
import os


# Cargar las variables de entorno desde el archivo .env
load_dotenv()


# Crear la instancia de la aplicación Flask
app = create_app()
app.secret_key = os.getenv("SECRET_KEY")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)