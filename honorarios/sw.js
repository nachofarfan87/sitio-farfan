/* Service worker del arancel: la página se puede instalar y abre sin conexión.
   Su alcance es /honorarios/ — el resto del sitio no pasa por acá. */
const CACHE = 'farfan-arancel-v1';
const CORE = ['./', './index.html', './icono.png', './icono-192.png', './manifest.webmanifest', './uma.json', './servicios.json'];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;

  // HTML y datos (uma/servicios) -> red primero (siempre lo último), caché como respaldo offline
  const isDoc = req.mode === 'navigate' || url.pathname.endsWith('/') || url.pathname.endsWith('/index.html');
  const isData = url.pathname.endsWith('/uma.json') || url.pathname.endsWith('/servicios.json');

  if (isDoc || isData) {
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (sameOrigin && res && res.status === 200) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => caches.match(req).then((m) => m || caches.match('./index.html')))
    );
    return;
  }

  // Resto del mismo origen (iconos, manifest) -> caché primero + actualización en segundo plano
  if (sameOrigin) {
    e.respondWith(
      caches.match(req).then((cached) => {
        const network = fetch(req)
          .then((res) => {
            if (res && res.status === 200) {
              const copy = res.clone();
              caches.open(CACHE).then((c) => c.put(req, copy));
            }
            return res;
          })
          .catch(() => cached);
        return cached || network;
      })
    );
  }
  // Recursos externos (tipografías): se dejan pasar; sin conexión caen a la letra del sistema.
});
