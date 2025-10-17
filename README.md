![Training+](https://github.com/user-attachments/assets/2c2e80ec-d4f4-4cb1-b8b1-48f4e34c01b9)

# Training+ | Sistema de Gestión y Supervisión de Entrenamientos Personalizados

**Plataforma web para la gestión integral de entrenamientos personalizados**

Sistema desarrollado como proyecto de tesis que conecta entrenadores y alumnos en un entorno digital, facilitando la creación, seguimiento y análisis de rutinas de entrenamiento personalizadas con métricas de progreso en tiempo real.

## 🎯 Características principales

### Para Entrenadores
- **Dashboard completo** con estadísticas de todos los alumnos
- **Creación de rutinas** estructuradas por semanas, días y ejercicios específicos  
- **Seguimiento en tiempo real** del progreso de cada alumno
- **Gestión de vinculaciones** con sistema de solicitudes
- **Análisis de rendimiento** con métricas detalladas por alumno

### Para Alumnos  
- **Registro de entrenamientos** con seguimiento de series, repeticiones y pesos
- **Visualización de progreso** con gráficas de rendimiento y marcas personales
- **Sistema de notificaciones** para nuevas rutinas y mensajes del entrenador
- **Análisis personal** con distribución por tipo de ejercicio (empuje, jalón, resistencia)

## 🔧 Funcionalidades del sistema

### Autenticación y vinculación
- Sistema de roles diferenciado (entrenador/alumno)
- Proceso de vinculación mediante solicitudes
- Búsqueda de usuarios y gestión de contactos

### Gestión de entrenamientos
- Planificación jerárquica: semanas → días → ejercicios
- Rutinas completamente personalizables
- Registro detallado de desempeño por ejercicio
- Ajustes dinámicos según el progreso

### Analytics y progreso
- **Dashboard del entrenador**: vista global de todos los alumnos
- **Progreso individual**: gráficas de evolución, % de completado, marcas personales
- **Clasificación por tipo**: análisis de distribución de ejercicios
- **Histórico completo** de entrenamientos realizados

## 📱 Capturas del sistema

<img width="1359" height="633" alt="Login" src="https://github.com/user-attachments/assets/da5c853e-7888-4cfa-882b-c72b7603947a" />
<img width="1359" height="633" alt="Signup" src="https://github.com/user-attachments/assets/4d4320f0-d6ac-4f3b-9b5b-312219a2a012" />
<img width="1359" height="633" alt="Trainer - Home" src="https://github.com/user-attachments/assets/b788f221-3df8-46b0-ab2b-83ef113880c6" />
<img width="1359" height="633" alt="Búsqueda" src="https://github.com/user-attachments/assets/f2755952-5f6d-4460-addf-49be5f73c736" />
<img width="1359" height="633" alt="Ver Entrenamiento" src="https://github.com/user-attachments/assets/2db93cab-55ca-4edd-879a-1e3478710849" />
<img width="1359" height="1179" alt="Dashboard" src="https://github.com/user-attachments/assets/7a7ecaf5-1e45-4efd-ae95-d4b391d72051" />
<img width="1359" height="961" alt="Progreso" src="https://github.com/user-attachments/assets/6182db6b-d1de-42dd-8130-ad1a8d167ddf" />
<img width="1359" height="633" alt="Editar Perfil" src="https://github.com/user-attachments/assets/cc9a45df-a342-4229-96c6-35f70570f871" />

## 🛠️ Stack tecnológico

| Componente | Tecnología |
|------------|------------|
| **Backend** | Python 3.13.1 + Flask |
| **Frontend** | HTML5, CSS3, JavaScript (Vanilla) |
| **Base de datos** | SQLite3 |
| **Arquitectura** | MVC con templates Jinja2 |

## 🚀 Instalación y configuración

### Prerrequisitos
- Python 3.7 o superior
- pip (gestor de paquetes de Python)

### Pasos de instalación

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/GuilleBouix/TrainingPlus-Tesis.git
   cd Training+
   ```

2. **Crear entorno virtual** (recomendado)
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar la aplicación**
   ```bash
   python app.py
   ```

5. **Acceder al sistema**
   Abrir el navegador en `http://localhost:5000`

## 📊 Arquitectura del sistema

```
Training+/
├── app.py                      # Aplicación principal Flask
├── requirements.txt            # Dependencias Python
├── README.md                   # Documentación del proyecto
├── .gitignore                  # Archivos ignorados por Git
└── app/                        # Módulo principal de la aplicación
    ├── __init__.py             # Inicializador del módulo
    ├── routes/                 # Controladores y rutas
    │   ├── auth.py             # Autenticación y registro
    │   ├── buscador.py         # Búsqueda de usuarios
    │   ├── cuestionario.py     # Formularios y encuestas
    │   ├── dashboard.py        # Panel de control del entrenador
    │   ├── entrenamiento.py    # Gestión de entrenamientos
    │   ├── form_entrenador.py  # Formularios de entrenador
    │   ├── notificaciones.py   # Sistema de notificaciones
    │   ├── opciones.py         # Configuraciones del sistema
    │   ├── perfil.py           # Gestión de perfiles de usuario
    │   ├── progreso.py         # Seguimiento y estadísticas
    │   ├── rutina.py           # Creación y gestión de rutinas
    │   ├── suscripcion.py      # Gestión de suscripciones
    │   └── usuario.py          # Operaciones de usuario
    ├── static/                 # Archivos estáticos
    │   ├── css/                # Hojas de estilo
    │   ├── images/             # Imágenes del sistema
    │   ├── manual/             # Manuales y documentación
    │   └── uploads/            # Archivos subidos por usuarios
    │       ├── exercises/      # Imágenes de ejercicios
    │       │   └── fitness/    # Categoría fitness
    │       ├── titles/         # Títulos y certificaciones
    │       ├── users/          # Fotos de perfil
    │       └── weekly_progress/ # Capturas de progreso semanal
    ├── templates/              # Plantillas HTML (Jinja2)
    └── utils/                  # Utilidades y helpers
        ├── conexion.py         # Gestión de conexiones BD
        └── helpers.py          # Funciones auxiliares
```

## 🎓 Contexto académico

Este sistema fue desarrollado como proyecto de tesis final para las materias Práctica Profesional y Programación Científica de la carrera Analista Programador en el Instituto Privado de Estudios Superiores IPET 1308, Oberá, Misiones, Argentina.
El proyecto se enfoca en la digitalización de procesos de entrenamiento físico personalizado, demostrando la aplicación práctica de tecnologías web modernas en la resolución de problemas reales del ámbito deportivo y la gestión de relaciones entrenador-alumno.

## 👨‍💻 Autor

**Guillermo Bouix** - Desarrollador principal  
Proyecto de Tesis - 2025
