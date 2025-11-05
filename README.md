# 🎧 Reminicence – Django Spotify Integration

> Comprehensive guide and implementation for connecting to the **Spotify Web API** using **Django**.  
> Includes secure authentication, token management, and interaction with Spotify’s core endpoints.

---

## 🚀 Descripción General

**Reminicence-Django** es una aplicación educativa basada en **Django** que implementa la conexión con la **Spotify Web API** utilizando el flujo de credenciales de cliente (**Client Credentials Flow**).  
Su propósito es servir como una guía práctica para entender la integración de servicios externos en entornos web seguros.

Incluye módulos para:
- Autenticación mediante credenciales de cliente.
- Gestión segura de tokens.
- Interacción con endpoints de Spotify para artistas, álbumes, canciones y playlists.
- Estructura modular escalable para extender funcionalidades.

---

## 🧩 Características Principales

- 🔐 **Autenticación segura:** manejo automatizado de tokens OAuth2.  
- 🎵 **Integración con Spotify:** obtención de datos de canciones, álbumes y artistas.  
- ⚙️ **Arquitectura modular:** separación de aplicaciones (`core`, `spotify_api`, `music`, etc.).  
- 📊 **Auditoría integrada:** registro de acciones dentro del sistema.  
- 🧠 **Enfoque educativo:** pensado para mostrar buenas prácticas de desarrollo en Django.

---

## 🛠️ Tecnologías Utilizadas

| Componente | Descripción |
|-------------|--------------|
| **Python 3.10+** | Lenguaje base del proyecto |
| **Django** | Framework principal de desarrollo web |
| **Spotify Web API** | Fuente de datos musicales y autenticación externa |
| **PostgreSQL / SQLite** | Base de datos relacional |
| **HTML, CSS, JS** | Frontend estático integrado en `/static` y `/templates` |

---

## ⚙️ Configuración Rápida

1. **Clona el repositorio**
   ```bash
   git clone https://github.com/carlosjulio-06612/Reminicence-Django.git
   cd Reminicence-Django/BK_Reminicence
````

2. **Crea y activa el entorno virtual**

   ```bash
   python -m venv venv
   source venv/bin/activate     # Linux/Mac
   venv\Scripts\activate        # Windows
   ```

3. **Instala dependencias**

   ```bash
   pip install -r requirements/requirements.txt
   ```

4. **Ejecuta el servidor**

   ```bash
   python manage.py runserver
   ```

   Accede a: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

## 🧱 Estructura Básica del Proyecto

```bash
Reminicence-Django/
│
├── BK_Reminicence/            # Proyecto principal
│   ├── applications/
│   │   ├── core/
│   │   ├── users/
│   │   ├── music/
│   │   ├── spotify_api/
│   │   └── auditing/
│   ├── static/                # Archivos estáticos (CSS, JS, imágenes)
│   └── templates/             # Plantillas HTML
│
├── LICENSE                    # Licencia MIT
└── .gitignore
```

---

## 📚 Documentación

Consulta la guía técnica completa y las instrucciones detalladas en el archivo [`README` dentro de BK_Reminicence](./BK_Reminicence/README.md).

---

## 🧾 Licencia

Este proyecto se distribuye bajo la licencia **MIT**.
Consulta el archivo [`LICENSE`](./LICENSE) para más información.

---

## ⭐ Contribuciones

Las contribuciones, ideas y mejoras son bienvenidas.
Puedes abrir un **issue** o enviar un **pull request** para colaborar.

