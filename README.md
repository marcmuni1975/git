# Sistema de Gestión Escolar CEIA

Sistema para gestionar notas y generar certificados de alumnos.

## Instalación

1. Clonar el repositorio:
```bash
git clone <url-del-repositorio>
cd <nombre-del-repositorio>
```

2. Crear y activar entorno virtual:
```bash
# En Windows
python -m venv venv
venv\Scripts\activate

# En macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Ejecutar la aplicación:
```bash
python app.py
```

La aplicación estará disponible en `http://localhost:5004`

## Funcionalidades

- Gestión de cursos (crear, editar, eliminar)
- Gestión de alumnos con número de lista
- Importación de listas de alumnos desde archivo TXT
- Registro y edición de notas por asignatura
- Generación de certificados individuales
- Informes de notas por curso
- Exportación a PDF

## Estructura de Archivos

```
.
├── app.py              # Aplicación principal
├── requirements.txt    # Dependencias
├── static/            # Archivos estáticos (CSS, JS, imágenes)
├── templates/         # Plantillas HTML
└── instance/         # Base de datos SQLite (se crea automáticamente)
