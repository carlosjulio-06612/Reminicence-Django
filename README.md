# 🎵 Reminicence — API Backend (Django REST)

## Descripción

**Reminicence** es una aplicación web musical actualmente en proceso de **migración hacia una arquitectura desacoplada**.
En esta rama (`api-migration`), el proyecto evoluciona desde un backend monolítico con plantillas HTML hacia una **API RESTful construida con Django** para ser consumida por un **frontend en React**.

El objetivo de esta fase es **centralizar toda la lógica de negocio, autenticación, auditoría e integración con Spotify** en el backend, garantizando una comunicación eficiente con el cliente a través de endpoints JSON.

---

## Tabla de Contenidos

1. [Estructura del proyecto](#estructura-del-proyecto)
2. [Tecnologías utilizadas](#tecnologías-utilizadas)
3. [Instalación y configuración](#instalación-y-configuración)
4. [Uso y endpoints](#uso-y-endpoints)
5. [Arquitectura y módulos](#arquitectura-y-módulos)
6. [Integración con el frontend React](#integración-con-el-frontend-react)
7. [Licencia](#licencia)
8. [Contacto y contribuciones](#contacto-y-contribuciones)

---

## Estructura del proyecto

```text
Reminicence/
│
├── Backend/
│   └── BK_Reminicence/
│       ├── applications/
│       │   ├── core/            # Configuración base, excepciones, paginación y utilidades
│       │   ├── music/           # Endpoints REST para canciones, artistas y álbumes
│       │   ├── spotify_api/     # Integración con Spotify mediante API propia
│       │   ├── users/           # Gestión y autenticación de usuarios vía JWT
│       │   └── auditing/        # Auditoría de acciones del sistema
│       │
│       ├── BK_Reminicence/      # Configuración global del proyecto Django
│       ├── requirements/        # Dependencias del entorno
│       ├── media/               # Archivos multimedia cargados por usuarios
|        └── manage.py            # Punto de entrada principal

```

---

## Tecnologías utilizadas

* **Python 3.12+**
* **Django 5.x**
* **Django REST Framework (DRF)**
* **PostgreSQL** como base de datos principal
* **Spotipy / Spotify Web API**
* **CORS Headers** para integración con React
* **SimpleJWT** para autenticación basada en tokens
* **Docker (opcional)** para despliegue y contenedorización

---

## Instalación y configuración

1. **Clonar el repositorio y cambiar a la rama `api-migration`:**

   ```bash
   git clone https://github.com/carlosjulio-06612/Reminicence-Django.git
   cd Reminicence/Backend
   git checkout api-migration
   ```

2. **Crear y activar entorno virtual:**

   ```bash
   python -m venv venv
   source venv/bin/activate     # Linux/Mac
   venv\Scripts\activate        # Windows
   ```

3. **Instalar dependencias:**

   ```bash
   pip install -r BK_Reminicence/requirements/local.txt
   ```

4. **Configurar variables sensibles:**

   Crea un archivo `secret.json` en `BK_Reminicence/BK_Reminicence/` con tus credenciales:

   ```json
   {
     "SECRET_KEY": "tu_clave_secreta",
     "DB_NAME": "reminicence_db",
     "DB_USER": "postgres",
     "DB_PASSWORD": "tu_contraseña",
     "DB_HOST": "localhost",
     "DB_PORT": "5432"
   }
   ```

5. **Aplicar migraciones y ejecutar servidor:**

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py runserver
   ```

   API disponible en: [http://127.0.0.1:8000/api/](http://127.0.0.1:8000/api/)

---

## Uso y endpoints

Los endpoints se agrupan por aplicación:

| Módulo          | Prefijo          | Descripción                                  |
| --------------- | ---------------- | -------------------------------------------- |
| **Users**       | `/api/users/`    | Registro, login y gestión de usuarios (JWT). |
| **Music**       | `/api/music/`    | CRUD de canciones, artistas y álbumes.       |
| **Spotify API** | `/api/spotify/`  | Consulta y sincronización con Spotify.       |
| **Auditing**    | `/api/auditing/` | Registro de acciones del sistema.            |

Ejemplo de endpoint activo:

```bash
GET /api/music/albums/
```

Retorna un listado en formato JSON con metadatos y paginación.

---

## Arquitectura y módulos

El backend sigue el patrón **RESTful modular**, con las aplicaciones divididas en:

* **`core`**: configuración global, manejo de excepciones y utilidades comunes.
* **`users`**: autenticación, tokens y control de permisos.
* **`music`**: servicios y endpoints REST del dominio musical.
* **`spotify_api`**: integración con API de terceros.
* **`auditing`**: monitoreo y trazabilidad de acciones.

---

## Integración con el frontend React

El frontend (en desarrollo) consumirá los endpoints de este backend mediante **fetch/Axios**.
Asegúrate de tener configurado CORS en `settings/base.py`:

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]
```

Esto permitirá la comunicación directa entre el cliente React y la API.

---

## Licencia

Distribuido bajo la **Licencia MIT**. Consulta el archivo `LICENSE` para más detalles.

---

## Contacto y contribuciones

Desarrollado por **Carlos Julio Wilches**.
Contribuciones, revisiones o sugerencias son bienvenidas mediante *pull requests* o *issues* en GitHub.
Repositorio: [Reminicence-Django](https://github.com/carlosjulio-06612/Reminicence-Django)

