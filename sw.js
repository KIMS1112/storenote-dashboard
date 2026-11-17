/* 매장경영노트 수익화 대시보드 — 서비스 워커
   앱 파일은 네트워크를 먼저 확인해 새 배포를 바로 받고, 오프라인일 때만 캐시를 씁니다.
   데이터(data.json)도 항상 네트워크 우선이라 갱신 내용이 즉시 반영됩니다. */
const CACHE = "storenote-dash-v3";
const ASSETS = [
  "./",
  "./index.html",
  "./styles.css",
  "./app.js",
  "./data.json",
  "./manifest.webmanifest",
  "./icon-180.png",
  "./icon-192.png",
  "./icon-512.png",
  "./icon-maskable-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function networkFirst(req) {
  return fetch(req, { cache: "no-store" })
    .then((res) => {
      if (res && res.ok) {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
      }
      return res;
    })
    .catch(() => caches.match(req).then((hit) => hit || caches.match("./index.html")));
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // 다른 도메인(폰트 CDN 등)은 그대로 둡니다.
  if (url.origin !== self.location.origin) return;

  // 아이콘만 캐시 우선
  if (/\/icon-[a-z0-9-]+\.png$/.test(url.pathname)) {
    event.respondWith(
      caches.match(req).then((hit) =>
        hit || fetch(req).then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
          return res;
        })
      )
    );
    return;
  }

  // 나머지(문서·스크립트·스타일·데이터)는 네트워크 우선
  event.respondWith(networkFirst(req));
});
