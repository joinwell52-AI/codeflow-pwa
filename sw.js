// build: 20260414-2.2.9
importScripts("./config.js");

const APP_VERSION = (self.CODEFLOW_CONFIG && self.CODEFLOW_CONFIG.appVersion) || "1.0.0";
const CACHE_NAME = `codeflow-pwa-${APP_VERSION}`;
const CORE_ASSETS = ["./", "./index.html", "./config.js", "./manifest.json", "./logo-CodeFlow-125.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => (key.startsWith("codeflow-pwa-") || key.startsWith("codeflow-pwa-")) && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

// 接收前端发来的 SKIP_WAITING，立即激活新 SW
self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") {
    return;
  }
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response && response.status === 200) {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, responseToCache));
        }
        return response;
      })
      .catch(() =>
        caches.match(request).then((cached) => {
          if (cached) {
            return cached;
          }
          if (request.mode === "navigate") {
            return caches.match("./index.html");
          }
          return Response.error();
        })
      )
  );
});
