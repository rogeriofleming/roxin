// O que faz o Roxin abrir SEM INTERNET.
//
// Guarda a casca do app (html, js, icones) no cache do navegador. As musicas nao
// passam por aqui: elas moram no OPFS, que e outro lugar e nao tem a ver com o
// service worker.
//
// Estrategia: rede primeiro para o HTML (assim uma versao nova aparece quando ha
// internet), cache primeiro para o resto. E sempre com uma volta pelo cache
// quando a rede falha -- que e o caso normal aqui: o Roger vai usar isto no
// aviao, no carro, no mato.
const CACHE = 'roxin-casca-v1';
const CASCA = ['./', 'index.html', 'app.js', 'acervo.js', 'tocador.js',
               'manifest.json', 'icone-180.png', 'icone-192.png', 'icone-512.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CASCA)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const ehPagina = req.mode === 'navigate';
  e.respondWith(
    (ehPagina ? fetch(req).then((r) => {
      caches.open(CACHE).then((c) => c.put(req, r.clone()));
      return r;
    }).catch(() => caches.match('index.html'))
      : caches.match(req).then((c) => c || fetch(req).then((r) => {
          if (r.ok) caches.open(CACHE).then((k) => k.put(req, r.clone()));
          return r;
        })))
  );
});
