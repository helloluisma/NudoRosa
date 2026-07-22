/*
 * Service Worker de Nudo Rosa.
 *
 * Se sirve desde la raíz (/service-worker.js, ver main.py) para que su
 * alcance cubra toda la app, no solo /static/.
 *
 * Alcance del caché — a propósito muy acotado:
 * Solo se cachean archivos estáticos de marca (CSS, JS, logo, iconos)
 * bajo /static/. TODO lo demás (páginas HTML, /login, cualquier
 * fetch/POST de ventas, clientas, cobros, inventario, sesión) pasa
 * directo a la red y nunca se guarda — esos datos son privados y
 * cambian todo el tiempo, cachearlos mostraría información vieja o
 * filtraría datos de negocio en el almacenamiento del dispositivo.
 */

const CACHE_VERSION = "nudo-rosa-v5";

const RUTAS_PRECARGA = [
    "/static/css/styles.css",
    "/static/js/app.js",
    "/static/images/logo.png",
    "/static/icons/icon-192.png",
    "/static/icons/icon-512.png",
    "/static/icons/icon-192-maskable.png",
    "/static/icons/icon-512-maskable.png",
    "/static/icons/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches
            .open(CACHE_VERSION)
            .then((cache) => cache.addAll(RUTAS_PRECARGA))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches
            .keys()
            .then((nombres) =>
                Promise.all(
                    nombres
                        .filter((nombre) => nombre !== CACHE_VERSION)
                        .map((nombre) => caches.delete(nombre))
                )
            )
            .then(() => self.clients.claim())
    );
});

function esRecursoEstaticoCacheable(url) {
    return url.origin === self.location.origin && url.pathname.startsWith("/static/");
}

/*
 * Stale-while-revalidate SOLO para /static/: responde con lo que haya
 * en caché al instante (si existe) y en paralelo pide la red para
 * dejar la versión más nueva lista para la próxima vez. Combinado con
 * CACHE_VERSION (se invalida todo al cambiar el número) y el `?v=N`
 * que ya usa _base.html en styles.css, una actualización de la app
 * nunca deja contenido viejo pegado.
 */
async function staleWhileRevalidate(request) {
    const cache = await caches.open(CACHE_VERSION);
    const enCache = await cache.match(request);

    const actualizarDesdeRed = fetch(request)
        .then((respuestaRed) => {
            if (respuestaRed.ok) {
                cache.put(request, respuestaRed.clone());
            }
            return respuestaRed;
        })
        .catch(() => enCache);

    return enCache || actualizarDesdeRed;
}

self.addEventListener("fetch", (event) => {
    const { request } = event;

    // Nunca interceptar nada que no sea una simple lectura: los
    // formularios (POST) de ventas/clientas/cobros/login deben llegar
    // siempre a la red, sin pasar por el caché.
    if (request.method !== "GET") {
        return;
    }

    const url = new URL(request.url);

    if (!esRecursoEstaticoCacheable(url)) {
        // Páginas HTML, /login, /manifest.webmanifest, /service-worker.js
        // y cualquier endpoint de datos: siempre a la red, tal cual.
        return;
    }

    event.respondWith(staleWhileRevalidate(request));
});
