'use strict';

// Minimal service worker — required for PWA installability.
// No caching strategy; the app always fetches live from the server.
self.addEventListener('fetch', event => {
  event.respondWith(fetch(event.request));
});
