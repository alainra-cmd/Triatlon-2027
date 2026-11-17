TRIATLÓN 2027 · BUSCADOR WEB DE COMPETICIONES (V15.6)

Novedades:
- Nuevo módulo «Buscador web de nuevas competiciones» en Datos y ajustes > Fuentes.
- Consulta discovery-feed.json y realiza búsquedas web mediante Bing News RSS para triatlón, duatlón, acuatlón, FETRI, World Triathlon, Challenge Family e IRONMAN.
- Muestra candidatos, fechas/localidades cuando se pueden extraer y enlace a la fuente original.
- Los resultados externos no se añaden automáticamente: se revisan y se importan manualmente.
- Feed inicial con eventos anunciados en calendarios de World Triathlon, Europe Triathlon y Challenge Family.
- Workflow de GitHub Actions semanal (lunes 06:15 UTC) para buscar nuevas menciones y actualizar el feed.
- El workflow conserva los candidatos oficiales y etiqueta las noticias como pendientes de revisión.
- Service worker actualizado y discovery-feed.json añadido a la caché.

Limitaciones:
- Los resultados RSS pueden ser noticias sin fecha de competición; se muestran como pistas y no se importan hasta disponer de fecha y localidad.
- Algunas páginas bloquean la extracción o requieren APIs/cookies. No se garantiza acceso a todas las webs.
- La búsqueda semanal requiere que GitHub Actions esté habilitado y tenga permiso de escritura.
- Las fechas oficiales del calendario no significan que las inscripciones estén abiertas; ese estado queda «Por verificar».
