# 🎵 Reminicence

## Descripción  
**Reminicence** es una aplicación web desarrollada con Django que permite la gestión y análisis de contenido musical. Incluye funcionalidades como autenticación de usuarios, auditoría de acciones, gestión de canciones/álbumes/géneros, integración con la API de Spotify API y manejo de archivos multimedia.  
Este proyecto se realiza en el contexto universitario y está estructurado para facilitar la lectura, revisión y extensión.

---

## Tabla de Contenidos  
1. [Estructura del proyecto](#estructura-del-proyecto)  
2. [Tecnologías utilizadas](#tecnologías-utilizadas)  
3. [Instalación y configuración](#instalación-y-configuración)  
4. [Uso](#uso)  
5. [Aplicaciones principales](#aplicaciones-principales)  
6. [Licencia](#licencia)  
7. [Contacto y contribuciones](#contacto-y-contribuciones)

---

## Estructura del proyecto  
```text
Reminicence/
│
├── Backend/
│   └── BK_Reminicence/
│       ├── applications/
│       │   ├── auditing/        # Módulo de auditoría del sistema
│       │   ├── core/            # Configuración base y componentes reutilizables
│       │   ├── music/           # Gestión de canciones, artistas y álbumes
│       │   ├── spotify_api/     # Integración con la API de Spotify
│       │   └── users/           # Administración de usuarios y autenticación
│       │
│       ├── BK_Reminicence/      # Configuración principal del proyecto Django
│       ├── media/               # Archivos cargados por los usuarios
│       ├── requirements/        # Dependencias del entorno
│       ├── static/              # Archivos estáticos (CSS, JS, imágenes) – **incluida**
│       └── templates/           # Plantillas HTML del proyecto
│
├── manage.py                    # Archivo principal de ejecución de Django
├── LICENSE                      # Licencia MIT del proyecto
└── .gitignore                   # Reglas de exclusión para Git
````


---

## Tecnologías utilizadas

* Python 3.x
* Django (versión compatible)
* Base de datos: PostgreSQL o SQLite (según configuración)
* Integración con Spotify API
* Dependencias listadas en `requirements/requirements.txt`

---

## Instalación y configuración

1. **Clonar el repositorio**

   ```bash
   git clone https://github.com/tu-usuario/reminicence.git
   cd reminicence/Backend
   ```
2. **Crear y activar el entorno virtual**

   ```bash
   python -m venv venv
   source venv/bin/activate     # Linux/Mac
   venv\Scripts\activate        # Windows
   ```
3. **Instalar dependencias**

   ```bash
   pip install -r requirements/requirements.txt
   ```
4. **Configurar variables sensibles**
   Crea un archivo `secret.json` en el directorio raíz con tus credenciales privadas. Ejemplo:

   ```json
   {
     "SECRET_KEY": "tu_clave_secreta",
     "DB_NAME": "nombre_base_de_datos",
     "DB_USER": "usuario",
     "DB_PASSWORD": "tu_contraseña",
     "DB_HOST": "localhost",
     "DB_PORT": "5432"
   }
   ```
5. **Aplicar migraciones**

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
6. **Ejecutar el servidor de desarrollo**

   ```bash
   python manage.py runserver
   ```

   Visita [http://127.0.0.1:8000/](http://127.0.0.1:8000/) para ver la aplicación.

---

## Uso

Una vez levantada la aplicación, puedes:

* Registrarte/iniciar sesión como usuario.
* Navegar por el módulo de música para explorar canciones, artistas y álbumes.
* Utilizar la funcionalidad de integración con Spotify para obtener datos externos.
* Ver el módulo de auditoría para rastrear acciones del sistema.

---

## Aplicaciones principales

| Aplicación      | Descripción                                                  |
| --------------- | ------------------------------------------------------------ |
| **core**        | Configuración general del proyecto y utilidades compartidas. |
| **users**       | Gestión de usuarios, autenticación y control de acceso.      |
| **music**       | CRUD de canciones, álbumes y géneros musicales.              |
| **spotify_api** | Integración con la API de Spotify para ampliar el catálogo.  |
| **auditing**    | Registro de eventos del sistema para trazabilidad.           |

---

## Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Ver el archivo `LICENSE` para más detalles.

---

## Contacto y contribuciones

Las contribuciones y sugerencias son bienvenidas. Prefiere abrir un **issue** o enviar un **pull request**.
Gracias por revisar el proyecto — ¡esperamos que sea útil y claro!
