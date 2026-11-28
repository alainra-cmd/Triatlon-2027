# Actualización manual segura del calendario

La app estática de GitHub Pages no debe contener un token de GitHub. Este Worker actúa como intermediario: verifica una solicitud con Cloudflare Turnstile y dispara el workflow mediante un token guardado como secreto del Worker.

## 1. Crear el Worker

1. En Cloudflare, abre **Workers & Pages** y crea un Worker llamado `triathlon-calendar-control`.
2. Sustituye su código por el contenido de `cloudflare/triathlon-calendar-control.js` y despliega.
3. Anota la URL `https://NOMBRE.SUBDOMINIO.workers.dev`.

## 2. Crear el token de GitHub

Crea un Fine-grained Personal Access Token limitado al repositorio `alainra-cmd/Triatlon-2027` con:
- **Actions: Read and write** (para iniciar el workflow y consultar su estado).
- **Contents: Read-only** (si se mantiene la lectura de datos del repositorio vía API; el feed público se lee sin token).

Guárdalo únicamente como secreto del Worker con el nombre `GH_TOKEN`. No lo pongas en el HTML, en GitHub Pages ni en mensajes.

## 3. Configurar secretos del Worker

En Worker → Settings → Variables and Secrets, añade como secretos:
- `GH_TOKEN`: el token anterior.
- `TURNSTILE_SECRET`: clave secreta del widget Turnstile.

## 4. Configurar Cloudflare Turnstile

1. Crea un widget Turnstile para el dominio `alainra-cmd.github.io`.
2. En los ajustes del widget, permite ese hostname.
3. Copia la **Site Key** pública; la Secret Key se guarda como `TURNSTILE_SECRET` en el Worker.

## 5. Conectar el HTML

En `index.html`, configura:
- `MANUAL_UPDATE_API`: URL del Worker, sin barra final.
- `MANUAL_UPDATE_TURNSTILE_SITE_KEY`: Site Key pública.

Después de guardar esos dos valores, el botón de la aplicación inicia la extracción y consulta el estado hasta que finalice. El token de GitHub permanece exclusivamente en el Worker.

## Seguridad

El endpoint de inicio exige validación Turnstile. CORS restringe el uso desde el dominio de la app, pero CORS no sustituye la autenticación ni la protección antiabuso; por eso se valida Turnstile en el servidor. Nunca publicar `GH_TOKEN` ni `TURNSTILE_SECRET`.
