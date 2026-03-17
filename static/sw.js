/**
 * Radio Calico Service Worker — offline caching for static assets.
 *
 * Caches the app shell (HTML, CSS, JS, logo) on install so the UI loads
 * offline. API requests and streaming media are network-only.
 */

const CACHE_NAME = 'radiocalico-v1';
const STATIC_ASSETS = [
    '/',
    '/css/player.css',
    '/js/player.js',
    '/logo.webp',
    '/logo.png',
    '/favicon.webp',
];

// Install: pre-cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

// Fetch: network-first for API/streaming, cache-first for static assets
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // API requests and streaming: always network
    if (url.pathname.startsWith('/api/') || url.hostname !== self.location.hostname) {
        return;
    }

    // Static assets: cache-first with network fallback
    event.respondWith(
        caches.match(event.request).then((cached) => {
            if (cached) return cached;
            return fetch(event.request).then((response) => {
                // Cache successful GET responses
                if (response.ok && event.request.method === 'GET') {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                }
                return response;
            });
        })
    );
});