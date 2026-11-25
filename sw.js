/* Actualización de lógica de banderas y comunidades; se conserva caché V16.1. */
const CACHE='triatlon-2027-v16-1-official-race-engine-1';
const ASSETS=['./','./index.html','./manifest.webmanifest','./icon.svg','./icon-192.png','./icon-512.png','./hero-triatlon.jpg','./fondo-alain.jpg','./cabecera-alain-triatlon-2027.jpg','./apple-touch-icon.png','./favicon.png','./fuente-carrera.png','./fuente-ciclismo.jpg','./fuente-natacion.jpg','./icon-1024.png','./status-feed.json','./race-feed.json'];
self.addEventListener('install',event=>event.waitUntil((async()=>{
 const cache=await caches.open(CACHE);
 await Promise.all(ASSETS.map(async asset=>{try{const response=await fetch(asset,{cache:'no-store'});if(response.ok)await cache.put(asset,response);}catch(_){}}));
 await self.skipWaiting();
})()));
self.addEventListener('activate',event=>event.waitUntil((async()=>{
 const keys=await caches.keys();
 await Promise.all(keys.filter(key=>key.startsWith('triatlon-2027-')&&key!==CACHE).map(key=>caches.delete(key)));
 await self.clients.claim();
})()));
self.addEventListener('fetch',event=>{
 if(event.request.method!=='GET')return;
 const url=new URL(event.request.url);
 if(url.pathname.endsWith('/status-feed.json')||url.pathname.endsWith('/race-feed.json')){
  event.respondWith(fetch(event.request,{cache:'no-store'}).then(response=>{if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));}return response;}).catch(()=>caches.match(event.request)));
  return;
 }
 if(event.request.mode==='navigate'||url.pathname.endsWith('/index.html')||url.pathname.endsWith('/sw.js')){
  event.respondWith(fetch(event.request,{cache:'no-store'}).then(response=>{if(response.ok&&url.pathname.endsWith('/index.html')){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put('./index.html',copy));}return response;}).catch(()=>caches.match(event.request).then(cached=>cached||caches.match('./index.html'))));
  return;
 }
 event.respondWith(caches.match(event.request).then(cached=>cached||fetch(event.request).then(response=>{if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));}return response;}).catch(()=>caches.match('./index.html'))));
});
self.addEventListener('notificationclick',event=>{event.notification.close();event.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(list=>list.length?list[0].focus():clients.openWindow('./')));});
